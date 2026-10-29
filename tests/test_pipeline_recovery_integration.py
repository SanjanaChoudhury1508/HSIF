from uuid import uuid4
from backend.app.services.pipeline_service import PipelineService
from database.repository import SessionRepository


def test_pipeline_recovers_persisted_history_and_state_from_postgres():
    repository = SessionRepository()
    session_id = f"phase5-recovery-{uuid4()}"

    state = {
        "emotion": {"label": "excited", "score": 0.739},
        "hesitation": {"score": 0.227},
        "confidence": {"score": 0.713},
        "engagement": {"score": 0.792},
        "cognitive_load": {"score": 0.274},
    }

    try:
        repository.add_turn(
            session_id=session_id,
            user_message="I am ready to continue.",
            assistant_message="Great, let's continue.",
            human_state=state,
            dialogue_strategy="continue",
        )

        # Simulate a restart by constructing a fresh pipeline instance.
        recovered = PipelineService(
            session_id=session_id,
            repository=repository,
        )

        history = recovered.dialogue_service.get_history()
        trajectory = recovered.human_state_engine.get_state_trajectory()

        assert len(history) == 1
        assert history[0]["user_message"] == "I am ready to continue."
        assert history[0]["assistant_message"] == "Great, let's continue."
        assert history[0]["dialogue_strategy"] == "continue"

        assert len(trajectory) == 1
        assert trajectory[0]["emotion"]["label"] == "excited"
        assert trajectory[0]["emotion"]["score"] == 0.739
        assert trajectory[0]["hesitation"] == 0.227
        assert trajectory[0]["confidence"] == 0.713
        assert trajectory[0]["engagement"] == 0.792
        assert trajectory[0]["cognitive_load"] == 0.274

        # Recovered historical state must not seed the temporal smoother
        # as though it were a new acoustic observation.
        assert recovered.human_state_engine.temporal_smoother._previous is None

    finally:
        repository.clear_session(session_id)
