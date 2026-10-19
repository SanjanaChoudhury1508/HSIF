from ai.human_state.hsr import (
    EmotionResult,
    ScoreResult,
    HumanState,
)
from ai.human_state.state_tracker import StateTracker


def make_state(
    emotion="neutral",
    emotion_score=0.5,
    hesitation=0.3,
    confidence=0.7,
    engagement=0.7,
    cognitive_load=0.3,
):
    return HumanState(
        emotion=EmotionResult(
            label=emotion,
            score=emotion_score,
        ),
        hesitation=ScoreResult(hesitation),
        confidence=ScoreResult(confidence),
        engagement=ScoreResult(engagement),
        cognitive_load=ScoreResult(cognitive_load),
    )


def test_empty_tracker_has_empty_trajectory():
    tracker = StateTracker()

    assert tracker.get_trajectory() == []


def test_single_state_creates_first_trajectory_step():
    tracker = StateTracker()

    tracker.add_state(
        make_state(
            emotion="neutral",
            engagement=0.8,
            confidence=0.9,
            hesitation=0.2,
            cognitive_load=0.2,
        )
    )

    trajectory = tracker.get_trajectory()

    assert len(trajectory) == 1
    assert trajectory[0]["step"] == 0
    assert trajectory[0]["emotion"]["label"] == "neutral"
    assert trajectory[0]["emotion"]["score"] == 0.5
    assert trajectory[0]["engagement"] == 0.8
    assert trajectory[0]["confidence"] == 0.9
    assert trajectory[0]["hesitation"] == 0.2
    assert trajectory[0]["cognitive_load"] == 0.2


def test_multiple_states_preserve_trajectory_order():
    tracker = StateTracker()

    tracker.add_state(
        make_state(
            emotion="neutral",
            engagement=0.8,
        )
    )

    tracker.add_state(
        make_state(
            emotion="happy",
            engagement=0.6,
        )
    )

    tracker.add_state(
        make_state(
            emotion="sad",
            engagement=0.4,
        )
    )

    trajectory = tracker.get_trajectory()

    assert len(trajectory) == 3
    assert [item["step"] for item in trajectory] == [0, 1, 2]
    assert [
        item["emotion"]["label"]
        for item in trajectory
    ] == ["neutral", "happy", "sad"]

    assert [
        item["engagement"]
        for item in trajectory
    ] == [0.8, 0.6, 0.4]


def test_trajectory_reflects_state_changes():
    tracker = StateTracker()

    tracker.add_state(
        make_state(
            engagement=0.8,
            cognitive_load=0.2,
        )
    )

    tracker.add_state(
        make_state(
            engagement=0.5,
            cognitive_load=0.6,
        )
    )

    trajectory = tracker.get_trajectory()

    assert trajectory[0]["engagement"] == 0.8
    assert trajectory[1]["engagement"] == 0.5
    assert trajectory[0]["cognitive_load"] == 0.2
    assert trajectory[1]["cognitive_load"] == 0.6


def test_clear_resets_trajectory():
    tracker = StateTracker()

    tracker.add_state(make_state())
    tracker.add_state(make_state())

    tracker.clear()

    assert tracker.get_trajectory() == []


def test_trajectory_is_json_friendly():
    tracker = StateTracker()

    tracker.add_state(
        make_state(
            emotion="excited",
            emotion_score=0.8,
            hesitation=0.2,
            confidence=0.9,
            engagement=0.85,
            cognitive_load=0.25,
        )
    )

    trajectory = tracker.get_trajectory()

    assert isinstance(trajectory, list)
    assert isinstance(trajectory[0], dict)
    assert isinstance(trajectory[0]["emotion"], dict)
    assert isinstance(trajectory[0]["step"], int)