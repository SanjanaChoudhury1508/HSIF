import librosa
import numpy as np


class AcousticFeatureExtractor:

    def __init__(self, sample_rate=16000):
        self.sample_rate = sample_rate
    
    def extract_pitch(self, audio):
        f0, _, _ = librosa.pyin(
            audio,
            fmin=librosa.note_to_hz("C2"),
            fmax=librosa.note_to_hz("C7"),
            sr=self.sample_rate
        )

        valid_pitch = f0[~np.isnan(f0)]

        if len(valid_pitch) == 0:
            return {
                "mean_pitch": 0.0,
                "min_pitch": 0.0,
                "max_pitch": 0.0
            }

        return {
            "mean_pitch": float(np.mean(valid_pitch)),
            "min_pitch": float(np.min(valid_pitch)),
            "max_pitch": float(np.max(valid_pitch))
        }
    
    def extract(self, audio_path, vad_result):
        audio, _ = librosa.load(
            audio_path,
            sr=self.sample_rate,
            mono=True
        )
    
        pauses = vad_result["pauses"]
    
        pause_durations = [
            pause["duration"]
            for pause in pauses
        ]
    
        mean_energy = float(
            np.sqrt(np.mean(audio ** 2))
        )
    
        pitch_features = self.extract_pitch(audio)
    
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
    
        return {
            "duration": vad_result["duration"],
            "speech_duration": vad_result["speech_duration"],
            "silence_duration": vad_result["silence_duration"],
            "number_of_pauses": len(pauses),
            "average_pause_duration": average_pause_duration,
            "max_pause_duration": max_pause_duration,
            "mean_energy": mean_energy,
            **pitch_features,
            "pauses": pauses
        }
    