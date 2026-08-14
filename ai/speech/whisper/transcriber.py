from faster_whisper import WhisperModel


class SpeechTranscriber:
    def __init__(self, model_size="base"):
        self.model = WhisperModel(
            model_size,
            device="cpu",
            compute_type="int8"
        )

    def transcribe(self, audio_path):
        segments, info = self.model.transcribe(audio_path)

        text = " ".join(
            segment.text.strip()
            for segment in segments
        )

        return {
            "text": text,
            "language": info.language,
            "language_probability": info.language_probability
        }