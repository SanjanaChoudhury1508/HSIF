from pathlib import Path

from ai.speech.preprocessing.audio_processor import AudioProcessor
from ai.speech.vad.detector import VoiceActivityDetector
from ai.speech.whisper.transcriber import SpeechTranscriber
from ai.speech.feature_extraction.acoustic_features import (
    AcousticFeatureExtractor
)


class SpeechService:

    def __init__(self):
        self.audio_processor = AudioProcessor()
        self.vad = VoiceActivityDetector()
        self.transcriber = SpeechTranscriber()
        self.feature_extractor = AcousticFeatureExtractor()

    def process(self, audio_path):
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(
                f"Audio file not found: {audio_path}"
            )
        processed_path = (
            audio_path.parent /
            f"{audio_path.stem}_processed.wav"
        )

        self.audio_processor.convert_to_wav(
            audio_path,
            processed_path
        )

        vad_result = self.vad.detect(
            processed_path
        )

        transcription = self.transcriber.transcribe(
            processed_path
        )

        features = self.feature_extractor.extract(
            processed_path,
            vad_result
        )

        return {
            "transcript": transcription["text"],
            "language": transcription["language"],
            "language_probability": (
                transcription["language_probability"]
            ),
            "audio": {
                "duration": round(vad_result["duration"], 3),
                "speech_duration": round(
                    vad_result["speech_duration"],3
                ),
                "silence_duration": round(
                    vad_result["silence_duration"], 3
                )
            },
            "vad": {
                "speech_segments": (
                    vad_result["speech_segments"]
                ),
                "pauses": [
                    {
                        "start": round(pause["start"], 3),
                        "end": round(pause["end"], 3),
                        "duration": round(pause["duration"], 3)
                    }
                    for pause in vad_result["pauses"]
                ]
            },
            "features": {
                "number_of_pauses": (
                    features["number_of_pauses"]
                ),
                "average_pause_duration": round(
                    features["average_pause_duration"], 3
                ),
                "max_pause_duration": round(
                    features["max_pause_duration"], 3
                ),
                "mean_energy": round(
                    features["mean_energy"], 4
                ),
                "mean_pitch": round(
                    features["mean_pitch"], 2
                ),
                "min_pitch": round(
                    features["min_pitch"], 2
                ),
                "max_pitch": round(
                    features["max_pitch"], 2
                )
            }
        }