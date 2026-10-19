import math


class HesitationDetector:
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

    def detect(self, speech_result):
        features = speech_result.get("features", {})
        audio = speech_result.get("audio", {})

        number_of_pauses = self._safe_float(
            features.get("number_of_pauses", 0)
        )
        average_pause_duration = self._safe_float(
            features.get("average_pause_duration", 0.0)
        )
        max_pause_duration = self._safe_float(
            features.get("max_pause_duration", 0.0)
        )

        silence_duration = self._safe_float(
            audio.get("silence_duration", 0.0)
        )
        speech_duration = self._safe_float(
            audio.get("speech_duration", 0.0)
        )

        total_duration = speech_duration + silence_duration

        if total_duration <= 0:
            return {
                "score": 0.5
            }

        pause_frequency = (
            number_of_pauses / speech_duration
            if speech_duration > 0
            else 0.0
        )

        silence_ratio = silence_duration / total_duration

        pause_score = self._normalize(pause_frequency, 0.5)
        average_pause_score = self._normalize(
            average_pause_duration, 2.0
        )
        max_pause_score = self._normalize(
            max_pause_duration, 4.0
        )
        silence_score = self._normalize(
            silence_ratio, 0.5
        )

        score = (
            0.30 * pause_score
            + 0.25 * average_pause_score
            + 0.25 * max_pause_score
            + 0.20 * silence_score
        )

        return {
            "score": round(min(max(score, 0.0), 1.0), 3)
        }