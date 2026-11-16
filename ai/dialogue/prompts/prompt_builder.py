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
        response_style = cls._safe_text(
            policy_decision.get(
                "response_style",
                "natural",
            )
        ) or "natural"

        complexity = cls._safe_text(
            policy_decision.get(
                "complexity",
                "moderate",
            )
        ) or "moderate"

        detail_level = cls._safe_text(
            policy_decision.get(
                "detail_level",
                "moderate",
            )
        ) or "moderate"


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

        strategy_guidelines = {
            "normal_response": (
                "Respond naturally and directly to the user's request."
            ),
            "clarify": (
                "Clarify the user's confusion before proceeding."
            ),
            "simplify": (
                "Use simpler language, reduce complexity, "
                "and explain one idea at a time."
            ),
            "reassure": (
                "Use supportive language and provide a clear explanation."
            ),
            "encourage": (
                "Use encouraging language while remaining informative."
            ),
            "slow_down": (
                "Explain the topic step by step without rushing."
            ),
            "ask_follow_up": (
                "Ask one focused follow-up question to understand the user's need."
            ),
            "reduce_information": (
                "Keep the response concise and focus on essential information."
            ),
            "acknowledge_frustration": (
                "Acknowledge the user's frustration and help resolve the issue."
            ),
            "re_engage": (
                "Use a concise and engaging response."
            ),
            "continue": (
                "Continue naturally with an appropriately detailed response."
            ),
        }

        strategy_instruction = strategy_guidelines.get(
            strategy,
            "Respond naturally while adapting to the user's current state.",
        )

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
- Strategy instruction: {strategy_instruction}
- Priority: {priority}
- Reason: {reason}
- Response style: {response_style}
- Explanation complexity: {complexity}
- Detail level: {detail_level}

RECENT CONVERSATION:
{history}



RESPONSE GUIDELINES:
1. Directly answer the CURRENT USER MESSAGE.
2. Identify the user's actual question, request, or task before generating the response.
3. Do not merely acknowledge, paraphrase, or repeat the user's message.
4. If the user requests guidance, provide actionable recommendations.
5. If the user requests a plan, provide an ordered and realistic plan.
6. If the user requests an explanation, explain the concept with relevant examples.
7. If the user requests a breakdown, provide a structured breakdown of the requested topic.
8. Use conversation history to understand context, but prioritize the current user message.
9. Do not ask the user to repeat information already available in conversation history.
10. Ask a follow-up question only when essential information is genuinely missing.
11. When sufficient information is available, provide a useful answer immediately.
12. Never invent project features, technical results, or facts.
13. Be specific, informative, and relevant. Avoid filler and generic responses.

DIALOGUE ADAPTATION:
- Follow the selected dialogue strategy when adapting tone, complexity, and detail.
- Do not allow the dialogue strategy to override the user's explicit request.
- A request for a detailed explanation must remain detailed unless there is a strong reason to simplify.
- A request for a step-by-step breakdown should receive actionable steps.
- If cognitive load is high, organize the response into smaller sections rather than omitting essential information.
- If confidence is low, use clear explanations and supportive language without being patronizing.
- If engagement is high, maintain an appropriately informative and interactive response.

Generate a complete and useful response.
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