from ai.speech.vad.detector import VoiceActivityDetector
from ai.speech.feature_extraction.acoustic_features import (
    AcousticFeatureExtractor
)


audio_path = "tests/audio/processed.wav"


vad = VoiceActivityDetector()

vad_result = vad.detect(audio_path)


extractor = AcousticFeatureExtractor()

features = extractor.extract(
    audio_path,
    vad_result
)


print("Audio Features")
print("--------------------")

for key, value in features.items():
    print(f"{key}: {value}")