import librosa
import numpy as np


class VoiceActivityDetector:
    def __init__(
        self,
        frame_duration=0.03,
        energy_threshold=0.01
    ):
        self.frame_duration = frame_duration
        self.energy_threshold = energy_threshold

    def detect_frames(self, audio_path):
        audio, sample_rate = librosa.load(
            audio_path,
            sr=16000,
            mono=True
        )

        frame_size = int(
            self.frame_duration * sample_rate
        )

        frames = []

        for start in range(0, len(audio), frame_size):
            frame = audio[start:start + frame_size]

            if len(frame) == 0:
                continue

            energy = np.sqrt(
                np.mean(frame ** 2)
            )

            is_speech = energy > self.energy_threshold

            frames.append({
                "start": start / sample_rate,
                "end": min(
                    (start + frame_size) / sample_rate,
                    len(audio) / sample_rate
                ),
                "is_speech": bool(is_speech),
                "energy": float(energy)
            })

        return frames

    def get_speech_segments(self, frames):
        segments = []

        current_start = None

        for frame in frames:

            if frame["is_speech"] and current_start is None:
                current_start = frame["start"]

            elif not frame["is_speech"] and current_start is not None:
                segments.append({
                    "start": current_start,
                    "end": frame["start"]
                })

                current_start = None

        if current_start is not None and frames:
            segments.append({
                "start": current_start,
                "end": frames[-1]["end"]
            })

        return segments

    def get_pauses(self, segments):
        pauses = []

        for i in range(len(segments) - 1):
            pause_start = segments[i]["end"]
            pause_end = segments[i + 1]["start"]

            pauses.append({
                "start": pause_start,
                "end": pause_end,
                "duration": pause_end - pause_start
            })

        return pauses
        
    def detect(self, audio_path):
        frames = self.detect_frames(audio_path)

        segments = self.get_speech_segments(frames)

        pauses = self.get_pauses(segments)
        
        total_duration = frames[-1]["end"] if frames else 0

        speech_duration = sum(
            segment["end"] - segment["start"]
            for segment in segments
        )

        silence_duration = max(
            total_duration - speech_duration,
            0
        )

        return {
            "duration": total_duration,
            "speech_segments": segments,
            "speech_duration": speech_duration,
            "silence_duration": silence_duration,
            "pauses": pauses
        }