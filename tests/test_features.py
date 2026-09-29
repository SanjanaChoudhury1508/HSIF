from pathlib import Path

import pytest

from ai.speech.vad.detector import VoiceActivityDetector
from ai.speech.feature_extraction.acoustic_features import (
    AcousticFeatureExtractor,
)


AUDIO_PATH = Path("tests/audio/processed.wav")


def test_audio_features():
    if not AUDIO_PATH.exists():
        pytest.skip("Local audio fixture processed.wav is not available.")

    vad = VoiceActivityDetector()
    vad_result = vad.detect(str(AUDIO_PATH))

    extractor = AcousticFeatureExtractor()

    features = extractor.extract(
        str(AUDIO_PATH),
        vad_result,
    )

    assert isinstance(features, dict)
    assert features