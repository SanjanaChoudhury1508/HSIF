import math
import pytest
from ai.human_state.human_state_engine import HumanStateEngine
from ai.human_state.state_tracker import StateTracker

def make_speech_result(
    energy=0.08,
    pauses=1,
    speech=8.0,
    silence=2.0,
    min_pitch=100.0,
    max_pitch=180.0,
):
    return {
        "audio": {
            "duration": speech + silence,
            "speech_duration": speech,
            "silence_duration": silence,
        },
        "features": {
            "number_of_pauses": pauses,
            "average_pause_duration": 0.3,
            "max_pause_duration": 0.6,
            "mean_energy": energy,
            "mean_pitch": 170.0,
            "min_pitch": min_pitch,
            "max_pitch": max_pitch,
        },
        "vad": {},
    }


def test_engine_automatically_tracks_processed_state():
    tracker = StateTracker()
    engine = HumanStateEngine(state_tracker=tracker)

    state = engine.process(make_speech_result())

    assert engine.get_current_state() is state
    assert len(engine.get_state_history()) == 1


def test_engine_tracks_multiple_states():
    engine = HumanStateEngine()

    state1 = engine.process(
        make_speech_result(
            energy=0.05,
            pauses=1,
        )
    )

    state2 = engine.process(
        make_speech_result(
            energy=0.10,
            pauses=5,
        )
    )

    history = engine.get_state_history()

    assert len(history) == 2
    assert history[0] is state1
    assert history[1] is state2


def test_engine_exposes_trajectory():
    engine = HumanStateEngine()

    engine.process(make_speech_result())
    engine.process(make_speech_result(energy=0.10))

    trajectory = engine.get_state_trajectory()

    assert len(trajectory) == 2
    assert trajectory[0]["step"] == 0
    assert trajectory[1]["step"] == 1


def test_engine_exposes_state_changes():
    engine = HumanStateEngine()

    engine.process(
        make_speech_result(
            energy=0.10,
            pauses=1,
            speech=9.0,
            silence=1.0,
        )
    )

    engine.process(
        make_speech_result(
            energy=0.02,
            pauses=8,
            speech=4.0,
            silence=6.0,
        )
    )

    changes = engine.get_state_changes()

    assert len(changes) >= 1


def test_engine_can_clear_state_history():
    engine = HumanStateEngine()

    engine.process(make_speech_result())
    engine.process(make_speech_result())

    engine.clear_state_history()

    assert engine.get_current_state() is None
    assert engine.get_state_history() == []
    assert engine.get_state_trajectory() == []


def test_custom_tracker_is_used():
    tracker = StateTracker(change_threshold=0.2)
    engine = HumanStateEngine(state_tracker=tracker)

    engine.process(make_speech_result())

    assert engine.state_tracker is tracker
    assert len(tracker.get_history()) == 1


def test_engine_passes_temporal_inputs_to_tracked_state():
    engine = HumanStateEngine()

    state = engine.process(
        make_speech_result(),
        timestamp=10.5,
        observation_valid=False,
    )

    assert state.timestamp == 10.5
    assert state.observation_valid is False
    assert engine.get_current_state() is state


def test_engine_process_to_dict_preserves_five_field_hsr():
    engine = HumanStateEngine()

    result = engine.process_to_dict(
        make_speech_result(),
        timestamp=10.5,
        observation_valid=True,
    )

    assert set(result) == {
        "emotion",
        "hesitation",
        "confidence",
        "engagement",
        "cognitive_load",
    }


def test_engine_accepts_calls_without_temporal_inputs():
    engine = HumanStateEngine()

    state = engine.process(make_speech_result())

    assert state.timestamp is None
    assert state.observation_valid is True

def test_temporal_smoothing_is_disabled_by_default():
    engine = HumanStateEngine()

    assert engine.enable_temporal_smoothing is False


def test_engine_can_enable_temporal_smoothing():
    from ai.human_state.temporal_smoother import TemporalSmoother

    smoother = TemporalSmoother(alpha=0.5)
    engine = HumanStateEngine(
        temporal_smoother=smoother,
        enable_temporal_smoothing=True,
    )

    assert engine.temporal_smoother is smoother
    assert engine.enable_temporal_smoothing is True


