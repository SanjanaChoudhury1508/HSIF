import math

import pytest

from ai.human_state.human_state_engine import HumanStateEngine
from ai.human_state.hsr import HumanState


def make_speech_result(
    duration=6.0,
    speech_duration=5.5,
    silence_duration=0.5,
    number_of_pauses=1,
    average_pause_duration=0.4,
    max_pause_duration=0.5,
    mean_energy=0.08,
    mean_pitch=180.0,
    min_pitch=100.0,
    max_pitch=230.0,
):
    return {
        "transcript": "Hello, this is a test.",
        "language": "en",
        "language_probability": 0.95,
        "audio": {
            "duration": duration,
            "speech_duration": speech_duration,
            "silence_duration": silence_duration,
        },
        "features": {
            "number_of_pauses": number_of_pauses,
            "average_pause_duration": average_pause_duration,
            "max_pause_duration": max_pause_duration,
            "mean_energy": mean_energy,
            "mean_pitch": mean_pitch,
            "min_pitch": min_pitch,
            "max_pitch": max_pitch,
        },
        "vad": {
            "speech_segments": [],
            "pauses": [],
        },
    }


@pytest.fixture
def engine():
    return HumanStateEngine()


def assert_valid_score(score):
    assert isinstance(score, (int, float))
    assert math.isfinite(score)
    assert 0.0 <= score <= 1.0


def test_engine_returns_human_state(engine):
    speech_result = make_speech_result()

    result = engine.process(speech_result)

    assert isinstance(result, HumanState)


def test_human_state_contains_all_required_components(engine):
    result = engine.process_to_dict(make_speech_result())

    assert set(result.keys()) == {
        "emotion",
        "hesitation",
        "confidence",
        "engagement",
        "cognitive_load",
    }


def test_emotion_has_label_and_score(engine):
    result = engine.process_to_dict(make_speech_result())

    assert isinstance(result["emotion"]["label"], str)
    assert result["emotion"]["label"]

    assert_valid_score(result["emotion"]["score"])


@pytest.mark.parametrize(
    "field",
    [
        "hesitation",
        "confidence",
        "engagement",
        "cognitive_load",
    ],
)
def test_score_components_are_normalized(engine, field):
    result = engine.process_to_dict(make_speech_result())

    assert set(result[field].keys()) == {"score"}
    assert_valid_score(result[field]["score"])


def test_high_pause_input_increases_hesitation(engine):
    low_hesitation = make_speech_result(
        number_of_pauses=0,
        average_pause_duration=0.0,
        max_pause_duration=0.0,
        silence_duration=0.1,
        speech_duration=5.9,
    )

    high_hesitation = make_speech_result(
        number_of_pauses=6,
        average_pause_duration=1.0,
        max_pause_duration=2.0,
        silence_duration=3.0,
        speech_duration=3.0,
    )

    low_score = engine.process_to_dict(
        low_hesitation
    )["hesitation"]["score"]

    high_score = engine.process_to_dict(
        high_hesitation
    )["hesitation"]["score"]

    assert high_score > low_score


def test_high_engagement_input_produces_higher_engagement(engine):
    high_engagement = make_speech_result(
        duration=10.0,
        speech_duration=9.0,
        silence_duration=1.0,
        number_of_pauses=1,
        mean_energy=0.12,
        min_pitch=100.0,
        max_pitch=220.0,
    )

    low_engagement = make_speech_result(
        duration=10.0,
        speech_duration=2.0,
        silence_duration=8.0,
        number_of_pauses=8,
        mean_energy=0.03,
        min_pitch=100.0,
        max_pitch=120.0,
    )

    high_score = engine.process_to_dict(
        high_engagement
    )["engagement"]["score"]

    low_score = engine.process_to_dict(
        low_engagement
    )["engagement"]["score"]

    assert high_score > low_score


