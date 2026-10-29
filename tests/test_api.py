import pytest
from pathlib import Path
from unittest.mock import Mock

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.api.process import sessions, get_pipeline_service
from backend.app.api import process as process_api

client = TestClient(app)

AUDIO_FILE = Path("tests/audio/recording.m4a")


def create_test_provider():
    provider = Mock()
    provider.generate.return_value = "Test AI response."
    return provider


def valid_process_response():
    return {
        "speech": {
            "transcript": "hello",
            "language": "en",
            "language_probability": 0.99,
            "audio": {
                "duration": 1.0,
                "speech_duration": 1.0,
                "silence_duration": 0.0,
            },
            "vad": {
                "speech_segments": [{"start": 0.0, "end": 1.0}],
                "pauses": [],
            },
            "features": {
                "number_of_pauses": 0,
                "average_pause_duration": 0.0,
                "max_pause_duration": 0.0,
                "mean_energy": 0.0,
                "mean_pitch": 0.0,
                "min_pitch": 0.0,
                "max_pitch": 0.0,
            },
        },
        "human_state": {
            "emotion": {"label": "neutral", "score": 0.0},
            "hesitation": {"score": 0.0},
            "confidence": {"score": 0.5},
            "engagement": {"score": 0.5},
            "cognitive_load": {"score": 0.0},
        },
        "dialogue": {
            "dialogue_state": {
                "emotion": "neutral",
                "emotion_score": 0.0,
                "hesitation": 0.0,
                "confidence": 0.5,
                "engagement": 0.5,
                "cognitive_load": 0.0,
                "interaction_state": "normal",
                "needs_clarification": False,
                "needs_encouragement": False,
            },
            "policy": {
                "strategy": "continue",
                "reason": "Test response",
                "priority": "normal",
            },
            "history": [],
            "prompt": "Test prompt",
        },
        "response": "hello",
    }


@pytest.fixture(autouse=True)
def mock_session_repository(monkeypatch):
    repository = Mock()
    repository.get_or_create_session.return_value = Mock()
    repository.get_turns.return_value = []

    monkeypatch.setattr(process_api, "repository", repository)
    sessions.clear()

    yield

    sessions.clear()


def test_health():
    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert data["service"] == "HSIF Backend"


