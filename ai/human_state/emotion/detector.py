class EmotionDetector:
    def detect(self, speech_result):
        features = speech_result.get("features", {})

        mean_pitch = features.get("mean_pitch", 0.0)
        min_pitch = features.get("min_pitch", 0.0)
        max_pitch = features.get("max_pitch", 0.0)
        mean_energy = features.get("mean_energy", 0.0)

        if mean_pitch == 0 or mean_energy == 0:
            return {
                "label": "neutral",
                "score": 0.5
            }

        pitch_range = max_pitch - min_pitch

        if mean_energy > 0.12 and pitch_range > 100:
            return {
                "label": "excited",
                "score": 0.8
            }

        if mean_energy < 0.04 and pitch_range < 50:
            return {
                "label": "sad",
                "score": 0.7
            }

        if mean_pitch > 220 and mean_energy > 0.08:
            return {
                "label": "happy",
                "score": 0.7
            }

        return {
            "label": "neutral",
            "score": 0.6
        }