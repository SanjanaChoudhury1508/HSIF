import math


class EngagementEstimator:
    def _safe_float(self, value, default=0.0):
        try:
            value = float(value)
            if not math.isfinite(value):
                return default
            return max(0.0, value)
        except (TypeError, ValueError):
            return default

    def _normalize(self, value, maximum):
        if maximum <= 0:
            return 0.0
        return min(value / maximum, 1.0)

    def estimate(self, speech_result):
        features = speech_result.get("features", {})
        audio = speech_result.get("audio", {})

        speech_duration = self._safe_float(
            audio.get("speech_duration", 0.0)
        )
        silence_duration = self._safe_float(
            audio.get("silence_duration", 0.0)
        )
        mean_energy = self._safe_float(
            features.get("mean_energy", 0.0)
        )
        number_of_pauses = self._safe_float(
            features.get("number_of_pauses", 0)
        )
        min_pitch = self._safe_float(
            features.get("min_pitch", 0.0)
        )
        max_pitch = self._safe_float(
            features.get("max_pitch", 0.0)
        )

        total_duration = speech_duration + silence_duration

        if total_duration <= 0:
            return {
                "score": 0.5
            }

        speech_activity = speech_duration / total_duration

        pause_frequency = (
            number_of_pauses / speech_duration
            if speech_duration > 0
            else 0.0
        )

        pause_penalty = self._normalize(
            pause_frequency,
            0.5,
        )

        pitch_range = max(0.0, max_pitch - min_pitch)

        if pitch_range >= 100:
            pitch_score = 0.9
        elif pitch_range >= 50:
            pitch_score = 0.7
        elif pitch_range > 0:
            pitch_score = 0.5
        else:
            pitch_score = 0.5

        energy_score = self._normalize(
            mean_energy,
            0.12,
        )

        score = (
            0.35 * speech_activity
            + 0.25 * energy_score
            + 0.20 * (1.0 - pause_penalty)
            + 0.20 * pitch_score
        )

        return {
            "score": round(
                max(0.0, min(score, 1.0)),
                3,
            )
        }