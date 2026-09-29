import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.api.process import sessions, get_pipeline_service

client = TestClient(app)

AUDIO_FILE = Path("tests/audio/recording.m4a")


def test_health():
    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert data["service"] == "HSIF Backend"


def test_process_audio():
    if not AUDIO_FILE.exists():
        pytest.skip("Local audio fixture recording.m4a is not available.")

    with AUDIO_FILE.open("rb") as audio:
        response = client.post(
            "/api/v1/process?session_id=test-session",
            files={
                "audio": (
                    "recording.m4a",
                    audio,
                    "audio/mp4"
                )
            }
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
                "text/plain"
            )
        }
    )

    assert response.status_code == 400

def test_sessions_are_isolated():
    sessions.clear()

    session_a_first = get_pipeline_service("session-a")
    session_a_second = get_pipeline_service("session-a")
    session_b = get_pipeline_service("session-b")

    assert session_a_first is session_a_second
    assert session_a_first is not session_b

    assert session_a_first.dialogue_service is not session_b.dialogue_service
    
def test_session_conversation_histories_are_isolated():
    sessions.clear()

    session_a = get_pipeline_service("session-a")
    session_b = get_pipeline_service("session-b")

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