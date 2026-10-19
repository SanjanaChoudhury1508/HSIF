from pathlib import Path

import pytest

from ai.speech.speech_service import SpeechService


AUDIO_PATH = Path("tests/audio/recording.m4a")


def test_speech_service():
    if not AUDIO_PATH.exists():
        pytest.skip("Local audio fixture recording.m4a is not available.")

    speech_service = SpeechService()

    result = speech_service.process(str(AUDIO_PATH))

    assert isinstance(result, dict)
    assert "transcript" in result