"""
human_state_engine.py

Main orchestration layer for the Human State Engine.

Input:
    SpeechResult produced by Eesha's speech-processing module.

Output:
    HumanState defined in hsr.py.

The engine coordinates all individual estimators and records
successive HumanState objects through StateTracker.
"""

from typing import Any, Dict, Mapping

from ai.human_state.hsr import HumanState, build_human_state
from ai.human_state.state_tracker import StateTracker
from ai.human_state.emotion.detector import EmotionDetector
from ai.human_state.hesitation.detector import HesitationDetector
from ai.human_state.confidence.estimator import ConfidenceEstimator
from ai.human_state.engagement.estimator import EngagementEstimator
from ai.human_state.cognitive_load.estimator import estimate_cognitive_load


class HumanStateEngine:
    """
    Orchestrates all Human State estimators and tracks
    successive HumanState results.
    """

    def __init__(
        self,
        emotion_detector: EmotionDetector | None = None,
        hesitation_detector: HesitationDetector | None = None,
        confidence_estimator: ConfidenceEstimator | None = None,
        engagement_estimator: EngagementEstimator | None = None,
        state_tracker: StateTracker | None = None,
    ) -> None:
        self.emotion_detector = emotion_detector or EmotionDetector()
        self.hesitation_detector = hesitation_detector or HesitationDetector()
        self.confidence_estimator = (
            confidence_estimator or ConfidenceEstimator()
        )
        self.engagement_estimator = (
            engagement_estimator or EngagementEstimator()
        )
        self.state_tracker = state_tracker or StateTracker()

    @staticmethod
    def _validate_input(
        speech_result: Mapping[str, Any] | None,
    ) -> Dict[str, Any]:
        if speech_result is None:
            return {
                "audio": {},
                "features": {},
                "vad": {},
            }

        if not isinstance(speech_result, Mapping):
            raise TypeError(
                "speech_result must be a dictionary-like Mapping."
            )

        normalized = dict(speech_result)

        if not isinstance(normalized.get("audio"), Mapping):
            normalized["audio"] = {}

        if not isinstance(normalized.get("features"), Mapping):
            normalized["features"] = {}

        if not isinstance(normalized.get("vad"), Mapping):
            normalized["vad"] = {}

        return normalized

    @staticmethod
    def _clamp_score(
        value: Any,
        default: float = 0.5,
    ) -> float:
        try:
            score = float(value)
        except (TypeError, ValueError):
            score = default

        if score != score:
            score = default

        return round(max(0.0, min(score, 1.0)), 3)

    @classmethod
    def _normalize_score_result(
        cls,
        result: Any,
        default: float = 0.5,
    ) -> Dict[str, float]:
        if not isinstance(result, Mapping):
            return {
                "score": default
            }

        return {
            "score": cls._clamp_score(
                result.get("score"),
                default=default,
            )
        }

    @classmethod
    def _normalize_emotion_result(
        cls,
        result: Any,
    ) -> Dict[str, Any]:
        if not isinstance(result, Mapping):
            return {
                "label": "neutral",
                "score": 0.5,
            }

        label = result.get("label", "neutral")

        if not isinstance(label, str) or not label.strip():
            label = "neutral"
        else:
            label = label.strip().lower()

        return {
            "label": label,
            "score": cls._clamp_score(
                result.get("score"),
                default=0.5,
            ),
        }

    def process(
        self,
        speech_result: Mapping[str, Any] | None,
    ) -> HumanState:
        """
        Process one SpeechResult, create a HumanState, and
        automatically record it in the StateTracker.
        """
        speech_result = self._validate_input(speech_result)

        emotion_result = self.emotion_detector.detect(
            speech_result
        )

        hesitation_result = self.hesitation_detector.detect(
            speech_result
        )

        confidence_result = self.confidence_estimator.estimate(
            speech_result
        )

        engagement_result = self.engagement_estimator.estimate(
            speech_result
        )

        cognitive_load_result = estimate_cognitive_load(
            speech_result
        )

        emotion = self._normalize_emotion_result(
            emotion_result
        )

        hesitation = self._normalize_score_result(
            hesitation_result
        )

        confidence = self._normalize_score_result(
            confidence_result
        )

        engagement = self._normalize_score_result(
            engagement_result
        )

        cognitive_load = self._normalize_score_result(
            cognitive_load_result
        )

        state = build_human_state(
            emotion_label=emotion["label"],
            emotion_score=emotion["score"],
            hesitation_score=hesitation["score"],
            confidence_score=confidence["score"],
            engagement_score=engagement["score"],
            cognitive_load_score=cognitive_load["score"],
        )

        self.state_tracker.add_state(state)

        return state

    def process_to_dict(
        self,
        speech_result: Mapping[str, Any] | None,
    ) -> Dict[str, Any]:
        """
        Process SpeechResult and return a JSON-friendly dictionary.
        """
        return self.process(speech_result).to_dict()

    def get_current_state(self) -> HumanState | None:
        return self.state_tracker.get_current_state()

    def get_state_history(self) -> list[HumanState]:
        return self.state_tracker.get_history()

    def get_state_trajectory(self) -> list[Dict[str, Any]]:
        return self.state_tracker.get_trajectory()

    def get_state_changes(self) -> list[Dict[str, Any]]:
        return self.state_tracker.get_state_changes()

    def clear_state_history(self) -> None:
        self.state_tracker.clear()


if __name__ == "__main__":
    import json

    sample_speech_result = {
        "transcript": "Hello, this is a test.",
        "language": "en",
        "language_probability": 0.657,
        "audio": {
            "duration": 6.037,
            "speech_duration": 5.52,
            "silence_duration": 0.517,
        },
        "features": {
            "number_of_pauses": 1,
            "average_pause_duration": 0.45,
            "max_pause_duration": 0.45,
            "mean_energy": 0.0789,
            "mean_pitch": 186.16,
            "min_pitch": 69.7,
            "max_pitch": 242.7,
        },
        "vad": {
            "speech_segments": [],
            "pauses": [],
        },
    }

    engine = HumanStateEngine()

    result = engine.process_to_dict(
        sample_speech_result
    )

    print(json.dumps(result, indent=2))