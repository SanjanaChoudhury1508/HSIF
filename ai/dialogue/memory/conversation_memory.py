"""
conversation_memory.py

Maintains a lightweight conversation history for the
Dialogue Engine.
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List


@dataclass
class ConversationTurn:
    """Represents one user-assistant conversation turn."""

    user_message: str
    assistant_message: str

    def to_dict(self) -> Dict[str, str]:
        """Convert the conversation turn into a dictionary."""
        return asdict(self)


class ConversationMemory:
    """
    Stores recent conversation turns.

    The memory is intentionally lightweight for the prototype.
    """

    def __init__(self, max_turns: int = 10):
        if not isinstance(max_turns, int):
            raise TypeError("max_turns must be an integer.")

        if max_turns <= 0:
            raise ValueError("max_turns must be greater than zero.")

        self.max_turns = max_turns
        self._history: List[ConversationTurn] = []

    def add_turn(
        self,
        user_message: str,
        assistant_message: str,
    ) -> None:
        """Add a conversation turn to memory."""

        if not isinstance(user_message, str):
            raise TypeError("user_message must be a string.")

        if not isinstance(assistant_message, str):
            raise TypeError("assistant_message must be a string.")

        turn = ConversationTurn(
            user_message=user_message.strip(),
            assistant_message=assistant_message.strip(),
        )

        self._history.append(turn)

        # Keep only the most recent turns.
        self._history = self._history[-self.max_turns:]

    def get_history(self) -> List[Dict[str, str]]:
        """Return the conversation history."""

        return [
            turn.to_dict()
            for turn in self._history
        ]

    def get_recent(
        self,
        count: int = 3,
    ) -> List[Dict[str, str]]:
        """Return the most recent conversation turns."""

        if not isinstance(count, int):
            raise TypeError("count must be an integer.")

        if count < 0:
            raise ValueError("count cannot be negative.")

        return [
            turn.to_dict()
            for turn in self._history[-count:]
        ]

    def clear(self) -> None:
        """Clear all stored conversation history."""

        self._history.clear()

    def __len__(self) -> int:
        """Return the number of stored conversation turns."""

        return len(self._history)


if __name__ == "__main__":
    memory = ConversationMemory(max_turns=3)

    memory.add_turn(
        "What is machine learning?",
        "Machine learning allows systems to learn patterns from data.",
    )

    memory.add_turn(
        "Can you explain it simply?",
        "It means teaching a computer to recognize patterns from examples.",
    )

    print(memory.get_history())