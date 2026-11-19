import librosa
import numpy as np


class AcousticFeatureExtractor:
    MIN_PITCH_SEGMENT_SAMPLES = 2048

    def __init__(self, sample_rate=16000):
        self.sample_rate = sample_rate

    def extract_pitch(self, audio):
        return self._pitch_summary(self._extract_pitch_values(audio))

    def _extract_pitch_values(self, audio):
        audio = np.asarray(audio, dtype=float)
        if audio.ndim != 1 or len(audio) < self.MIN_PITCH_SEGMENT_SAMPLES:
            return np.array([], dtype=float)

        try:
            f0, _, _ = librosa.pyin(
                audio,
                fmin=librosa.note_to_hz("C2"),
                fmax=librosa.note_to_hz("C7"),
                sr=self.sample_rate
            )
        except (ValueError, IndexError):
            return np.array([], dtype=float)

        valid_pitch = np.asarray(f0, dtype=float)
        valid_pitch = valid_pitch[np.isfinite(valid_pitch)]
        return valid_pitch

    @staticmethod
    def _pitch_summary(valid_pitch):
        if len(valid_pitch) == 0:
            return {
                "mean_pitch": 0.0,
                "std_pitch": 0.0,
                "min_pitch": 0.0,
                "max_pitch": 0.0
            }

        return {
            "mean_pitch": float(np.mean(valid_pitch)),
            "std_pitch": float(np.std(valid_pitch)),
            "min_pitch": float(np.min(valid_pitch)),
            "max_pitch": float(np.max(valid_pitch))
        }

    def _speech_audio_segments(self, audio, vad_result):
        segments = vad_result.get("speech_segments")
        if segments is None:
            # Keep compatibility with older VAD results that did not include
            # segment boundaries. Current VAD always supplies this field.
            return [audio] if len(audio) else []

        audio_duration = len(audio) / self.sample_rate
        intervals = []
        for segment in segments:
            if not isinstance(segment, dict):
                continue
            try:
                start = float(segment["start"])
                end = float(segment["end"])
            except (KeyError, TypeError, ValueError, OverflowError):
                continue

            if not np.isfinite(start) or not np.isfinite(end) or end <= start:
                continue

            start = max(0.0, min(start, audio_duration))
            end = max(0.0, min(end, audio_duration))
            start_index = int(start * self.sample_rate)
            end_index = int(end * self.sample_rate)
            if end_index > start_index:
                intervals.append((start_index, end_index))

        # VAD normally returns ordered, disjoint ranges. Normalize defensively
        # so overlapping or unordered caller-provided ranges do not duplicate
        # audio and distort energy or pitch features.
        merged_intervals = []
        for start_index, end_index in sorted(intervals):
            if merged_intervals and start_index <= merged_intervals[-1][1]:
                previous_start, previous_end = merged_intervals[-1]
                merged_intervals[-1] = (
                    previous_start,
                    max(previous_end, end_index),
                )
            else:
                merged_intervals.append((start_index, end_index))

        return [audio[start:end] for start, end in merged_intervals]

    def extract(self, audio_path, vad_result, transcript=""):
        audio, _ = librosa.load(
            audio_path,
            sr=self.sample_rate,
            mono=True
        )

        pauses = vad_result.get("pauses", [])
        pause_durations = [
            float(pause["duration"])
            for pause in pauses
            if isinstance(pause, dict)
            and isinstance(pause.get("duration"), (int, float))
            and np.isfinite(pause["duration"])
        ]

        speech_segments = self._speech_audio_segments(audio, vad_result)
        speech_audio = (
            np.concatenate(speech_segments)
            if speech_segments
            else np.array([], dtype=float)
        )
        if len(speech_audio):
            mean_energy = float(np.sqrt(np.mean(speech_audio ** 2)))
            std_energy = float(np.std(speech_audio))
            # Pitch is estimated independently per sufficiently long segment.
            # Concatenating segments before pYIN would invent a continuous
            # waveform at each VAD boundary; short fragments cannot support a
            # stable pitch estimate even when their combined length is large.
            pitch_values = [
                self._extract_pitch_values(segment)
                for segment in speech_segments
                if len(segment) >= self.MIN_PITCH_SEGMENT_SAMPLES
            ]
            pitch_values = [values for values in pitch_values if len(values)]
            pitch_features = self._pitch_summary(
                np.concatenate(pitch_values)
                if pitch_values
                else np.array([], dtype=float)
            )
        else:
            mean_energy = 0.0
            std_energy = 0.0
            pitch_features = self._pitch_summary(np.array([], dtype=float))

        average_pause_duration = (
            float(np.mean(pause_durations))
            if pause_durations
            else 0.0
        )

        max_pause_duration = (
            float(np.max(pause_durations))
            if pause_durations
            else 0.0
        )

        speech_duration = vad_result.get("speech_duration", 0.0)

        words = transcript.split()
        word_count = len(words)

        speech_rate = (
            word_count / speech_duration
            if speech_duration > 0
            else 0.0
        )

        return {
            "duration": vad_result.get("duration", 0.0),
            "speech_duration": speech_duration,
            "silence_duration": vad_result.get("silence_duration", 0.0),
            "number_of_pauses": len(pauses),
            "average_pause_duration": average_pause_duration,
            "max_pause_duration": max_pause_duration,
            "mean_energy": mean_energy,
            "std_energy": std_energy,
            "mean_pitch": pitch_features["mean_pitch"],
            "std_pitch": pitch_features["std_pitch"],
            "min_pitch": pitch_features["min_pitch"],
            "max_pitch": pitch_features["max_pitch"],
            "speech_rate": speech_rate,
            "pauses": pauses
        }
