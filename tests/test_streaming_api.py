import json
import pytest
from unittest.mock import Mock
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.api import streaming as streaming_api
from backend.app.api.process import sessions
from starlette.websockets import WebSocketDisconnect

client = TestClient(app)


def make_pipeline():
    pipeline = Mock()
    
    pipeline.process_audio.return_value = {
        "speech": {
            "transcript": "Hello there.",
            "language": "en",
            "language_probability": 0.99,
            "audio": {
                "duration": 1.0,
                "speech_duration": 0.8,
                "silence_duration": 0.2,
            },
            "vad": {
                "speech_segments": [],
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
        },
        "human_state": {"emotion": "calm"},
        "dialogue": {
            "strategy": "continue",
            "reason": "The user greeted the assistant.",
            "policy": {
                "strategy": "continue",
                "reason": "The user greeted the assistant.",
            },
        },
        "response": "Hi! How can I help?",
    }

    pipeline.speech_service.transcriber.transcribe_pcm_chunk.return_value = (
        "Hello there."
    )
    return pipeline


def start_session(websocket):
    websocket.send_text(json.dumps({
        "type": "start_session",
        "audio": {
            "encoding": "pcm_s16le",
            "sample_rate": 16000,
            "channels": 1,
        },
    }))
    return websocket.receive_json()



def test_websocket_rejects_invalid_session_id():
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws/session/not-a-uuid"):
            pass

    assert exc_info.value.code == 1008


def test_websocket_requires_start_session():
    session_id = str(uuid4())

    with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
        websocket.send_bytes(b"\x00\x00")
        event = websocket.receive_json()

        assert event["type"] == "error"
        assert event["code"] == "SESSION_NOT_STARTED"


def test_websocket_streams_chunk_and_returns_final_events(monkeypatch):
    session_id = str(uuid4())
    pipeline = make_pipeline()

    monkeypatch.setattr(
        streaming_api,
        "get_pipeline_service",
        lambda _session_id: pipeline,
    )

    with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
        ready = start_session(websocket)

        assert ready["type"] == "session_ready"
        assert ready["session_id"] == session_id

        # 1 second of valid mono PCM16 audio at 16 kHz.
        audio_chunk = b"\x00\x00" * 16000
        websocket.send_bytes(audio_chunk)

        chunk_event = websocket.receive_json()
        assert chunk_event["type"] == "speech_chunk"
        assert chunk_event["chunk_index"] == 1
        assert chunk_event["duration"] == 1.0
        assert "energy" in chunk_event
        assert "speech_event" in chunk_event

        websocket.send_text(json.dumps({
            "type": "end_turn",
            "turn_id": "turn-1",
        }))

        received = []
        expected = {
            "transcript_final",
            "human_state_update",
            "dialogue_strategy",
            "assistant_response",
        }

        
        for _ in range(10):
            if expected.issubset({event["type"] for event in received}):
                break
        
            received.append(websocket.receive_json())
            event=websocket.receive_json()
            print("Received event:", event)
            received.append(event)
        
        actual = {event["type"] for event in received}
        assert expected.issubset(actual), f"Missing events: {expected - actual}; received: {received}"


        events = {event["type"]: event for event in received}

        assert events["transcript_final"]["text"] == "Hello there."
        assert events["transcript_final"]["turn_id"] == "turn-1"
        assert events["human_state_update"]["state"]["emotion"] == "calm"
        assert events["dialogue_strategy"]["strategy"] == "continue"
        assert events["assistant_response"]["text"] == "Hi! How can I help?"

        pipeline.process_audio.assert_called_once()

        websocket.send_text(json.dumps({"type": "end_session"}))
        ended = websocket.receive_json()
        assert ended["type"] == "session_ended"


def test_websocket_rejects_invalid_audio_configuration(monkeypatch):
    session_id = str(uuid4())

    with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
        websocket.send_text(json.dumps({
            "type": "start_session",
            "audio": {
                "encoding": "mp3",
                "sample_rate": 44100,
                "channels": 2,
            },
        }))

        # The endpoint closes the connection for an unsupported configuration.
        try:
            event = websocket.receive_json()
        except Exception:
            event = None

        assert event is None or event.get("type") == "error"
