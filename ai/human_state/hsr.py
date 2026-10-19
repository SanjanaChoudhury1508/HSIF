
"""
Human State Representation (HSR).

The HSR is the structured output of the Human State Engine.

Scores are normalized to the inclusive range [0.0, 1.0].
They represent model estimates, not objective psychological measurements.

EmotionResult.score represents confidence in the predicted emotion label,
not the intensity of that emotion.
"""

from dataclasses import dataclass, asdict, field
from math import isfinite
from typing import Any, Dict


def _validate_score(score: float, field_name: str = "score") -> float:
    """Validate that a score is a finite number between 0 and 1."""
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        raise TypeError(f"{field_name} must be a numeric value")

    if not isfinite(score):
        raise ValueError(f"{field_name} must be finite")

    if not 0.0 <= score <= 1.0:
        raise ValueError(f"{field_name} must be between 0.0 and 1.0")

    return float(score)


@dataclass
class EmotionResult:
    """Predicted emotion label and confidence in that prediction."""

    label: str
    score: float

    def __post_init__(self) -> None:
        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError("emotion label must be a non-empty string")

        self.label = self.label.strip().lower()
        self.score = _validate_score(self.score, "emotion score")


@dataclass
class ScoreResult:
    """Normalized score for a human-state dimension."""

    score: float

    def __post_init__(self) -> None:
        self.score = _validate_score(self.score)


@dataclass
class HumanState:
    """Current structured representation of the estimated human state."""

    emotion: EmotionResult
    hesitation: ScoreResult
    confidence: ScoreResult
    engagement: ScoreResult
    cognitive_load: ScoreResult

    # Reserved for temporal processing. Excluded from the existing HSR
    # serialization so the five-field API contract remains unchanged.
    timestamp: float | None = field(default=None, repr=False, compare=False)
    observation_valid: bool = field(default=True, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.emotion, EmotionResult):
            raise TypeError("emotion must be an EmotionResult")

        for name in (
            "hesitation",
            "confidence",
            "engagement",
            "cognitive_load",
        ):
            if not isinstance(getattr(self, name), ScoreResult):
                raise TypeError(f"{name} must be a ScoreResult")

        if self.timestamp is not None:
            if isinstance(self.timestamp, bool) or not isinstance(
                self.timestamp, (int, float)
            ):
                raise TypeError("timestamp must be a numeric value or None")

            if not isfinite(self.timestamp):
                raise ValueError("timestamp must be finite")

            self.timestamp = float(self.timestamp)

        if not isinstance(self.observation_valid, bool):
            raise TypeError("observation_valid must be a boolean")

    def to_dict(self) -> Dict[str, Any]:
        """Return the stable, JSON-friendly five-field HSR representation."""
        return {
            "emotion": asdict(self.emotion),
            "hesitation": asdict(self.hesitation),
            "confidence": asdict(self.confidence),
            "engagement": asdict(self.engagement),
            "cognitive_load": asdict(self.cognitive_load),
        }


def build_human_state(
    emotion_label: str,
    emotion_score: float,
    hesitation_score: float,
    confidence_score: float,
    engagement_score: float,
    cognitive_load_score: float,
    *,
    timestamp: float | None = None,
    observation_valid: bool = True,
) -> HumanState:
    """Build a validated HSR from estimator outputs."""
    return HumanState(
        emotion=EmotionResult(emotion_label, emotion_score),
        hesitation=ScoreResult(hesitation_score),
        confidence=ScoreResult(confidence_score),
        engagement=ScoreResult(engagement_score),
        cognitive_load=ScoreResult(cognitive_load_score),
        timestamp=timestamp,
        observation_valid=observation_valid,
    )