def test_engine_tracks_smoothed_state_when_enabled():
    from ai.human_state.temporal_smoother import TemporalSmoother

    engine = HumanStateEngine(
        temporal_smoother=TemporalSmoother(alpha=0.5),
        enable_temporal_smoothing=True,
    )

    first = engine.process(
        make_speech_result(energy=0.02, pauses=1)
    )
    second = engine.process(
        make_speech_result(energy=0.12, pauses=8)
    )

    assert engine.get_state_history() == [first, second]
    assert engine.get_current_state() is second


def test_engine_records_invalid_observation_without_smoothing_it():
    from ai.human_state.human_state_engine import HumanStateEngine

    engine = HumanStateEngine(enable_temporal_smoothing=True)

    valid_result = {
        "audio": {"duration": 2.0, "speech_duration": 1.5},
        "features": {},
        "vad": {"speech_segments": [{"start": 0.2, "end": 1.7}]},
    }
    invalid_result = {
        "audio": {"duration": 0.0, "speech_duration": 0.0},
        "features": {},
        "vad": {"speech_segments": []},
    }

    engine.process(
        valid_result,
        timestamp=1.0,
        observation_valid=True,
    )
    baseline = engine.temporal_smoother._previous

    invalid_state = engine.process(
        invalid_result,
        timestamp=2.0,
        observation_valid=False,
    )

    assert invalid_state.observation_valid is False
    assert engine.temporal_smoother._previous is baseline
    assert len(engine.get_state_history()) == 2
    assert engine.get_state_history()[-1].observation_valid is False


def test_clear_state_history_resets_temporal_smoother():
    from ai.human_state.temporal_smoother import TemporalSmoother

    smoother = TemporalSmoother(alpha=0.5)
    engine = HumanStateEngine(
        temporal_smoother=smoother,
        enable_temporal_smoothing=True,
    )

    engine.process(make_speech_result(energy=0.02, pauses=1))
    assert smoother._previous is not None

    engine.clear_state_history()

    assert engine.get_current_state() is None
    assert engine.get_state_history() == []
    assert smoother._previous is None
    assert smoother._candidate_emotion is None
    assert smoother._candidate_count == 0


def test_emotion_confirmation_keeps_label_and_score_consistent():
    from ai.human_state.hsr import build_human_state
    from ai.human_state.temporal_smoother import TemporalSmoother

    smoother = TemporalSmoother(emotion_confirmation_count=2)

    first = build_human_state(
        emotion_label="neutral",
        emotion_score=0.8,
        hesitation_score=0.5,
        confidence_score=0.5,
        engagement_score=0.5,
        cognitive_load_score=0.5,
    )
    candidate = build_human_state(
        emotion_label="sad",
        emotion_score=0.3,
        hesitation_score=0.5,
        confidence_score=0.5,
        engagement_score=0.5,
        cognitive_load_score=0.5,
    )

    smoother.smooth(first)
    result = smoother.smooth(candidate)

    assert result.emotion.label == "neutral"
    # The pending "sad" score must not be presented as confidence
    # in the currently displayed "neutral" label.
    assert result.emotion.score == first.emotion.score

def test_invalid_observation_returns_neutral_fallback_and_tracks_it():
    engine = HumanStateEngine(enable_temporal_smoothing=True)

    state = engine.process(
        make_speech_result(),
        timestamp=12.0,
        observation_valid=False,
    )

    assert state.observation_valid is False
    assert state.timestamp == 12.0
    assert state.emotion.label == "neutral"
    assert state.emotion.score == 0.5

    for field in (
        "hesitation",
        "confidence",
        "engagement",
        "cognitive_load",
    ):
        assert getattr(state, field).score == 0.5

    assert engine.get_current_state() is state
    assert engine.get_state_history() == [state]


def test_invalid_observation_does_not_call_estimators():
    from unittest.mock import Mock

    engine = HumanStateEngine()
    engine.emotion_detector.detect = Mock(
        side_effect=AssertionError("Estimator should not run")
    )
    engine.hesitation_detector.detect = Mock(
        side_effect=AssertionError("Estimator should not run")
    )
    engine.confidence_estimator.estimate = Mock(
        side_effect=AssertionError("Estimator should not run")
    )
    engine.engagement_estimator.estimate = Mock(
        side_effect=AssertionError("Estimator should not run")
    )

    # Cognitive load is a module-level function, so this test verifies
    # the injected estimators; the early-return path also bypasses it.
    state = engine.process(
        make_speech_result(),
        observation_valid=False,
    )

    assert state.observation_valid is False


