import json
from unittest.mock import Mock
from uuid import uuid4
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.api import streaming as streaming_api
from backend.app.services.pipeline_service import PipelineService
from database.repository import SessionRepository


client = TestClient(app)


def test_websocket_completes_and_persists_real_pipeline_turn(monkeypatch):
    repository = SessionRepository()
    session_id = str(uuid4())
    transcript = "I need help understanding this topic."
    assistant_response = "Let's break it into smaller steps."

    speech_result = {
        "transcript": transcript,
        "language": "en",
        "language_probability": 0.99,
        "audio": {
            "duration": 1.0,
            "speech_duration": 0.8,
            "silence_duration": 0.2,
        },
        "vad": {
            "speech_segments": [{"start": 0.1, "end": 0.9}],
            "pause_count": 0,
            "longest_pause": 0.0,
            "speech_to_silence_ratio": 4.0,
            "pauses": [],
        },
        "features": {
            "number_of_pauses": 0,
            "average_pause_duration": 0.0,
            "max_pause_duration": 0.0,
            "mean_energy": 0.0,
            "std_energy": 0.0,
            "mean_pitch": 0.0,
            "std_pitch": 0.0,
            "min_pitch": 0.0,
            "max_pitch": 0.0,
            "speech_rate": 0.0,
        },
    }

    llm_provider = Mock()
    llm_provider.generate.return_value = assistant_response

    pipeline = PipelineService(
        llm_provider=llm_provider,
        session_id=session_id,
        repository=repository,
    )

    # Replace only the external speech-processing operation.
    pipeline.speech_service.process = Mock(return_value=speech_result)

    monkeypatch.setattr(
        streaming_api,
        "get_pipeline_service",
        lambda requested_session_id: (
            pipeline
            if requested_session_id == session_id
            else None
        ),
    )

    try:
        with client.websocket_connect(
            f"/ws/session/{session_id}"
        ) as websocket:
            websocket.send_text(json.dumps({
                "type": "start_session",
                "audio": {
                    "encoding": "pcm_s16le",
                    "sample_rate": 16000,
                    "channels": 1,
                },
            }))

            ready = websocket.receive_json()
            assert ready["type"] == "session_ready"

            # One second of mono PCM16 audio at 16 kHz.
            websocket.send_bytes(b"\x00\x00" * 16000)

            chunk_event = websocket.receive_json()
            assert chunk_event["type"] == "speech_chunk"

            websocket.send_text(json.dumps({
                "type": "end_turn",
                "turn_id": "integration-turn-1",
            }))

            received = {}
            expected = {
                "transcript_final",
                "human_state_update",
                "dialogue_strategy",
                "assistant_response",
            }

            for _ in range(4):
                event = websocket.receive_json()
                received[event["type"]] = event

            assert expected.issubset(received)

            assert received["transcript_final"]["text"] == transcript
            assert received["transcript_final"]["turn_id"] == (
                "integration-turn-1"
            )
            assert received["human_state_update"]["final"] is True
            assert received["dialogue_strategy"]["strategy"]
            assert (
                received["assistant_response"]["text"]
                == assistant_response
            )

            websocket.send_text(json.dumps({"type": "end_session"}))
            assert websocket.receive_json()["type"] == "session_ended"

        # Verify the completed turn was stored in PostgreSQL.
        turns = repository.get_turns(session_id, limit=10)

        assert len(turns) == 1
        assert turns[0].user_message == transcript
        assert turns[0].assistant_message == assistant_response
        assert turns[0].dialogue_strategy == (
            received["dialogue_strategy"]["strategy"]
        )

        # Verify persisted state is present and usable.
        state = turns[0].human_state
        assert state["emotion"]["label"]
        assert state["_temporal"]["observation_valid"] is True

        # Simulate a restart and verify history restoration.
        recovered = PipelineService(
            session_id=session_id,
            repository=repository,
        )

        history = recovered.dialogue_service.get_history()
        assert len(history) == 1
        assert history[0]["user_message"] == transcript
        assert history[0]["assistant_message"] == assistant_response

        trajectory = recovered.human_state_engine.get_state_trajectory()
        assert len(trajectory) == 1
        assert trajectory[0]["emotion"]["label"] == state["emotion"]["label"]

        llm_provider.generate.assert_called_once()

    finally:
        repository.clear_session(session_id)
