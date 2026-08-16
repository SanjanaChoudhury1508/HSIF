"""
state_fusion.py

Combines the Human State Representation (HSR) into
a dialogue-oriented conversational state.

The Human State Engine estimates individual signals such as
emotion, hesitation, confidence, engagement, and cognitive load.

This module interprets those signals together so that the
Dialogue Policy Engine can decide how the AI should respond.
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, Mapping


@dataclass
class DialogueState:
    """Dialogue-oriented representation of the user's current state."""

    emotion: str
    emotion_score: float

    hesitation: float
    confidence: float
    engagement: float
    cognitive_load: float

    interaction_state: str
    needs_clarification: bool
    needs_encouragement: bool

    def to_dict(self) -> Dict[str, Any]:
        """Convert the dialogue state into a JSON-friendly dictionary."""
        return asdict(self)


class StateFusion:
    """
    Converts a HumanState into a DialogueState.

    The current implementation uses simple rule-based fusion.
    """

    @staticmethod
    def _clamp(value: Any, default: float = 0.5) -> float:
        """Convert a value to a safe score between 0.0 and 1.0."""

        try:
            score = float(value)
        except (TypeError, ValueError):
            score = default

        if score != score:
            score = default

        return round(max(0.0, min(score, 1.0)), 3)

    @classmethod
    def _get_score(
        cls,
        state: Mapping[str, Any],
        field: str,
    ) -> float:
        """Safely extract a score from a HumanState component."""

        component = state.get(field, {})

        if not isinstance(component, Mapping):
            return 0.5

        return cls._clamp(component.get("score"))

    @classmethod
    def fuse(
        cls,
        human_state: Mapping[str, Any] | None,
    ) -> DialogueState:
        """
        Fuse Human State signals into a dialogue-oriented state.

        Parameters
        ----------
        human_state:
            Dictionary representation of HumanState.

        Returns
        -------
        DialogueState
            Combined state used by the Dialogue Policy Engine.
        """

        if human_state is None:
            human_state = {}

        if not isinstance(human_state, Mapping):
            raise TypeError(
                "human_state must be a dictionary-like Mapping."
            )

        emotion = human_state.get("emotion", {})

        if not isinstance(emotion, Mapping):
            emotion = {}

        emotion_label = emotion.get("label", "neutral")

        if not isinstance(emotion_label, str) or not emotion_label.strip():
            emotion_label = "neutral"
        else:
            emotion_label = emotion_label.strip().lower()

        emotion_score = cls._clamp(
            emotion.get("score"),
            default=0.5,
        )

        hesitation = cls._get_score(
            human_state,
            "hesitation",
        )

        confidence = cls._get_score(
            human_state,
            "confidence",
        )

        engagement = cls._get_score(
            human_state,
            "engagement",
        )

        cognitive_load = cls._get_score(
            human_state,
            "cognitive_load",
        )

        # High hesitation + low confidence suggests that
        # the user may be struggling with the interaction.
        struggling = (
            hesitation >= 0.6
            and confidence <= 0.45
        )

        # High cognitive load suggests that the user may
        # benefit from a simpler response.
        overloaded = cognitive_load >= 0.7

        # Low engagement suggests that the system may need
        # to regain the user's attention.
        disengaged = engagement <= 0.3

        if overloaded:
            interaction_state = "overloaded"
        elif struggling:
            interaction_state = "struggling"
        elif disengaged:
            interaction_state = "disengaged"
        elif confidence >= 0.8 and engagement >= 0.8:
            interaction_state = "confident_engaged"
        else:
            interaction_state = "neutral"

        needs_clarification = (
            struggling
            or overloaded
            or emotion_label in {
                "confused",
                "uncertain",
            }
        )

        needs_encouragement = (
            struggling
            or confidence <= 0.35
            or disengaged
        )

        return DialogueState(
            emotion=emotion_label,
            emotion_score=emotion_score,
            hesitation=hesitation,
            confidence=confidence,
            engagement=engagement,
            cognitive_load=cognitive_load,
            interaction_state=interaction_state,
            needs_clarification=needs_clarification,
            needs_encouragement=needs_encouragement,
        )

    @classmethod
    def fuse_to_dict(
        cls,
        human_state: Mapping[str, Any] | None,
    ) -> Dict[str, Any]:
        """Fuse HumanState and return a JSON-friendly dictionary."""

        return cls.fuse(human_state).to_dict()