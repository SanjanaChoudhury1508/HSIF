from pathlib import Path

from ai.speech.preprocessing.audio_processor import AudioProcessor
from ai.speech.vad.detector import VoiceActivityDetector
from ai.speech.feature_extraction.acoustic_features import (
    AcousticFeatureExtractor,
)


def test_audio_features():
    input_path = Path("tests/audio/recording.m4a")
    processed_path = Path("tests/audio/test_features_processed.wav")

    processor = AudioProcessor()
    processor.convert_to_wav(input_path, processed_path)

    try:
        vad = VoiceActivityDetector()
        vad_result = vad.detect(processed_path)

        extractor = AcousticFeatureExtractor()
        features = extractor.extract(
            processed_path,
            vad_result,
        )

        assert isinstance(features, dict)
        assert features
        assert features["duration"] > 0
        assert features["speech_duration"] > 0
        assert features["number_of_pauses"] >= 0
        assert features["mean_energy"] >= 0
        assert features["mean_pitch"] >= 0
        assert features["min_pitch"] >= 0
        assert features["max_pitch"] >= 0

    finally:
        if processed_path.exists():
            processed_path.unlink()