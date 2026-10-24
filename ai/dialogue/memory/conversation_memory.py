
"""
conversation_memory.py

Maintains a lightweight conversation history for the
Dialogue Engine.
"""

import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Set


@dataclass
class ConversationTurn:
    """Represents one user-assistant conversation turn."""

    user_message: str
    assistant_message: str
    human_state: Dict[str, Any] | None = None
    dialogue_strategy: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert the conversation turn into a dictionary."""
        return asdict(self)


class ConversationMemory:
    """
    Stores bounded conversation history and retrieves relevant turns.

    Relevance retrieval uses lightweight lexical matching and does not
    require external embedding models or services.
    """

    _STOP_WORDS = {
        "a", "an", "and", "are", "as", "at", "be", "but", "by",
        "can", "could", "did", "do", "does", "for", "from", "had",
        "has", "have", "how", "i", "if", "in", "into", "is", "it",
        "its", "me", "my", "of", "on", "or", "our", "please",
        "should", "so", "that", "the", "their", "them", "there",
        "this", "to", "was", "we", "were", "what", "when", "where",
        "which", "who", "why", "will", "with", "would", "you", "your",
    }

    def __init__(self, max_turns: int = 10):
        if isinstance(max_turns, bool) or not isinstance(max_turns, int):
            raise TypeError("max_turns must be an integer.")

        if max_turns <= 0:
            raise ValueError("max_turns must be greater than zero.")

        self.max_turns = max_turns
        self._history: List[ConversationTurn] = []

    def add_turn(
        self,
        user_message: str,
        assistant_message: str,
        human_state: Dict[str, Any] | None = None,
        dialogue_strategy: str | None = None,
    ) -> None:
        """Add a conversation turn to memory."""

        if not isinstance(user_message, str):
            raise TypeError("user_message must be a string.")

        if not isinstance(assistant_message, str):
            raise TypeError("assistant_message must be a string.")

        if human_state is not None and not isinstance(human_state, dict):
            raise TypeError("human_state must be a dictionary or None.")

        if dialogue_strategy is not None and not isinstance(
            dialogue_strategy, str
        ):
            raise TypeError("dialogue_strategy must be a string or None.")

        turn = ConversationTurn(
            user_message=user_message.strip(),
            assistant_message=assistant_message.strip(),
            human_state=human_state,
            dialogue_strategy=dialogue_strategy,
        )

        self._history.append(turn)
        self._history = self._history[-self.max_turns:]

    def get_history(self) -> List[Dict[str, Any]]:
        """Return the complete retained conversation history."""
        return [turn.to_dict() for turn in self._history]

    def get_recent(
        self,
        count: int = 3,
    ) -> List[Dict[str, Any]]:
        """Return the most recent conversation turns."""

        if isinstance(count, bool) or not isinstance(count, int):
            raise TypeError("count must be an integer.")

        if count < 0:
            raise ValueError("count cannot be negative.")

        if count == 0:
            return []

        return [
            turn.to_dict()
            for turn in self._history[-count:]
        ]

    @classmethod
    def _tokenize(cls, text: str) -> Set[str]:
        """Extract meaningful lowercase words for lexical matching."""
        words = re.findall(r"\b[a-z0-9_+#.-]+\b", text.lower())
        return {
            word for word in words
            if word not in cls._STOP_WORDS and len(word) > 1
        }

    @classmethod
    def _turn_relevance(
        cls,
        query_tokens: Set[str],
        turn: ConversationTurn,
    ) -> float:
        """Score a turn by lexical overlap with the current query."""
        if not query_tokens:
            return 0.0

        user_tokens = cls._tokenize(turn.user_message)
        assistant_tokens = cls._tokenize(turn.assistant_message)

        user_overlap = len(query_tokens & user_tokens)
        assistant_overlap = len(query_tokens & assistant_tokens)

        # A match in the original user message is more direct evidence
        # of topic relevance than a match only in the answer.
        return (2.0 * user_overlap) + assistant_overlap

    def get_relevant(
        self,
        query: str,
        count: int = 3,
        include_recent: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant prior turns, preferring lexical matches.

        Results are returned in chronological order for prompt construction.
        Recent turns can be included as fallback context.
        """
        if not isinstance(query, str):
            raise TypeError("query must be a string.")

        if isinstance(count, bool) or not isinstance(count, int):
            raise TypeError("count must be an integer.")

        if count < 0:
            raise ValueError("count cannot be negative.")

        if not isinstance(include_recent, bool):
            raise TypeError("include_recent must be a boolean.")

        if count == 0 or not self._history:
            return []

        query_tokens = self._tokenize(query)

        scored_turns = [
            (index, self._turn_relevance(query_tokens, turn))
            for index, turn in enumerate(self._history)
        ]

        relevant = [
            index
            for index, score in scored_turns
            if score > 0
        ]

        # Rank strongest matches first; break ties in favor of newer turns.
        relevant.sort(
            key=lambda index: (
                self._turn_relevance(query_tokens, self._history[index]),
                index,
            ),
            reverse=True,
        )

        selected = relevant[:count]

        if include_recent and len(selected) < count:
            recent_indices = list(
                range(max(0, len(self._history) - count), len(self._history))
            )

            for index in reversed(recent_indices):
                if index not in selected:
                    selected.append(index)
                if len(selected) >= count:
                    break

        selected.sort()

        return [self._history[index].to_dict() for index in selected]

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
    print(memory.get_relevant("machine learning patterns"))
