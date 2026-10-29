from uuid import uuid4
from unittest.mock import Mock
from backend.app.services.pipeline_service import PipelineService
from database.repository import SessionRepository


def test_complete_pipeline_persists_turn_and_recovers_after_restart():
    repository = SessionRepository()
    session_id = f"phase5-e2e-{uuid4()}"

    transcript = "I am confused and need a simpler explanation."
    assistant_response = "Let's break it down into smaller steps."

    speech_result = {
        "transcript": transcript,
        "language": "en",
        "language_probability": 0.99,
        "audio": {
            "duration": 2.0,
            "speech_duration": 1.6,
        },
        "vad": {
            "speech_segments": [
                {"start": 0.1, "end": 1.7},
            ],
        },
        "features": {},
    }

    llm_provider = Mock()
    llm_provider.generate.return_value = assistant_response

    try:
        # First pipeline instance: process and persist a complete turn.
        pipeline = PipelineService(
            llm_provider=llm_provider,
            session_id=session_id,
            repository=repository,
        )

        # Mock only the external speech-processing stage.
        pipeline.speech_service.process = Mock(
            return_value=speech_result,
        )

        result = pipeline.process_audio("integration-test.wav")

        assert result["speech"]["transcript"] == transcript
        assert result["response"] == assistant_response
        assert result["dialogue"]["policy"]["strategy"]

        llm_provider.generate.assert_called_once()

        # Verify the completed turn exists in PostgreSQL.
        persisted_turns = repository.get_turns(session_id, limit=10)

        assert len(persisted_turns) == 1
        assert persisted_turns[0].user_message == transcript
        assert persisted_turns[0].assistant_message == assistant_response
        assert (
            persisted_turns[0].dialogue_strategy
            == result["dialogue"]["policy"]["strategy"]
        )

        persisted_state = persisted_turns[0].human_state

        assert persisted_state["emotion"]["label"]
        assert 0.0 <= persisted_state["emotion"]["score"] <= 1.0
        assert "_temporal" in persisted_state
        assert persisted_state["_temporal"]["observation_valid"] is True

        # Simulate an application restart with a fresh pipeline instance.
        recovered = PipelineService(
            session_id=session_id,
            repository=repository,
        )

        history = recovered.dialogue_service.get_history()
        trajectory = recovered.human_state_engine.get_state_trajectory()

        assert len(history) == 1
        assert history[0]["user_message"] == transcript
        assert history[0]["assistant_message"] == assistant_response
        assert (
            history[0]["dialogue_strategy"]
            == result["dialogue"]["policy"]["strategy"]
        )

        assert len(trajectory) == 1
        assert (
            trajectory[0]["emotion"]["label"]
            == persisted_state["emotion"]["label"]
        )
        assert (
            trajectory[0]["emotion"]["score"]
            == persisted_state["emotion"]["score"]
        )

        # Historical recovery must not seed the temporal smoother.
        assert recovered.human_state_engine.temporal_smoother._previous is None

    finally:
        repository.clear_session(session_id)
