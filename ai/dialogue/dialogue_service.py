"""
dialogue_service.py

Coordinates the Dialogue Engine pipeline:

Human State
    ↓
State Fusion
    ↓
Dialogue Policy
    ↓
Conversation Memory
    ↓
Prompt Builder
"""

from typing import Any, Dict, Mapping

from ai.dialogue.fusion.state_fusion import StateFusion
from ai.dialogue.memory.conversation_memory import ConversationMemory
from ai.dialogue.policy.dialogue_policy import DialoguePolicy
from ai.dialogue.prompts.prompt_builder import PromptBuilder


class DialogueService:
    """Coordinates the complete dialogue processing pipeline."""

    def __init__(self, max_memory_turns: int = 10):
        self.memory = ConversationMemory(
            max_turns=max_memory_turns
        )

    def process(
        self,
        user_message: str,
        human_state: Mapping[str, Any] | None,
    ) -> Dict[str, Any]:
        """
        Process a user message through the Dialogue Engine.

        Parameters
        ----------
        user_message:
            Current user message.

        human_state:
            Human State Representation produced by the
            Human State Engine.

        Returns
        -------
        dict
            Dialogue state, policy decision, memory,
            and LLM-ready prompt.
        """

        if not isinstance(user_message, str):
            raise TypeError("user_message must be a string.")

        if human_state is None:
            human_state = {}

        if not isinstance(human_state, Mapping):
            raise TypeError(
                "human_state must be a dictionary-like Mapping."
            )

        # 1. Fuse Human State into Dialogue State.
        dialogue_state = StateFusion.fuse_to_dict(
            human_state
        )

        # 2. Determine the recommended response strategy.
        policy_decision = DialoguePolicy.decide_to_dict(
            dialogue_state
        )

        # 3. Retrieve recent conversation history
        # before adding the current turn.
        history = self.memory.get_recent(5)

        # 4. Build an LLM-ready prompt.
        prompt = PromptBuilder.build(
            user_message=user_message,
            dialogue_state=dialogue_state,
            policy_decision=policy_decision,
            conversation_history=history,
        )

        return {
            "dialogue_state": dialogue_state,
            "policy": policy_decision,
            "history": history,
            "prompt": prompt,
        }

    def add_response(
        self,
        user_message: str,
        assistant_message: str,
    ) -> None:
        """
        Store the completed user-assistant interaction.

        This should be called after the LLM generates
        the assistant's response.
        """

        self.memory.add_turn(
            user_message=user_message,
            assistant_message=assistant_message,
        )

    def get_history(self):
        """Return the stored conversation history."""
        return self.memory.get_history()

    def clear_memory(self) -> None:
        """Clear the conversation memory."""
        self.memory.clear()


if __name__ == "__main__":
    service = DialogueService()

    human_state = {
        "emotion": {
            "label": "confused",
            "score": 0.8,
        },
        "hesitation": {
            "score": 0.8,
        },
        "confidence": {
            "score": 0.3,
        },
        "engagement": {
            "score": 0.8,
        },
        "cognitive_load": {
            "score": 0.5,
        },
    }

    result = service.process(
        user_message="I still don't understand this concept.",
        human_state=human_state,
    )

    print("DIALOGUE STATE")
    print(result["dialogue_state"])

    print("\nPOLICY")
    print(result["policy"])

    print("\nPROMPT")
    print(result["prompt"])