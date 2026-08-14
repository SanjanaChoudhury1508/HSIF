"""
hsr.py

Defines the Human State Representation (HSR) — the single structured
output of the Human State Engine.

Every estimator (emotion, hesitation, confidence, engagement,
cognitive_load) produces a small piece of this. This file combines
them into one consistent object that gets handed off to Jennie's
dialogue module.

Keeping this format stable is important: other modules will depend
on these exact field names.
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any


@dataclass
class EmotionResult:
    label: str      # e.g. "neutral", "happy", "sad", "angry", "anxious"
    score: float     # confidence of the label, 0.0 - 1.0


@dataclass
class ScoreResult:
    """Generic 0.0-1.0 score used by hesitation, confidence,
    engagement, and cognitive_load — they all share this shape."""
    score: float


@dataclass
class HumanState:
    """The full Human State Representation (HSR)."""
    emotion: EmotionResult
    hesitation: ScoreResult
    confidence: ScoreResult
    engagement: ScoreResult
    cognitive_load: ScoreResult

    def to_dict(self) -> Dict[str, Any]:
        """Convert to a plain dict — useful for JSON responses,
        logging, or passing to the dialogue module."""
        return asdict(self)


def build_human_state(
    emotion_label: str,
    emotion_score: float,
    hesitation_score: float,
    confidence_score: float,
    engagement_score: float,
    cognitive_load_score: float,
) -> HumanState:
    """
    Convenience factory to build a HumanState from raw values.
    This is what human_state_service.py will call after running
    all the individual estimators.
    """
    return HumanState(
        emotion=EmotionResult(label=emotion_label, score=emotion_score),
        hesitation=ScoreResult(score=hesitation_score),
        confidence=ScoreResult(score=confidence_score),
        engagement=ScoreResult(score=engagement_score),
        cognitive_load=ScoreResult(score=cognitive_load_score),
    )


if __name__ == "__main__":
    # Quick manual sanity check — run with: python hsr.py
    example = build_human_state(
        emotion_label="neutral",
        emotion_score=0.72,
        hesitation_score=0.31,
        confidence_score=0.68,
        engagement_score=0.75,
        cognitive_load_score=0.42,
    )
    import json
    print(json.dumps(example.to_dict(), indent=2))