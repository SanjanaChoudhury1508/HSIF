import math


class EmotionDetector:
    def _clamp(self, value, minimum=0.0, maximum=1.0):
        return max(minimum, min(maximum, value))

    def _safe_float(self, value, default=0.0):
        try:
            value = float(value)
            if not math.isfinite(value):
                return default
            return value
        except (TypeError, ValueError):
            return default

    def detect(self, speech_result):
        features = speech_result.get("features", {})

        mean_pitch = self._safe_float(features.get("mean_pitch", 0.0))
        min_pitch = self._safe_float(features.get("min_pitch", 0.0))
        max_pitch = self._safe_float(features.get("max_pitch", 0.0))
        mean_energy = self._safe_float(features.get("mean_energy", 0.0))

        if mean_pitch <= 0 or mean_energy <= 0:
            return {
                "label": "neutral",
                "score": 0.5
            }

        pitch_range = max(0.0, max_pitch - min_pitch)

        energy_level = self._clamp(mean_energy / 0.15)
        pitch_variation = self._clamp(pitch_range / 150.0)
        high_pitch = self._clamp((mean_pitch - 150.0) / 120.0)
        low_energy = 1.0 - self._clamp(mean_energy / 0.12)
        low_variation = 1.0 - self._clamp(pitch_range / 100.0)

        excited_score = (
            0.55 * energy_level
            + 0.45 * pitch_variation
        )

        sad_score = (
            0.60 * low_energy
            + 0.40 * low_variation
        )

        happy_score = (
            0.50 * high_pitch
            + 0.30 * energy_level
            + 0.20 * pitch_variation
        )

        candidates = {
            "excited": excited_score,
            "sad": sad_score,
            "happy": happy_score,
        }

        label = max(candidates, key=candidates.get)
        score = candidates[label]

        if score < 0.65:
            return {
                "label": "neutral",
                "score": round(1.0 - score, 3)
            }

        return {
            "label": label,
            "score": round(self._clamp(score), 3)
        }