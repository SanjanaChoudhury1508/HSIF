import math


class ConfidenceEstimator:
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

        number_of_pauses = self._safe_float(
            features.get("number_of_pauses", 0)
        )
        average_pause_duration = self._safe_float(
            features.get("average_pause_duration", 0.0)
        )
        min_pitch = self._safe_float(
            features.get("min_pitch", 0.0)
        )
        max_pitch = self._safe_float(
            features.get("max_pitch", 0.0)
        )
        mean_energy = self._safe_float(
            features.get("mean_energy", 0.0)
        )
        speech_duration = self._safe_float(
            audio.get("speech_duration", 0.0)
        )

        if speech_duration <= 0:
            return {
                "score": 0.5
            }

        pitch_range = max(0.0, max_pitch - min_pitch)

        pause_frequency = number_of_pauses / speech_duration

        pause_penalty = self._normalize(
            pause_frequency,
            0.5,
        )

        duration_penalty = self._normalize(
            average_pause_duration,
            2.0,
        )

        pause_confidence = 1.0 - pause_penalty
        duration_confidence = 1.0 - duration_penalty

        if 40.0 <= pitch_range <= 150.0:
            pitch_score = 0.9
        elif pitch_range < 40.0:
            pitch_score = 0.6
        else:
            pitch_score = max(
                0.4,
                0.9 - ((pitch_range - 150.0) / 250.0)
            )

        energy_score = self._normalize(
            mean_energy,
            0.12,
        )

        score = (
            0.30 * pause_confidence
            + 0.20 * duration_confidence
            + 0.25 * pitch_score
            + 0.25 * energy_score
        )

        return {
            "score": round(
                max(0.0, min(score, 1.0)),
                3,
            )
        }