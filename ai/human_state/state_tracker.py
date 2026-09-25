from typing import Any
from .hsr import HumanState


class StateTracker:
    def __init__(self, change_threshold: float = 0.1):
        if change_threshold < 0:
            raise ValueError("change_threshold must be non-negative")

        self.change_threshold = change_threshold
        self._history: list[HumanState] = []

    def add_state(self, state: HumanState) -> HumanState:
        if not isinstance(state, HumanState):
            raise TypeError("state must be a HumanState")

        self._history.append(state)
        return state

    def get_current_state(self) -> HumanState | None:
        if not self._history:
            return None

        return self._history[-1]

    def get_history(self) -> list[HumanState]:
        return list(self._history)

    def clear(self) -> None:
        self._history.clear()

    def get_state_changes(self) -> list[dict[str, Any]]:
        changes = []

        for i in range(1, len(self._history)):
            previous = self._history[i - 1]
            current = self._history[i]

            state_changes = {}

            if previous.emotion.label != current.emotion.label:
                state_changes["emotion"] = {
                    "from": previous.emotion.label,
                    "to": current.emotion.label,
                }

            numeric_fields = [
                "hesitation",
                "confidence",
                "engagement",
                "cognitive_load",
            ]

            for field in numeric_fields:
                previous_score = getattr(previous, field).score
                current_score = getattr(current, field).score
                delta = current_score - previous_score

                if abs(delta) >= self.change_threshold:
                    state_changes[field] = {
                        "from": previous_score,
                        "to": current_score,
                        "delta": delta,
                    }

            if state_changes:
                changes.append(
                    {
                        "from_index": i - 1,
                        "to_index": i,
                        "changes": state_changes,
                    }
                )

        return changes