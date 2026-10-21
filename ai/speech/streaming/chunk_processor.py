
import numpy as np


class StreamingAudioProcessor:
    """Process mono, 16 kHz, signed 16-bit PCM audio chunks."""

    def __init__(self, sample_rate=16000, energy_threshold=0.01):
        if sample_rate <= 0:
            raise ValueError("sample_rate must be positive.")
        if energy_threshold < 0:
            raise ValueError("energy_threshold cannot be negative.")

        self.sample_rate = sample_rate
        self.energy_threshold = energy_threshold
        self.total_audio_duration = 0.0
        self.total_speech_duration = 0.0
        self._in_speech = False
        self._speech_start = None
        self._last_speech_end = None
        self._pause_count = 0
        self._pauses = []

    def process_chunk(self, audio_bytes):
        """Return chunk metrics, timestamps, and speech-transition events."""
        if not audio_bytes:
            return {
                "duration": 0.0,
                "is_speech": False,
                "speech_duration": self.total_speech_duration,
                "total_duration": self.total_audio_duration,
                "start": self.total_audio_duration,
                "end": self.total_audio_duration,
                "energy": 0.0,
                "speech_event": None,
                "pause": None,
                "pause_count": self._pause_count,
            }

        if len(audio_bytes) % 2 != 0:
            raise ValueError("PCM audio must contain complete 16-bit samples.")

        audio = (
            np.frombuffer(audio_bytes, dtype="<i2").astype(np.float32)
            / 32768.0
        )

        if audio.size == 0:
            return self.process_chunk(b"")

        duration = audio.size / self.sample_rate
        start = self.total_audio_duration
        end = start + duration
        energy = float(np.sqrt(np.mean(audio ** 2)))
        is_speech = energy > self.energy_threshold

        speech_event = None
        pause = None

        if is_speech and not self._in_speech:
            speech_event = "speech_start"
            self._speech_start = start

            if self._last_speech_end is not None:
                pause_duration = max(0.0, start - self._last_speech_end)
                pause = {
                    "start": self._last_speech_end,
                    "end": start,
                    "duration": pause_duration,
                }
                self._pauses.append(pause)
                self._pause_count += 1

        elif not is_speech and self._in_speech:
            speech_event = "speech_end"
            self._last_speech_end = start

        self._in_speech = is_speech
        self.total_audio_duration = end

        if is_speech:
            self.total_speech_duration += duration

        return {
            "duration": duration,
            "is_speech": bool(is_speech),
            "speech_duration": self.total_speech_duration,
            "total_duration": self.total_audio_duration,
            "start": start,
            "end": end,
            "energy": energy,
            "speech_event": speech_event,
            "pause": pause,
            "pause_count": self._pause_count,
        }

    def process_chunk_with_transcription(self, audio_bytes, transcribe_chunk=None):
        """Process a chunk and optionally obtain a transcript."""
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
        self._in_speech = False
        self._speech_start = None
        self._last_speech_end = None
        self._pause_count = 0
        self._pauses.clear()