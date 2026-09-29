from pathlib import Path

import pytest

from ai.speech.whisper.transcriber import SpeechTranscriber


AUDIO_PATH = Path("tests/audio/sample.wav")


def test_transcription():
    if not AUDIO_PATH.exists():
        pytest.skip("Local audio fixture sample.wav is not available.")

    transcriber = SpeechTranscriber()

    result = transcriber.transcribe(str(AUDIO_PATH))

    assert isinstance(result, dict)
    assert "text" in result
    assert "language" in result
    assert "language_probability" in result