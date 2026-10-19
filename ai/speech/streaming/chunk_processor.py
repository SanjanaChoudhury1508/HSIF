import numpy as np


class StreamingAudioProcessor:
    """
    Processes raw mono, 16 kHz, signed 16-bit PCM audio chunks.
    Uses an energy threshold for basic speech detection.
    """

    def __init__(
        self,
        sample_rate=16000,
        energy_threshold=0.01
    ):
        self.sample_rate = sample_rate
        self.energy_threshold = energy_threshold
        self.total_audio_duration = 0.0
        self.total_speech_duration = 0.0

    def process_chunk(self, audio_bytes):
        """Process one raw PCM audio chunk."""

        if not audio_bytes:
            return {
                "duration": 0.0,
                "is_speech": False,
                "speech_duration": self.total_speech_duration,
                "total_duration": self.total_audio_duration
            }

        if len(audio_bytes) % 2 != 0:
            raise ValueError(
                "PCM audio must contain complete 16-bit samples."
            )

        audio = np.frombuffer(
            audio_bytes,
            dtype="<i2"
        ).astype(np.float32) / 32768.0

        if audio.size == 0:
            return {
                "duration": 0.0,
                "is_speech": False,
                "speech_duration": self.total_speech_duration,
                "total_duration": self.total_audio_duration
            }

        duration = audio.size / self.sample_rate
        energy = float(np.sqrt(np.mean(audio ** 2)))
        is_speech = energy > self.energy_threshold

        self.total_audio_duration += duration

        if is_speech:
            self.total_speech_duration += duration

        return {
            "duration": duration,
            "is_speech": bool(is_speech),
            "speech_duration": self.total_speech_duration,
            "total_duration": self.total_audio_duration
        }

    def process_chunk_with_transcription(
        self,
        audio_bytes,
        transcribe_chunk=None
    ):
        """Process a chunk and optionally obtain a partial transcript."""

        result = self.process_chunk(audio_bytes)
        partial_transcript = ""

        if (
            transcribe_chunk is not None
            and audio_bytes
            and result["duration"] > 0
        ):
            partial_transcript = transcribe_chunk(audio_bytes)

        result["partial_transcript"] = partial_transcript
        return result

    def reset(self):
        """Reset cumulative streaming state."""

        self.total_audio_duration = 0.0
        self.total_speech_duration = 0.0