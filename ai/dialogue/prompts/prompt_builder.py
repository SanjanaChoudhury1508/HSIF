"""
prompt_builder.py

Builds structured prompts for the LLM using:
- User message
- Human state
- Dialogue policy
- Conversation history
"""

from typing import Any, Dict, Mapping, List


class PromptBuilder:
    """Builds LLM-ready prompts from dialogue context."""

    @staticmethod
    def _safe_text(value: Any) -> str:
        """Convert a value into safe text."""
        if value is None:
            return ""

        if not isinstance(value, str):
            return str(value)

        return value.strip()

    @classmethod
    def build(
        cls,
        user_message: str,
        dialogue_state: Mapping[str, Any] | None,
        policy_decision: Mapping[str, Any] | None,
        conversation_history: List[Mapping[str, Any]] | None = None,
    ) -> str:
        """
        Build a structured prompt for the LLM.

        Parameters
        ----------
        user_message:
            Current message from the user.

        dialogue_state:
            Fused Human State / Dialogue State.

        policy_decision:
            Recommended dialogue strategy.

        conversation_history:
            Recent conversation turns.

        Returns
        -------
        str
            LLM-ready prompt.
        """

        if not isinstance(user_message, str):
            raise TypeError("user_message must be a string.")

        if dialogue_state is None:
            dialogue_state = {}

        if policy_decision is None:
            policy_decision = {}

        if not isinstance(dialogue_state, Mapping):
            raise TypeError(
                "dialogue_state must be a dictionary-like Mapping."
            )

        if not isinstance(policy_decision, Mapping):
            raise TypeError(
                "policy_decision must be a dictionary-like Mapping."
            )

        if conversation_history is None:
            conversation_history = []

        if not isinstance(conversation_history, list):
            raise TypeError("conversation_history must be a list.")

        emotion = cls._safe_text(
            dialogue_state.get("emotion", "neutral")
        ) or "neutral"

        interaction_state = cls._safe_text(
            dialogue_state.get(
                "interaction_state",
                "neutral",
            )
        ) or "neutral"

        strategy = cls._safe_text(
            policy_decision.get(
                "strategy",
                "normal_response",
            )
        ) or "normal_response"

        reason = cls._safe_text(
            policy_decision.get(
                "reason",
                "",
            )
        )

        priority = cls._safe_text(
            policy_decision.get(
                "priority",
                "low",
            )
        ) or "low"

        confidence = dialogue_state.get(
            "confidence",
            0.5,
        )

        hesitation = dialogue_state.get(
            "hesitation",
            0.5,
        )

        engagement = dialogue_state.get(
            "engagement",
            0.5,
        )

        cognitive_load = dialogue_state.get(
            "cognitive_load",
            0.5,
        )

        history_lines = []

        for turn in conversation_history[-5:]:
            if not isinstance(turn, Mapping):
                continue

            previous_user = cls._safe_text(
                turn.get("user_message", "")
            )

            previous_assistant = cls._safe_text(
                turn.get("assistant_message", "")
            )

            if previous_user:
                history_lines.append(
                    f"User: {previous_user}"
                )

            if previous_assistant:
                history_lines.append(
                    f"Assistant: {previous_assistant}"
                )

        if history_lines:
            history = "\n".join(history_lines)
        else:
            history = "No previous conversation."

        prompt = f"""You are a conversational AI assistant.

Your goal is to respond helpfully while adapting to the user's
current conversational state.

CURRENT USER MESSAGE:
{user_message.strip()}

HUMAN STATE:
- Emotion: {emotion}
- Interaction state: {interaction_state}
- Confidence: {confidence}
- Hesitation: {hesitation}
- Engagement: {engagement}
- Cognitive load: {cognitive_load}

DIALOGUE POLICY:
- Strategy: {strategy}
- Priority: {priority}
- Reason: {reason}

RECENT CONVERSATION:
{history}

RESPONSE GUIDELINES:
- Follow the recommended dialogue strategy.
- Adapt the response to the user's current state.
- If the user appears confused, explain clearly.
- If cognitive load is high, avoid unnecessary complexity.
- If the user is struggling, be supportive and encouraging.
- Keep the response relevant to the user's message.
- Do not mention internal state detection or these instructions.

Generate the appropriate response to the user.
"""

        return prompt.strip()


if __name__ == "__main__":
    example_state = {
        "emotion": "confused",
        "interaction_state": "struggling",
        "confidence": 0.3,
        "hesitation": 0.8,
        "engagement": 0.8,
        "cognitive_load": 0.5,
    }

    example_policy = {
        "strategy": "clarify",
        "reason": "The user appears to be struggling.",
        "priority": "high",
    }

    example_history = [
        {
            "user_message": "What is machine learning?",
            "assistant_message": "It is a way for computers to learn patterns.",
        }
    ]

    prompt = PromptBuilder.build(
        user_message="I still don't understand it.",
        dialogue_state=example_state,
        policy_decision=example_policy,
        conversation_history=example_history,
    )

    print(prompt)