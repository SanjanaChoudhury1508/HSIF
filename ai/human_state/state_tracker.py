
from typing import Any
from math import isfinite

from .hsr import HumanState


class StateTracker:
    def __init__(self, change_threshold: float = 0.1):
        if (
            isinstance(change_threshold, bool)
            or not isinstance(change_threshold, (int, float))
            or not isfinite(change_threshold)
            or change_threshold < 0
        ):
            raise ValueError("change_threshold must be a finite non-negative number")

        self.change_threshold = float(change_threshold)
        self._history: list[HumanState] = []

    def add_state(self, state: HumanState) -> HumanState:
        if not isinstance(state, HumanState):
            raise TypeError("state must be a HumanState")

        if state.timestamp is not None and self._history:
            previous_timestamp = self._history[-1].timestamp

            if (
                previous_timestamp is not None
                and state.timestamp < previous_timestamp
            ):
                raise ValueError("state timestamps must be non-decreasing")

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

    def get_trajectory(self) -> list[dict[str, Any]]:
        trajectory = []

        for index, state in enumerate(self._history):
            entry = {
                "step": index,
                "emotion": {
                    "label": state.emotion.label,
                    "score": state.emotion.score,
                },
                "hesitation": state.hesitation.score,
                "confidence": state.confidence.score,
                "engagement": state.engagement.score,
                "cognitive_load": state.cognitive_load.score,
            }

            # Include temporal fields only when available, preserving the
            # existing trajectory format for states without metadata.
            if state.timestamp is not None:
                entry["timestamp"] = state.timestamp

            entry["observation_valid"] = state.observation_valid
            trajectory.append(entry)

        return trajectory

    def get_state_changes(self) -> list[dict[str, Any]]:
        changes = []
        previous_valid = None

        for index, current in enumerate(self._history):
            if not current.observation_valid:
                continue

            if previous_valid is None:
                previous_valid = (index, current)
                continue

            previous_index, previous = previous_valid
            state_changes = {}

            if previous.emotion.label != current.emotion.label:
                state_changes["emotion"] = {
                    "from": previous.emotion.label,
                    "to": current.emotion.label,
                }

            for field in (
                "hesitation",
                "confidence",
                "engagement",
                "cognitive_load",
            ):
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
                change = {
                    "from_index": previous_index,
                    "to_index": index,
                    "changes": state_changes,
                }

                if (
                    previous.timestamp is not None
                    and current.timestamp is not None
                ):
                    change["elapsed_seconds"] = (
                        current.timestamp - previous.timestamp
                    )

                changes.append(change)

            previous_valid = (index, current)

        return changes