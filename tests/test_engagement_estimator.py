from ai.human_state.engagement.estimator import EngagementEstimator


def make_speech_result(
    speech=10.0,
    silence=2.0,
    energy=0.08,
    pauses=1,
    min_pitch=100.0,
    max_pitch=180.0,
):
    return {
        "features": {
            "mean_energy": energy,
            "number_of_pauses": pauses,
            "min_pitch": min_pitch,
            "max_pitch": max_pitch,
        },
        "audio": {
            "speech_duration": speech,
            "silence_duration": silence,
        },
    }


def test_active_speech_has_high_engagement():
    estimator = EngagementEstimator()

    result = estimator.estimate(
        make_speech_result(
            speech=12.0,
            silence=1.0,
            energy=0.10,
            pauses=1,
            min_pitch=100,
            max_pitch=200,
        )
    )

    assert result["score"] >= 0.7


def test_high_silence_reduces_engagement():
    estimator = EngagementEstimator()

    active = estimator.estimate(
        make_speech_result(
            speech=10.0,
            silence=1.0,
        )
    )

    inactive = estimator.estimate(
        make_speech_result(
            speech=5.0,
            silence=10.0,
        )
    )

    assert inactive["score"] < active["score"]


def test_frequent_pauses_reduce_engagement():
    estimator = EngagementEstimator()

    low_pauses = estimator.estimate(
        make_speech_result(
            pauses=1,
            speech=10.0,
        )
    )

    high_pauses = estimator.estimate(
        make_speech_result(
            pauses=8,
            speech=10.0,
        )
    )

    assert high_pauses["score"] < low_pauses["score"]


def test_high_energy_supports_engagement():
    estimator = EngagementEstimator()

    low_energy = estimator.estimate(
        make_speech_result(
            energy=0.02,
        )
    )

    high_energy = estimator.estimate(
        make_speech_result(
            energy=0.11,
        )
    )

    assert high_energy["score"] > low_energy["score"]


def test_pitch_variation_supports_engagement():
    estimator = EngagementEstimator()

    low_variation = estimator.estimate(
        make_speech_result(
            min_pitch=150,
            max_pitch=160,
        )
    )

    high_variation = estimator.estimate(
        make_speech_result(
            min_pitch=100,
            max_pitch=220,
        )
    )

    assert high_variation["score"] > low_variation["score"]


def test_zero_duration_returns_neutral_score():
    estimator = EngagementEstimator()

    result = estimator.estimate(
        make_speech_result(
            speech=0.0,
            silence=0.0,
            energy=0.10,
            pauses=5,
        )
    )

    assert result["score"] == 0.5


def test_invalid_features_are_safe():
    estimator = EngagementEstimator()

    result = estimator.estimate(
        {
            "features": {
                "mean_energy": "invalid",
                "number_of_pauses": None,
                "min_pitch": float("nan"),
                "max_pitch": "invalid",
            },
            "audio": {
                "speech_duration": 10.0,
                "silence_duration": "invalid",
            },
        }
    )

    assert 0.0 <= result["score"] <= 1.0


def test_negative_values_are_safe():
    estimator = EngagementEstimator()

    result = estimator.estimate(
        make_speech_result(
            speech=-10.0,
            silence=-5.0,
            energy=-0.5,
            pauses=-10,
            min_pitch=-100,
            max_pitch=-50,
        )
    )

    assert 0.0 <= result["score"] <= 1.0


def test_score_is_bounded():
    estimator = EngagementEstimator()

    result = estimator.estimate(
        make_speech_result(
            speech=1.0,
            silence=100.0,
            energy=100.0,
            pauses=1000,
            min_pitch=0,
            max_pitch=1000,
        )
    )

    assert 0.0 <= result["score"] <= 1.0