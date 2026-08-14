class EngagementEstimator:
    def estimate(self, speech_result):
        features = speech_result.get("features", {})
        audio = speech_result.get("audio", {})
        vad = speech_result.get("vad", {})

        speech_duration = audio.get("speech_duration", 0.0)
        silence_duration = audio.get("silence_duration", 0.0)
        mean_energy = features.get("mean_energy", 0.0)
        number_of_pauses = features.get("number_of_pauses", 0)
        min_pitch = features.get("min_pitch", 0.0)
        max_pitch = features.get("max_pitch", 0.0)

        total_duration = speech_duration + silence_duration

        if total_duration <= 0:
            return {
                "score": 0.5
            }

        speech_activity = speech_duration / total_duration

        pause_penalty = min(
            number_of_pauses / max(speech_duration, 1.0),
            1.0
        )

        pitch_range = max_pitch - min_pitch

        if pitch_range >= 100:
            pitch_score = 0.9
        elif pitch_range >= 50:
            pitch_score = 0.7
        elif pitch_range > 0:
            pitch_score = 0.5
        else:
            pitch_score = 0.5

        if mean_energy >= 0.1:
            energy_score = 0.9
        elif mean_energy >= 0.05:
            energy_score = 0.7
        elif mean_energy > 0:
            energy_score = 0.5
        else:
            energy_score = 0.5

        score = (
            0.35 * speech_activity
            + 0.25 * energy_score
            + 0.20 * (1.0 - pause_penalty)
            + 0.20 * pitch_score
        )

        return {
            "score": round(max(0.0, min(score, 1.0)), 3)
        }