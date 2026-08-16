"""
dialogue_policy.py

Converts the fused DialogueState into a recommended
response strategy for the conversational AI.
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, Mapping


@dataclass
class PolicyDecision:
    """Recommended strategy for the dialogue system."""

    strategy: str
    reason: str
    priority: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert the policy decision into a JSON-friendly dictionary."""
        return asdict(self)


class DialoguePolicy:
    """
    Rule-based Dialogue Policy Engine.

    Takes the output of StateFusion and recommends
    how the AI should respond.
    """

    @staticmethod
    def _get_bool(
        state: Mapping[str, Any],
        field: str,
    ) -> bool:
        """Safely extract a boolean value."""
        return bool(state.get(field, False))

    @staticmethod
    def _get_state(
        state: Mapping[str, Any],
    ) -> str:
        """Safely extract the interaction state."""

        value = state.get(
            "interaction_state",
            "neutral",
        )

        if not isinstance(value, str):
            return "neutral"

        value = value.strip().lower()

        valid_states = {
            "neutral",
            "struggling",
            "overloaded",
            "disengaged",
            "confident_engaged",
        }

        if value not in valid_states:
            return "neutral"

        return value

    @classmethod
    def decide(
        cls,
        dialogue_state: Mapping[str, Any] | None,
    ) -> PolicyDecision:
        """
        Generate a response strategy from a fused DialogueState.

        Priority order:

        1. Overloaded
        2. Struggling
        3. Disengaged
        4. Confident and engaged
        5. Neutral
        """

        if dialogue_state is None:
            dialogue_state = {}

        if not isinstance(dialogue_state, Mapping):
            raise TypeError(
                "dialogue_state must be a dictionary-like Mapping."
            )

        interaction_state = cls._get_state(
            dialogue_state
        )

        needs_clarification = cls._get_bool(
            dialogue_state,
            "needs_clarification",
        )

        needs_encouragement = cls._get_bool(
            dialogue_state,
            "needs_encouragement",
        )

        if interaction_state == "overloaded":
            return PolicyDecision(
                strategy="simplify",
                reason="The user may be experiencing high cognitive load.",
                priority="high",
            )

        if interaction_state == "struggling":
            return PolicyDecision(
                strategy="clarify",
                reason="The user appears to be struggling with the interaction.",
                priority="high",
            )

        if interaction_state == "disengaged":
            return PolicyDecision(
                strategy="re_engage",
                reason="The user's engagement appears low.",
                priority="medium",
            )

        if interaction_state == "confident_engaged":
            return PolicyDecision(
                strategy="continue",
                reason="The user appears confident and engaged.",
                priority="low",
            )

        if needs_clarification:
            return PolicyDecision(
                strategy="clarify",
                reason="The fused state indicates that clarification may help.",
                priority="medium",
            )

        if needs_encouragement:
            return PolicyDecision(
                strategy="encourage",
                reason="The user may benefit from additional encouragement.",
                priority="medium",
            )

        return PolicyDecision(
            strategy="normal_response",
            reason="No special dialogue adaptation is required.",
            priority="low",
        )

    @classmethod
    def decide_to_dict(
        cls,
        dialogue_state: Mapping[str, Any] | None,
    ) -> Dict[str, Any]:
        """Generate a policy decision as a JSON-friendly dictionary."""

        return cls.decide(dialogue_state).to_dict()


if __name__ == "__main__":
    example_state = {
        "emotion": "confused",
        "emotion_score": 0.8,
        "hesitation": 0.8,
        "confidence": 0.3,
        "engagement": 0.8,
        "cognitive_load": 0.5,
        "interaction_state": "struggling",
        "needs_clarification": True,
        "needs_encouragement": True,
    }

    print(
        DialoguePolicy.decide_to_dict(
            example_state
        )
    )