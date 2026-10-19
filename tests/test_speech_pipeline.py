from pathlib import Path

import pytest

from ai.speech.preprocessing.audio_processor import AudioProcessor
from ai.speech.whisper.transcriber import SpeechTranscriber


INPUT_AUDIO = Path("tests/audio/recording.m4a")
PROCESSED_AUDIO = Path("tests/audio/processed.wav")


def test_speech_pipeline():
    if not INPUT_AUDIO.exists():
        pytest.skip("Local audio fixture recording.m4a is not available.")

    processor = AudioProcessor()

    processor.convert_to_wav(
        str(INPUT_AUDIO),
        str(PROCESSED_AUDIO),
    )

    assert PROCESSED_AUDIO.exists()

    transcriber = SpeechTranscriber()

    result = transcriber.transcribe(str(PROCESSED_AUDIO))

    assert isinstance(result, dict)
    assert "text" in result
    assert "language" in result
    assert "language_probability" in result