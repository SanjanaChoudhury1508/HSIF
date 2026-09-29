from pathlib import Path

import pytest

from ai.speech.vad.detector import VoiceActivityDetector


AUDIO_PATH = Path("tests/audio/processed.wav")


def test_vad():
    if not AUDIO_PATH.exists():
        pytest.skip("Local audio fixture processed.wav is not available.")

    vad = VoiceActivityDetector()

    result = vad.detect(str(AUDIO_PATH))

    assert isinstance(result, dict)
    assert "duration" in result
    assert "speech_duration" in result
    assert "silence_duration" in result
    assert "speech_segments" in result