def test_invalid_observation_keeps_public_hsr_schema():
    result = HumanStateEngine().process_to_dict(
        make_speech_result(),
        observation_valid=False,
    )

    assert set(result) == {
        "emotion",
        "hesitation",
        "confidence",
        "engagement",
        "cognitive_load",
    }

@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (float("nan"), 0.5),
        (float("inf"), 0.5),
        (float("-inf"), 0.5),
        ("invalid", 0.5),
        (None, 0.5),
        (-0.2, 0.0),
        (1.4, 1.0),
        (0.4567, 0.457),
    ],
)
def test_clamp_score_handles_invalid_and_out_of_range_values(
    value, expected
):
    assert HumanStateEngine._clamp_score(value) == expected


@pytest.mark.parametrize(
    ("result", "expected_label", "expected_score"),
    [
        (None, "neutral", 0.5),
        ({}, "neutral", 0.5),
        ({"label": "excited", "score": 0.8}, "excited", 0.8),
        ({"label": "HAPPY", "score": 0.7}, "happy", 0.7),
        ({"label": " sad ", "score": 0.6}, "sad", 0.6),
        ({"label": "unknown_emotion", "score": 0.9}, "neutral", 0.9),
        ({"label": "", "score": 0.4}, "neutral", 0.4),
        ({"label": None, "score": 0.4}, "neutral", 0.4),
        ({"label": 123, "score": 0.4}, "neutral", 0.4),
    ],
)
def test_normalize_emotion_result_validates_label(
    result, expected_label, expected_score
):
    normalized = HumanStateEngine._normalize_emotion_result(result)

    assert normalized == {
        "label": expected_label,
        "score": expected_score,
    }


def test_out_of_order_timestamp_does_not_corrupt_smoother_baseline():
    from ai.human_state.temporal_smoother import TemporalSmoother

    engine = HumanStateEngine(
        temporal_smoother=TemporalSmoother(alpha=0.5),
        enable_temporal_smoothing=True,
    )

    first = engine.process(
        make_speech_result(energy=0.02),
        timestamp=10.0,
    )
    previous_baseline = engine.temporal_smoother._previous
    previous_history = engine.get_state_history()

    with pytest.raises(ValueError, match="non-decreasing"):
        engine.process(
            make_speech_result(energy=0.12),
            timestamp=9.0,
        )

    assert engine.get_state_history() == previous_history
    assert engine.get_current_state() is first
    assert engine.temporal_smoother._previous is previous_baseline


def test_invalid_observation_with_older_timestamp_does_not_corrupt_history():
    engine = HumanStateEngine(enable_temporal_smoothing=True)

    first = engine.process(
        make_speech_result(),
        timestamp=10.0,
    )

    with pytest.raises(ValueError, match="non-decreasing"):
        engine.process(
            make_speech_result(),
            timestamp=9.0,
            observation_valid=False,
        )

    assert engine.get_state_history() == [first]
    assert engine.get_current_state() is first

def test_tracker_rejection_does_not_corrupt_smoother_baseline():
    from ai.human_state.temporal_smoother import TemporalSmoother

    smoother = TemporalSmoother(alpha=0.5)
    engine = HumanStateEngine(
        temporal_smoother=smoother,
        enable_temporal_smoothing=True,
    )

    # Establish the initial baseline at t=10.
    engine.process(make_speech_result(), timestamp=10.0)

    # Invalid observations enter tracker history but do not update
    # the temporal smoother's baseline.
    engine.process(
        make_speech_result(),
        timestamp=12.0,
        observation_valid=False,
    )

    previous_baseline = smoother._previous
    previous_history = engine.get_state_history()
    previous_current_state = engine.get_current_state()

    # The smoother accepts t=11 relative to its t=10 baseline,
    # but the tracker must reject it because its latest timestamp is t=12.
    with pytest.raises(ValueError, match="non-decreasing"):
        engine.process(make_speech_result(), timestamp=11.0)

    # A rejected observation must not leave internal components inconsistent.
    assert smoother._previous is previous_baseline
    assert engine.get_state_history() == previous_history
    assert engine.get_current_state() is previous_current_state
