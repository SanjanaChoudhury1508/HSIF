from pathlib import Path

import pytest

from ai.speech.preprocessing.audio_processor import AudioProcessor


INPUT_AUDIO = Path("tests/audio/recording.m4a")
OUTPUT_AUDIO = Path("tests/audio/processed.wav")


def test_audio_preprocessing():
    if not INPUT_AUDIO.exists():
        pytest.skip("Local audio fixture recording.m4a is not available.")

    processor = AudioProcessor()

    result = processor.convert_to_wav(
        str(INPUT_AUDIO),
        str(OUTPUT_AUDIO),
    )

    assert result
    assert OUTPUT_AUDIO.exists()