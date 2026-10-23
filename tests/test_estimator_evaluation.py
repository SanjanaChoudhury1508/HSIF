
"""Controlled behavioral checks for the baseline HSR estimators.

These tests evaluate heuristic consistency, not real-world
psychological accuracy.
"""

import math

import pytest

from ai.human_state.emotion.detector import EmotionDetector
from ai.human_state.hesitation.detector import HesitationDetector
from ai.human_state.confidence.estimator import ConfidenceEstimator
from ai.human_state.engagement.estimator import EngagementEstimator
from ai.human_state.cognitive_load.estimator import estimate_cognitive_load


ESTIMATORS = [
    ("hesitation", HesitationDetector().detect),
    ("confidence", ConfidenceEstimator().estimate),
    ("engagement", EngagementEstimator().estimate),
    ("cognitive_load", estimate_cognitive_load),
]


def speech_result(
    *,
    duration=10.0,
    speech_duration=8.0,
    silence_duration=2.0,
    pauses=2,
    average_pause=0.5,
    max_pause=1.0,
    energy=0.08,
    mean_pitch=150.0,
    min_pitch=100.0,
    max_pitch=200.0,
):
    return {
        "transcript": "this is a controlled test",
        "audio": {
            "duration": duration,
            "speech_duration": speech_duration,
            "silence_duration": silence_duration,
        },
        "features": {
            "number_of_pauses": pauses,
            "average_pause_duration": average_pause,
            "max_pause_duration": max_pause,
            "mean_energy": energy,
            "mean_pitch": mean_pitch,
            "min_pitch": min_pitch,
            "max_pitch": max_pitch,
        },
    }


@pytest.mark.parametrize(
    "name,estimator",
    ESTIMATORS,
    ids=[item[0] for item in ESTIMATORS],
)
def test_dimension_scores_are_finite_and_bounded(name, estimator):
    result = estimator(speech_result())
    score = result["score"]

    assert math.isfinite(score), name
    assert 0.0 <= score <= 1.0, name


@pytest.mark.parametrize(
    "name,estimator",
    ESTIMATORS,
    ids=[item[0] for item in ESTIMATORS],
)
def test_identical_inputs_produce_identical_scores(name, estimator):
    sample = speech_result()

    assert estimator(sample) == estimator(sample)


def test_more_pauses_increase_hesitation_score():
    estimator = HesitationDetector().detect

    fewer_pauses = estimator(speech_result(pauses=1))["score"]
    more_pauses = estimator(speech_result(pauses=4))["score"]

    assert more_pauses > fewer_pauses


def test_more_silence_reduces_engagement_score():
    estimator = EngagementEstimator().estimate

    more_speech = estimator(
        speech_result(speech_duration=9.0, silence_duration=1.0)
    )["score"]

    less_speech = estimator(
        speech_result(speech_duration=6.0, silence_duration=4.0)
    )["score"]

    assert more_speech > less_speech


def test_missing_features_do_not_crash_estimators():
    sample = {"audio": {}, "features": {}}

    for name, estimator in ESTIMATORS:
        result = estimator(sample)
        assert math.isfinite(result["score"]), name
        assert 0.0 <= result["score"] <= 1.0, name


def test_emotion_detector_returns_a_supported_label_and_bounded_score():
    result = EmotionDetector().detect(speech_result())

    assert result["label"] in {"neutral", "excited", "sad", "happy"}
    assert math.isfinite(result["score"])
    assert 0.0 <= result["score"] <= 1.0


def test_emotion_detector_handles_missing_acoustic_features():
    result = EmotionDetector().detect({"features": {}})

    assert result["label"] == "neutral"
    assert 0.0 <= result["score"] <= 1.0


def test_longer_pauses_increase_hesitation_score():
    estimator = HesitationDetector().detect

    shorter_pauses = estimator(
        speech_result(average_pause=0.2, max_pause=0.5)
    )["score"]

    longer_pauses = estimator(
        speech_result(average_pause=1.2, max_pause=2.5)
    )["score"]

    assert longer_pauses > shorter_pauses


def test_more_frequent_pauses_reduce_confidence():
    estimator = ConfidenceEstimator().estimate

    fewer_pauses = estimator(
        speech_result(pauses=1)
    )["score"]

    more_pauses = estimator(
        speech_result(pauses=4)
    )["score"]

    assert more_pauses < fewer_pauses


def test_lower_energy_reduces_engagement_score():
    estimator = EngagementEstimator().estimate

    higher_energy = estimator(
        speech_result(energy=0.10)
    )["score"]

    lower_energy = estimator(
        speech_result(energy=0.02)
    )["score"]

    assert higher_energy > lower_energy


def test_more_pauses_increase_cognitive_load_score():
    fewer_pauses = estimate_cognitive_load(
        speech_result(pauses=1)
    )["score"]

    more_pauses = estimate_cognitive_load(
        speech_result(pauses=4)
    )["score"]

    assert more_pauses > fewer_pauses


def test_lower_speech_activity_increases_cognitive_load_score():
    higher_activity = estimate_cognitive_load(
        speech_result(speech_duration=9.0, silence_duration=1.0)
    )["score"]

    lower_activity = estimate_cognitive_load(
        speech_result(speech_duration=6.0, silence_duration=4.0)
    )["score"]

    assert lower_activity > higher_activity


def test_emotion_detector_is_deterministic_for_distinct_acoustic_profiles():
    detector = EmotionDetector()

    profiles = [
        speech_result(energy=0.02, mean_pitch=120.0,
                      min_pitch=110.0, max_pitch=125.0),
        speech_result(energy=0.14, mean_pitch=220.0,
                      min_pitch=100.0, max_pitch=260.0),
    ]

    for sample in profiles:
        first = detector.detect(sample)
        second = detector.detect(sample)

        assert first == second
        assert first["label"] in {"neutral", "excited", "sad", "happy"}
        assert 0.0 <= first["score"] <= 1.0


def test_emotion_detector_does_not_infer_neutral_from_missing_features():
    result = EmotionDetector().detect({"features": {}})

    assert result["label"] == "neutral"
    assert result["score"] == 0.5


@pytest.mark.parametrize(
    "name,estimator",
    ESTIMATORS,
    ids=[item[0] for item in ESTIMATORS],
)
def test_estimators_handle_partial_observations(name, estimator):
    sample = {
        "audio": {
            "duration": 10.0,
            "speech_duration": 8.0,
            "silence_duration": 2.0,
        },
        "features": {},
        "vad": {},
    }

    result = estimator(sample)

    assert math.isfinite(result["score"])
    assert 0.0 <= result["score"] <= 1.0


def test_empty_observation_is_not_marked_valid_by_engine():
    engine = __import__(
        "ai.human_state.human_state_engine",
        fromlist=["HumanStateEngine"],
    ).HumanStateEngine()

    state = engine.process(
        {"audio": {}, "features": {}, "vad": {}},
        observation_valid=False,
    )

    assert state.observation_valid is False