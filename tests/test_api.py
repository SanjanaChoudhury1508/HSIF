from pathlib import Path
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

AUDIO_FILE = Path("tests/audio/recording.m4a")

def test_health():
    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert data["service"] == "HSIF Backend"


def test_process_audio():
    with AUDIO_FILE.open("rb") as audio:
        response = client.post(
            "/api/v1/process",
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
        "/api/v1/process",
        files={
            "audio": (
                "test.txt",
                b"not an audio file",
                "text/plain"
            )
        }
    )

    assert response.status_code == 400