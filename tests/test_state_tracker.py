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


def test_tracker_starts_empty():
    tracker = StateTracker()

    assert tracker.get_current_state() is None
    assert tracker.get_history() == []
    assert tracker.get_state_changes() == []


def test_add_state_and_get_current_state():
    tracker = StateTracker()
    state = make_state()

    tracker.add_state(state)

    assert tracker.get_current_state() is state


def test_history_preserves_order():
    tracker = StateTracker()

    state1 = make_state(engagement=0.8)
    state2 = make_state(engagement=0.6)

    tracker.add_state(state1)
    tracker.add_state(state2)

    history = tracker.get_history()

    assert history == [state1, state2]


def test_history_returns_copy():
    tracker = StateTracker()
    state = make_state()

    tracker.add_state(state)

    history = tracker.get_history()
    history.clear()

    assert len(tracker.get_history()) == 1


def test_invalid_state_raises_type_error():
    tracker = StateTracker()

    try:
        tracker.add_state("invalid")
        assert False
    except TypeError:
        assert True


def test_clear_removes_history():
    tracker = StateTracker()

    tracker.add_state(make_state())
    tracker.clear()

    assert tracker.get_current_state() is None
    assert tracker.get_history() == []


def test_detects_numeric_state_change():
    tracker = StateTracker(change_threshold=0.1)

    state1 = make_state(engagement=0.8)
    state2 = make_state(engagement=0.5)

    tracker.add_state(state1)
    tracker.add_state(state2)

    changes = tracker.get_state_changes()

    assert len(changes) == 1
    assert changes[0]["from_index"] == 0
    assert changes[0]["to_index"] == 1
    assert changes[0]["changes"]["engagement"]["from"] == 0.8
    assert changes[0]["changes"]["engagement"]["to"] == 0.5


def test_detects_emotion_change():
    tracker = StateTracker()

    state1 = make_state(emotion="neutral")
    state2 = make_state(emotion="excited")

    tracker.add_state(state1)
    tracker.add_state(state2)

    changes = tracker.get_state_changes()

    assert len(changes) == 1
    assert changes[0]["changes"]["emotion"] == {
        "from": "neutral",
        "to": "excited",
    }


def test_ignores_small_numeric_change():
    tracker = StateTracker(change_threshold=0.1)

    state1 = make_state(engagement=0.70)
    state2 = make_state(engagement=0.75)

    tracker.add_state(state1)
    tracker.add_state(state2)

    assert tracker.get_state_changes() == []


def test_detects_multiple_state_changes():
    tracker = StateTracker(change_threshold=0.1)

    state1 = make_state(
        hesitation=0.2,
        confidence=0.8,
        engagement=0.8,
        cognitive_load=0.2,
    )

    state2 = make_state(
        hesitation=0.6,
        confidence=0.5,
        engagement=0.4,
        cognitive_load=0.7,
    )

    tracker.add_state(state1)
    tracker.add_state(state2)

    changes = tracker.get_state_changes()

    changed_fields = changes[0]["changes"]

    assert "hesitation" in changed_fields
    assert "confidence" in changed_fields
    assert "engagement" in changed_fields
    assert "cognitive_load" in changed_fields


def test_negative_threshold_raises_error():
    try:
        StateTracker(change_threshold=-0.1)
        assert False
    except ValueError:
        assert True