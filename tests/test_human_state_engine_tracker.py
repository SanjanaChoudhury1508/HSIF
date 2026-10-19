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
