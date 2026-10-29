from pathlib import Path
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

def test_websocket_handles_session_initialization_failure(monkeypatch):
    session_id = str(uuid4())

    def fail_initialization(*args, **kwargs):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(
        streaming_api,
        "get_pipeline_service",
        fail_initialization,
    )

    with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
        websocket.send_text(json.dumps({
            "type": "start_session",
            "audio": {
                "encoding": "pcm_s16le",
                "sample_rate": 16000,
                "channels": 1,
            },
        }))

        event = websocket.receive_json()
        assert event["type"] == "error"
        assert event["code"] == "SESSION_INITIALIZATION_FAILED"
        assert event["recoverable"] is False

        with pytest.raises(WebSocketDisconnect) as exc_info:
            websocket.receive_json()

        assert exc_info.value.code == 1011


def test_websocket_handles_final_pipeline_failure(monkeypatch):
    session_id = str(uuid4())
    pipeline = make_pipeline()
    pipeline.process_audio.side_effect = RuntimeError("pipeline failed")

    monkeypatch.setattr(
        streaming_api,
        "get_pipeline_service",
        lambda *_args, **_kwargs: pipeline,
    )

    with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
        ready = start_session(websocket)
        assert ready["type"] == "session_ready"

        websocket.send_bytes(b"\x00\x00" * 16000)

        chunk_event = websocket.receive_json()
        assert chunk_event["type"] == "speech_chunk"

        websocket.send_text(json.dumps({
            "type": "end_turn",
            "turn_id": "turn-failure",
        }))

        event = websocket.receive_json()
        assert event["type"] == "error"
        assert event["code"] == "PIPELINE_FAILED"
        assert event["turn_id"] == "turn-failure"
        assert event["recoverable"] is True

        # The connection should remain usable after a failed turn.
        websocket.send_text(json.dumps({"type": "ping"}))
        pong = websocket.receive_json()
        assert pong["type"] == "pong"


def test_websocket_handles_invalid_json():
    session_id = str(uuid4())

    with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
        websocket.send_text("{invalid json")

        event = websocket.receive_json()
        assert event["type"] == "error"
        assert event["code"] == "INVALID_JSON"
        assert event["recoverable"] is True


def test_websocket_rejects_non_object_control_message():
    session_id = str(uuid4())

    with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
        websocket.send_text(json.dumps(["start_session"]))

        event = websocket.receive_json()
        assert event["type"] == "error"
        assert event["code"] == "INVALID_MESSAGE"
        assert event["recoverable"] is True


def test_websocket_rejects_duplicate_start_session(monkeypatch):
    session_id = str(uuid4())
    pipeline = make_pipeline()

    monkeypatch.setattr(
        streaming_api,
        "get_pipeline_service",
        lambda *_args, **_kwargs: pipeline,
    )

    with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
        first = start_session(websocket)
        assert first["type"] == "session_ready"

        websocket.send_text(json.dumps({
            "type": "start_session",
            "audio": {
                "encoding": "pcm_s16le",
                "sample_rate": 16000,
                "channels": 1,
            },
        }))

        event = websocket.receive_json()
        assert event["type"] == "error"
        assert event["code"] == "SESSION_ALREADY_STARTED"


def test_websocket_recovers_after_oversized_audio(monkeypatch):
    session_id = str(uuid4())
    pipeline = make_pipeline()

    monkeypatch.setattr(
        streaming_api,
        "MAX_AUDIO_BYTES",
        8,
    )
    monkeypatch.setattr(
        streaming_api,
        "get_pipeline_service",
        lambda *_args, **_kwargs: pipeline,
    )

    with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
        ready = start_session(websocket)
        assert ready["type"] == "session_ready"

        websocket.send_bytes(b"\x00" * 10)

        error = websocket.receive_json()
        assert error["type"] == "error"
        assert error["code"] == "AUDIO_TOO_LARGE"
        assert error["recoverable"] is True

        # Restore a realistic limit before sending a valid turn.
        monkeypatch.setattr(
            streaming_api,
            "MAX_AUDIO_BYTES",
            10 * 1024 * 1024,
        )

        # A fresh turn should work on the same connection.
        websocket.send_bytes(b"\x00\x00" * 16000)
        chunk_event = websocket.receive_json()
        assert chunk_event["type"] == "speech_chunk"

        websocket.send_text(json.dumps({
            "type": "end_turn",
            "turn_id": "turn-after-oversize",
        }))

        received = []
        expected = {
            "transcript_final",
            "human_state_update",
            "dialogue_strategy",
            "assistant_response",
        }

        for _ in range(6):
            event = websocket.receive_json()
            received.append(event)
            if expected.issubset({item["type"] for item in received}):
                break

        assert expected.issubset({item["type"] for item in received})
        pipeline.process_audio.assert_called_once()

def test_websocket_removes_temporary_wav_after_pipeline_failure(
    monkeypatch, tmp_path
):
    session_id = str(uuid4())
    pipeline = make_pipeline()
    pipeline.process_audio.side_effect = RuntimeError("pipeline failed")

    created_paths = []
    original_named_temporary_file = streaming_api.tempfile.NamedTemporaryFile

    def tracked_temporary_file(*args, **kwargs):
        temp_file = original_named_temporary_file(*args, **kwargs)
        created_paths.append(Path(temp_file.name))
        return temp_file

    monkeypatch.setattr(
        streaming_api.tempfile,
        "NamedTemporaryFile",
        tracked_temporary_file,
    )
    monkeypatch.setattr(
        streaming_api,
        "get_pipeline_service",
        lambda *_args, **_kwargs: pipeline,
    )

    with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
        assert start_session(websocket)["type"] == "session_ready"

        websocket.send_bytes(b"\x00\x00" * 16000)
        assert websocket.receive_json()["type"] == "speech_chunk"

        websocket.send_text(json.dumps({
            "type": "end_turn",
            "turn_id": "cleanup-failure",
        }))

        event = websocket.receive_json()
        assert event["type"] == "error"
        assert event["code"] == "PIPELINE_FAILED"

    assert len(created_paths) == 1
    assert not created_paths[0].exists()


def test_websocket_recovers_after_invalid_pcm_chunk(monkeypatch):
    session_id = str(uuid4())
    pipeline = make_pipeline()

    class FailingProcessor:
        def __init__(self, sample_rate):
            self.sample_rate = sample_rate
            self.reset_count = 0

        def process_chunk(self, chunk):
            if chunk == b"invalid":
                raise ValueError("Invalid PCM chunk")
            return {
                "duration": 0.0,
                "total_duration": 0.0,
                "speech_duration": 0.0,
                "is_speech": False,
                "start": 0.0,
                "end": 0.0,
                "energy": 0.0,
                "speech_event": None,
                "pause": None,
                "pause_count": 0,
            }

        def reset(self):
            self.reset_count += 1

    monkeypatch.setattr(
        streaming_api,
        "StreamingAudioProcessor",
        FailingProcessor,
    )
    monkeypatch.setattr(
        streaming_api,
        "get_pipeline_service",
        lambda *_args, **_kwargs: pipeline,
    )

    with client.websocket_connect(f"/ws/session/{session_id}") as websocket:
        assert start_session(websocket)["type"] == "session_ready"

        websocket.send_bytes(b"invalid")
        error = websocket.receive_json()
        assert error["type"] == "error"
        assert error["code"] == "INVALID_PCM"
        assert error["recoverable"] is True

        # A valid chunk should still be accepted after the bad chunk.
        websocket.send_bytes(b"\x00\x00")
        event = websocket.receive_json()
        assert event["type"] == "speech_chunk"
        assert event["chunk_index"] == 1