def test_cognitive_load_increases_with_long_pauses(engine):
    low_load = make_speech_result(
        duration=6.0,
        speech_duration=5.8,
        silence_duration=0.2,
        number_of_pauses=0,
        average_pause_duration=0.0,
        max_pause_duration=0.0,
        mean_energy=0.12,
        mean_pitch=180.0,
        min_pitch=140.0,
        max_pitch=230.0,
    )

    high_load = make_speech_result(
        duration=8.0,
        speech_duration=4.0,
        silence_duration=4.0,
        number_of_pauses=5,
        average_pause_duration=0.8,
        max_pause_duration=2.0,
        mean_energy=0.02,
        mean_pitch=150.0,
        min_pitch=148.0,
        max_pitch=152.0,
    )

    low_score = engine.process_to_dict(
        low_load
    )["cognitive_load"]["score"]

    high_score = engine.process_to_dict(
        high_load
    )["cognitive_load"]["score"]

    assert high_score > low_score


def test_empty_input_returns_safe_human_state(engine):
    result = engine.process_to_dict({})

    assert set(result.keys()) == {
        "emotion",
        "hesitation",
        "confidence",
        "engagement",
        "cognitive_load",
    }

    assert result["emotion"]["label"] == "neutral"

    for component in (
        "hesitation",
        "confidence",
        "engagement",
        "cognitive_load",
    ):
        assert_valid_score(result[component]["score"])


def test_none_input_returns_safe_human_state(engine):
    result = engine.process_to_dict(None)

    assert result["emotion"]["label"] == "neutral"

    for component in (
        "hesitation",
        "confidence",
        "engagement",
        "cognitive_load",
    ):
        assert_valid_score(result[component]["score"])


def test_missing_optional_sections_are_handled(engine):
    speech_result = {
        "transcript": "",
    }

    result = engine.process_to_dict(speech_result)

    assert result["emotion"]["label"] == "neutral"

    for component in (
        "hesitation",
        "confidence",
        "engagement",
        "cognitive_load",
    ):
        assert_valid_score(result[component]["score"])


def test_zero_duration_audio_is_safe(engine):
    speech_result = make_speech_result(
        duration=0.0,
        speech_duration=0.0,
        silence_duration=0.0,
    )

    result = engine.process_to_dict(speech_result)

    for component in (
        "hesitation",
        "confidence",
        "engagement",
        "cognitive_load",
    ):
        assert_valid_score(result[component]["score"])


def test_very_short_audio_is_safe(engine):
    speech_result = make_speech_result(
        duration=0.1,
        speech_duration=0.1,
        silence_duration=0.0,
    )

    result = engine.process_to_dict(speech_result)

    assert result["emotion"]["label"]
    assert_valid_score(result["emotion"]["score"])

    for component in (
        "hesitation",
        "confidence",
        "engagement",
        "cognitive_load",
    ):
        assert_valid_score(result[component]["score"])


def test_missing_feature_values_are_safe(engine):
    speech_result = {
        "audio": {
            "duration": 5.0,
            "speech_duration": 4.5,
            "silence_duration": 0.5,
        },
        "features": {},
    }

    result = engine.process_to_dict(speech_result)

    assert result["emotion"]["label"] == "neutral"

    for component in (
        "hesitation",
        "confidence",
        "engagement",
        "cognitive_load",
    ):
        assert_valid_score(result[component]["score"])


def test_invalid_input_type_raises_type_error(engine):
    with pytest.raises(TypeError):
        engine.process("invalid speech result")


def test_to_dict_returns_json_friendly_structure(engine):
    result = engine.process_to_dict(make_speech_result())

    assert isinstance(result, dict)
    assert isinstance(result["emotion"], dict)

    for component in (
        "hesitation",
        "confidence",
        "engagement",
        "cognitive_load",
    ):
        assert isinstance(result[component], dict)
        assert isinstance(result[component]["score"], float)


def test_process_and_process_to_dict_are_consistent(engine):
    speech_result = make_speech_result()

    human_state = engine.process(speech_result)
    dictionary_result = engine.process_to_dict(speech_result)

    assert human_state.to_dict() == dictionary_result