def test_process_audio(monkeypatch):
    if not AUDIO_FILE.exists():
        pytest.skip("Local audio fixture recording.m4a is not available.")

    test_provider = create_test_provider()
    original_get_pipeline_service = get_pipeline_service

    def get_test_pipeline_service(session_id):
        return original_get_pipeline_service(
            session_id,
            llm_provider=test_provider,
        )

    monkeypatch.setattr(
        "backend.app.api.process.get_pipeline_service",
        get_test_pipeline_service,
    )

    with AUDIO_FILE.open("rb") as audio:
        response = client.post(
            "/api/v1/process?session_id=test-session",
            files={
                "audio": (
                    "recording.m4a",
                    audio,
                    "audio/mp4",
                )
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert "speech" in data
    assert "human_state" in data
    assert "dialogue" in data

    assert "transcript" in data["speech"]
    assert "emotion" in data["human_state"]
    assert "policy" in data["dialogue"]


def test_unsupported_audio_format():
    response = client.post(
        "/api/v1/process?session_id=test-session",
        files={
            "audio": (
                "test.txt",
                b"not an audio file",
                "text/plain",
            )
        },
    )

    assert response.status_code == 400


def test_sessions_are_isolated():
    sessions.clear()

    test_provider = create_test_provider()

    session_a_first = get_pipeline_service(
        "session-a",
        llm_provider=test_provider,
    )
    session_a_second = get_pipeline_service(
        "session-a",
        llm_provider=test_provider,
    )
    session_b = get_pipeline_service(
        "session-b",
        llm_provider=test_provider,
    )

    assert session_a_first is session_a_second
    assert session_a_first is not session_b
    assert session_a_first.dialogue_service is not session_b.dialogue_service


def test_session_conversation_histories_are_isolated():
    sessions.clear()

    test_provider = create_test_provider()

    session_a = get_pipeline_service(
        "session-a",
        llm_provider=test_provider,
    )
    session_b = get_pipeline_service(
        "session-b",
        llm_provider=test_provider,
    )

    session_a.dialogue_service.add_response(
        user_message="Hello from session A",
        assistant_message="Response for session A",
        human_state={},
        dialogue_strategy="continue",
    )

    session_b.dialogue_service.add_response(
        user_message="Hello from session B",
        assistant_message="Response for session B",
        human_state={},
        dialogue_strategy="continue",
    )

    history_a = session_a.dialogue_service.get_history()
    history_b = session_b.dialogue_service.get_history()

    assert len(history_a) == 1
    assert len(history_b) == 1

    assert history_a[0]["user_message"] == "Hello from session A"
    assert history_a[0]["assistant_message"] == "Response for session A"

    assert history_b[0]["user_message"] == "Hello from session B"
    assert history_b[0]["assistant_message"] == "Response for session B"


def test_session_state_trajectory_is_isolated():
    sessions.clear()

    test_provider = create_test_provider()

    session_a = get_pipeline_service(
        "trajectory-a",
        llm_provider=test_provider,
    )
    session_b = get_pipeline_service(
        "trajectory-b",
        llm_provider=test_provider,
    )

    sample_speech = {
        "transcript": "Test conversation turn.",
        "audio": {},
        "features": {},
        "vad": {},
    }

    session_a.human_state_engine.process(sample_speech)
    state_a_2 = session_a.human_state_engine.process(sample_speech)

    session_b.human_state_engine.process(sample_speech)

    response_a = client.get("/api/v1/session/trajectory-a/state")
    response_b = client.get("/api/v1/session/trajectory-b/state")

    assert response_a.status_code == 200
    assert response_b.status_code == 200

    data_a = response_a.json()
    data_b = response_b.json()

    assert data_a["session_id"] == "trajectory-a"
    assert data_b["session_id"] == "trajectory-b"

    assert len(data_a["trajectory"]) == 2
    assert len(data_b["trajectory"]) == 1

    assert data_a["current_state"] == state_a_2.to_dict()
    assert data_a["trajectory"][0]["step"] == 0
    assert data_a["trajectory"][1]["step"] == 1
    assert data_b["trajectory"][0]["step"] == 0


def test_missing_audio_file():
    response = client.post("/api/v1/process?session_id=test-session")

    assert response.status_code == 422


def test_missing_session_id():
    response = client.post(
        "/api/v1/process",
        files={"audio": ("test.wav", b"audio-data", "audio/wav")},
    )

    assert response.status_code == 422


def test_empty_audio_upload():
    response = client.post(
        "/api/v1/process?session_id=test-session",
        files={"audio": ("empty.wav", b"", "audio/wav")},
    )

    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_unsupported_extension_is_rejected():
    response = client.post(
        "/api/v1/process?session_id=test-session",
        files={
            "audio": (
                "malware.exe",
                b"content",
                "application/octet-stream",
            )
        },
    )

    assert response.status_code == 400
    assert "unsupported audio format" in response.json()["detail"].lower()


def test_oversized_audio_upload(monkeypatch):
    monkeypatch.setattr(process_api, "MAX_FILE_SIZE", 8)

    response = client.post(
        "/api/v1/process?session_id=test-session",
        files={"audio": ("large.wav", b"123456789", "audio/wav")},
    )

    assert response.status_code == 413


def test_pipeline_value_error_returns_400(monkeypatch):
    def failing_pipeline(session_id, llm_provider=None):
        pipeline = Mock()
        pipeline.process_audio.side_effect = ValueError("Invalid audio data")
        return pipeline

    monkeypatch.setattr(
        process_api,
        "get_pipeline_service",
        failing_pipeline,
    )

    response = client.post(
        "/api/v1/process?session_id=value-error-session",
        files={"audio": ("test.wav", b"audio-data", "audio/wav")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid audio data"


def test_pipeline_unexpected_error_returns_500(monkeypatch):
    def failing_pipeline(session_id, llm_provider=None):
        pipeline = Mock()
        pipeline.process_audio.side_effect = RuntimeError("Processing failed")
        return pipeline

    monkeypatch.setattr(
        process_api,
        "get_pipeline_service",
        failing_pipeline,
    )

    response = client.post(
        "/api/v1/process?session_id=runtime-error-session",
        files={"audio": ("test.wav", b"audio-data", "audio/wav")},
    )

    assert response.status_code == 500
    assert "Audio processing failed" in response.json()["detail"]


def test_temporary_audio_file_is_removed_after_success(monkeypatch):
    captured = {}

    def successful_pipeline(session_id, llm_provider=None):
        pipeline = Mock()

        def process_audio(path):
            captured["path"] = Path(path)
            assert captured["path"].exists()
            return valid_process_response()

        pipeline.process_audio.side_effect = process_audio
        return pipeline

    monkeypatch.setattr(
        process_api,
        "get_pipeline_service",
        successful_pipeline,
    )

    response = client.post(
        "/api/v1/process?session_id=temp-cleanup-success",
        files={"audio": ("test.wav", b"audio-data", "audio/wav")},
    )

    assert response.status_code == 200
    assert "path" in captured
    assert not captured["path"].exists()


def test_temporary_audio_file_is_removed_after_pipeline_failure(monkeypatch):
    captured = {}

    def failing_pipeline(session_id, llm_provider=None):
        pipeline = Mock()

        def process_audio(path):
            captured["path"] = Path(path)
            assert captured["path"].exists()
            raise RuntimeError("Simulated pipeline failure")

        pipeline.process_audio.side_effect = process_audio
        return pipeline

    monkeypatch.setattr(
        process_api,
        "get_pipeline_service",
        failing_pipeline,
    )

    response = client.post(
        "/api/v1/process?session_id=temp-cleanup-failure",
        files={"audio": ("test.wav", b"audio-data", "audio/wav")},
    )

    assert response.status_code == 500
    assert "path" in captured
    assert not captured["path"].exists()