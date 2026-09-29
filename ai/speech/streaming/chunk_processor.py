import io

import librosa
import numpy as np


class StreamingAudioProcessor:
    """
    Processes progressively received audio chunks.

    Each chunk is converted into mono 16 kHz audio and passed
    through a lightweight energy-based VAD.
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
        """
        Process one audio chunk.

        Returns:
            dict containing chunk duration, speech status,
            and cumulative speech/audio duration.
        """

        if not audio_bytes:
            return {
                "duration": 0.0,
                "is_speech": False,
                "speech_duration": self.total_speech_duration,
                "total_duration": self.total_audio_duration
            }

        audio, _ = librosa.load(
            io.BytesIO(audio_bytes),
            sr=self.sample_rate,
            mono=True
        )

        if len(audio) == 0:
            return {
                "duration": 0.0,
                "is_speech": False,
                "speech_duration": self.total_speech_duration,
                "total_duration": self.total_audio_duration
            }

        duration = len(audio) / self.sample_rate
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
        """
        Process an audio chunk and optionally generate
        a partial transcript using a supplied transcription function.
        """

        result = self.process_chunk(audio_bytes)

        partial_transcript = ""

        if transcribe_chunk is not None and audio_bytes:
            partial_transcript = transcribe_chunk(audio_bytes)

        result["partial_transcript"] = partial_transcript

        return result

    def reset(self):
        """Reset cumulative streaming state."""

        self.total_audio_duration = 0.0
        self.total_speech_duration = 0.0