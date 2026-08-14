class ConfidenceEstimator:
    def estimate(self, speech_result):
        features = speech_result.get("features", {})
        audio = speech_result.get("audio", {})

        number_of_pauses = features.get("number_of_pauses", 0)
        average_pause_duration = features.get("average_pause_duration", 0.0)
        min_pitch = features.get("min_pitch", 0.0)
        max_pitch = features.get("max_pitch", 0.0)
        mean_energy = features.get("mean_energy", 0.0)
        speech_duration = audio.get("speech_duration", 0.0)

        if speech_duration <= 0:
            return {
                "score": 0.5
            }

        pitch_range = max_pitch - min_pitch
        pause_frequency = number_of_pauses / max(speech_duration, 1.0)

        pause_penalty = min(pause_frequency / 0.5, 1.0)
        duration_penalty = min(average_pause_duration / 2.0, 1.0)

        if pitch_range > 200:
            pitch_score = 0.4
        elif pitch_range > 100:
            pitch_score = 0.6
        elif pitch_range > 40:
            pitch_score = 0.8
        else:
            pitch_score = 0.6

        if mean_energy >= 0.1:
            energy_score = 0.9
        elif mean_energy >= 0.05:
            energy_score = 0.7
        elif mean_energy > 0:
            energy_score = 0.5
        else:
            energy_score = 0.5

        score = (
            0.30 * (1.0 - pause_penalty)
            + 0.20 * (1.0 - duration_penalty)
            + 0.25 * pitch_score
            + 0.25 * energy_score
        )

        return {
            "score": round(max(0.0, min(score, 1.0)), 3)
        }