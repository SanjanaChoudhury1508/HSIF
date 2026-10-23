
"""
dialogue_policy.py

Converts the fused DialogueState into a recommended
response strategy for the conversational AI.
"""

import math
from dataclasses import dataclass, asdict
from typing import Any, Dict, Mapping


@dataclass
class PolicyDecision:
    """Recommended strategy for the dialogue system."""

    strategy: str
    reason: str
    priority: str
    response_style: str = "natural"
    complexity: str = "moderate"
    detail_level: str = "moderate"

    def to_dict(self) -> Dict[str, Any]:
        """Convert the policy decision into a JSON-friendly dictionary."""
        return asdict(self)


class DialoguePolicy:
    """Rule-based Dialogue Policy Engine."""

    @staticmethod
    def _get_bool(
        state: Mapping[str, Any],
        field: str,
    ) -> bool:
        """Safely extract a boolean value."""
        return bool(state.get(field, False))

    @staticmethod
    def _get_score(
        state: Mapping[str, Any],
        field: str,
        default: float = 0.5,
    ) -> float:
        """Safely extract a finite score and clamp it to [0, 1]."""
        try:
            score = float(state.get(field, default))
        except (TypeError, ValueError, OverflowError):
            return default

        if not math.isfinite(score):
            return default

        return round(max(0.0, min(score, 1.0)), 3)

    @staticmethod
    def _get_state(state: Mapping[str, Any]) -> str:
        """Safely extract the interaction state."""
        value = state.get("interaction_state", "neutral")

        if not isinstance(value, str):
            return "neutral"

        value = value.strip().lower()

        valid_states = {
            "neutral",
            "struggling",
            "overloaded",
            "overloaded_uncertain",
            "disengaged",
            "confident_engaged",
        }

        return value if value in valid_states else "neutral"

    @classmethod
    def decide(
        cls,
        dialogue_state: Mapping[str, Any] | None,
    ) -> PolicyDecision:
        """Generate a response strategy from a fused DialogueState."""

        if dialogue_state is None:
            dialogue_state = {}

        if not isinstance(dialogue_state, Mapping):
            raise TypeError(
                "dialogue_state must be a dictionary-like Mapping."
            )

        interaction_state = cls._get_state(dialogue_state)
        needs_clarification = cls._get_bool(
            dialogue_state, "needs_clarification"
        )
        needs_encouragement = cls._get_bool(
            dialogue_state, "needs_encouragement"
        )

        emotion = dialogue_state.get("emotion", "neutral")
        if not isinstance(emotion, str):
            emotion = "neutral"
        emotion = emotion.strip().lower()

        hesitation = cls._get_score(dialogue_state, "hesitation")
        confidence = cls._get_score(dialogue_state, "confidence")
        cognitive_load = cls._get_score(dialogue_state, "cognitive_load")

        # Acknowledge frustration before applying generic strategies.
        if emotion == "frustrated":
            return PolicyDecision(
                strategy="acknowledge_frustration",
                reason="The user appears to be frustrated.",
                priority="high",
                response_style="empathetic",
                complexity="simple",
                detail_level="minimal",
            )

        # High hesitation and low confidence call for reassurance.
        if hesitation >= 0.7 and confidence <= 0.45:
            return PolicyDecision(
                strategy="reassure",
                reason=(
                    "High hesitation and low confidence suggest "
                    "that reassurance may help."
                ),
                priority="high",
                response_style="supportive",
                complexity="simple",
                detail_level="moderate",
            )

        if (
            interaction_state == "overloaded_uncertain"
            and confidence <= 0.35
        ):
            return PolicyDecision(
                strategy="simplify",
                reason=(
                    "High cognitive load and very low confidence suggest "
                    "that a simpler, supportive explanation may help."
                ),
                priority="high",
                response_style="supportive",
                complexity="simple",
                detail_level="minimal",
            )

        # Very high cognitive load requires less information.
        if (
            interaction_state in {"overloaded", "overloaded_uncertain"}
            and cognitive_load >= 0.9
        ):
            return PolicyDecision(
                strategy="reduce_information",
                reason=(
                    "The user's cognitive load appears very high, "
                    "so the amount of information should be reduced."
                ),
                priority="high",
                response_style=(
                    "supportive"
                    if interaction_state == "overloaded_uncertain"
                    else "concise"
                ),
                complexity="simple",
                detail_level="minimal",
            )

        # High hesitation calls for a slower explanation.
        if hesitation >= 0.7:
            return PolicyDecision(
                strategy="slow_down",
                reason=(
                    "The user's hesitation suggests that the "
                    "conversation may need to proceed more slowly."
                ),
                priority="medium",
                response_style="calm",
                complexity="simple",
                detail_level="moderate",
            )

        if interaction_state == "overloaded":
            return PolicyDecision(
                strategy="simplify",
                reason="The user may be experiencing high cognitive load.",
                priority="high",
                response_style="clear",
                complexity="simple",
                detail_level="moderate",
            )

        if interaction_state == "struggling":
            return PolicyDecision(
                strategy="clarify",
                reason="The user appears to be struggling with the interaction.",
                priority="high",
                response_style="patient",
                complexity="simple",
                detail_level="moderate",
            )

        if interaction_state == "disengaged":
            return PolicyDecision(
                strategy="re_engage",
                reason="The user's engagement appears low.",
                priority="medium",
                response_style="engaging",
                complexity="moderate",
                detail_level="minimal",
            )

        if interaction_state == "confident_engaged":
            return PolicyDecision(
                strategy="continue",
                reason="The user appears confident and engaged.",
                priority="low",
                response_style="natural",
                complexity="advanced",
                detail_level="detailed",
            )

        if needs_clarification:
            if emotion == "uncertain":
                return PolicyDecision(
                    strategy="ask_follow_up",
                    reason=(
                        "The user's state suggests uncertainty, so a "
                        "follow-up question may help clarify their intent."
                    ),
                    priority="medium",
                    response_style="curious",
                    complexity="simple",
                    detail_level="minimal",
                )

            return PolicyDecision(
                strategy="clarify",
                reason="The fused state indicates that clarification may help.",
                priority="medium",
                response_style="clear",
                complexity="simple",
                detail_level="moderate",
            )

        if needs_encouragement:
            return PolicyDecision(
                strategy="encourage",
                reason="The user may benefit from additional encouragement.",
                priority="medium",
                response_style="encouraging",
                complexity="simple",
                detail_level="moderate",
            )

        return PolicyDecision(
            strategy="normal_response",
            reason="No special dialogue adaptation is required.",
            priority="low",
            response_style="natural",
            complexity="moderate",
            detail_level="moderate",
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

    print(DialoguePolicy.decide_to_dict(example_state))
