class HesitationDetector:
    def detect(self, speech_result):
        features = speech_result.get("features", {})
        audio = speech_result.get("audio", {})

        number_of_pauses = features.get("number_of_pauses", 0)
        average_pause_duration = features.get("average_pause_duration", 0.0)
        max_pause_duration = features.get("max_pause_duration", 0.0)

        silence_duration = audio.get("silence_duration", 0.0)
        speech_duration = audio.get("speech_duration", 0.0)

        total_duration = speech_duration + silence_duration

        if total_duration <= 0:
            return {
                "score": 0.5
            }

        pause_frequency = number_of_pauses / max(speech_duration, 1.0)

        silence_ratio = silence_duration / total_duration

        pause_score = min(pause_frequency / 0.5, 1.0)
        average_pause_score = min(average_pause_duration / 2.0, 1.0)
        max_pause_score = min(max_pause_duration / 4.0, 1.0)
        silence_score = min(silence_ratio / 0.5, 1.0)

        score = (
            0.30 * pause_score
            + 0.25 * average_pause_score
            + 0.25 * max_pause_score
            + 0.20 * silence_score
        )

        return {
            "score": round(max(0.0, min(score, 1.0)), 3)
        }