
"""Temporal smoothing for successive HumanState observations."""

from ai.human_state.hsr import HumanState, build_human_state


class TemporalSmoother:
    """Smooth numeric state scores and stabilize emotion transitions."""

    _SCORE_FIELDS = (
        "hesitation",
        "confidence",
        "engagement",
        "cognitive_load",
    )

    def __init__(
        self,
        alpha: float = 0.4,
        emotion_confirmation_count: int = 2,
    ) -> None:
        if isinstance(alpha, bool) or not isinstance(alpha, (int, float)):
            raise TypeError("alpha must be numeric")
        if not 0.0 < alpha <= 1.0:
            raise ValueError("alpha must be in (0, 1]")

        if (
            isinstance(emotion_confirmation_count, bool)
            or not isinstance(emotion_confirmation_count, int)
            or emotion_confirmation_count < 1
        ):
            raise ValueError(
                "emotion_confirmation_count must be a positive integer"
            )

        self.alpha = float(alpha)
        self.emotion_confirmation_count = emotion_confirmation_count
        self._previous: HumanState | None = None
        self._candidate_emotion: str | None = None
        self._candidate_count = 0

    def reset(self) -> None:
        """Clear temporal context, for example when starting a new session."""
        self._previous = None
        self._candidate_emotion = None
        self._candidate_count = 0

    def smooth(self, state: HumanState) -> HumanState:
        """Return a smoothed state while preserving temporal metadata."""
        if not isinstance(state, HumanState):
            raise TypeError("state must be a HumanState")

        if not state.observation_valid:
            # Preserve the invalid observation for the caller/tracker, but
            # don't let it alter the reliable smoothing baseline.
            return state

        if self._previous is None:
            self._previous = state
            return state

        previous = self._previous

        if (
            previous.timestamp is not None
            and state.timestamp is not None
            and state.timestamp < previous.timestamp
        ):
            raise ValueError("state timestamps must be non-decreasing")

        smoothed_scores = {}

        for name in self._SCORE_FIELDS:
            old_score = getattr(previous, name).score
            new_score = getattr(state, name).score

            score = (
                self.alpha * new_score
                + (1.0 - self.alpha) * old_score
            )
            smoothed_scores[name] = max(0.0, min(1.0, score))

        emotion_label = self._smooth_emotion(
            previous.emotion.label,
            state.emotion.label,
        )

        emotion_score = (
            state.emotion.score
            if emotion_label == state.emotion.label
            else previous.emotion.score
        )

        result = build_human_state(
            emotion_label=emotion_label,
            emotion_score=emotion_score,
            hesitation_score=smoothed_scores["hesitation"],
            confidence_score=smoothed_scores["confidence"],
            engagement_score=smoothed_scores["engagement"],
            cognitive_load_score=smoothed_scores["cognitive_load"],
            timestamp=state.timestamp,
            observation_valid=state.observation_valid,
        )

        self._previous = result
        return result

    def _smooth_emotion(
        self,
        previous_label: str,
        current_label: str,
    ) -> str:
        if current_label == previous_label:
            self._candidate_emotion = None
            self._candidate_count = 0
            return current_label

        if current_label != self._candidate_emotion:
            self._candidate_emotion = current_label
            self._candidate_count = 1
        else:
            self._candidate_count += 1

        if self._candidate_count >= self.emotion_confirmation_count:
            self._candidate_emotion = None
            self._candidate_count = 0
            return current_label

        return previous_label
