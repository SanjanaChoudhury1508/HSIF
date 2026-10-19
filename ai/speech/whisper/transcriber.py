
import tempfile
import wave
from pathlib import Path

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

    def transcribe_pcm_chunk(self, audio_bytes, sample_rate=16000):
        """Transcribe one raw mono, 16-bit PCM audio chunk."""
        if not audio_bytes:
            return ""

        if len(audio_bytes) % 2 != 0:
            raise ValueError(
                "PCM audio must contain complete 16-bit samples."
            )

        temp_path = None

        try:
            with tempfile.NamedTemporaryFile(
                suffix=".wav", delete=False
            ) as temp_file:
                temp_path = Path(temp_file.name)

            with wave.open(str(temp_path), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_bytes)

            segments, _ = self.model.transcribe(str(temp_path))

            return " ".join(
                segment.text.strip()
                for segment in segments
            )

        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
