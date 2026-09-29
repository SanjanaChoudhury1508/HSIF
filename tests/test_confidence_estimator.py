from ai.human_state.confidence.estimator import ConfidenceEstimator


def make_speech_result(
    pauses=0,
    average_pause=0.0,
    min_pitch=100.0,
    max_pitch=180.0,
    energy=0.08,
    speech=10.0,
):
    return {
        "features": {
            "number_of_pauses": pauses,
            "average_pause_duration": average_pause,
            "min_pitch": min_pitch,
            "max_pitch": max_pitch,
            "mean_energy": energy,
        },
        "audio": {
            "speech_duration": speech,
        },
    }


def test_confident_speech_has_high_score():
    estimator = ConfidenceEstimator()

    result = estimator.estimate(
        make_speech_result(
            pauses=1,
            average_pause=0.2,
            min_pitch=100,
            max_pitch=180,
            energy=0.10,
            speech=10,
        )
    )

    assert result["score"] >= 0.7


def test_frequent_pauses_reduce_confidence():
    estimator = ConfidenceEstimator()

    low_pause = estimator.estimate(
        make_speech_result(
            pauses=1,
            average_pause=0.2,
            energy=0.08,
        )
    )

    high_pause = estimator.estimate(
        make_speech_result(
            pauses=8,
            average_pause=0.2,
            energy=0.08,
        )
    )

    assert high_pause["score"] < low_pause["score"]


def test_long_pauses_reduce_confidence():
    estimator = ConfidenceEstimator()

    short_pause = estimator.estimate(
        make_speech_result(
            pauses=2,
            average_pause=0.2,
            energy=0.08,
        )
    )

    long_pause = estimator.estimate(
        make_speech_result(
            pauses=2,
            average_pause=1.5,
            energy=0.08,
        )
    )

    assert long_pause["score"] < short_pause["score"]


def test_reasonable_pitch_variation_supports_confidence():
    estimator = ConfidenceEstimator()

    result = estimator.estimate(
        make_speech_result(
            min_pitch=100,
            max_pitch=180,
            energy=0.08,
        )
    )

    assert result["score"] >= 0.7


def test_low_energy_reduces_confidence():
    estimator = ConfidenceEstimator()

    high_energy = estimator.estimate(
        make_speech_result(
            energy=0.11,
        )
    )

    low_energy = estimator.estimate(
        make_speech_result(
            energy=0.02,
        )
    )

    assert low_energy["score"] < high_energy["score"]


def test_zero_speech_duration_returns_neutral_score():
    estimator = ConfidenceEstimator()

    result = estimator.estimate(
        make_speech_result(
            pauses=5,
            average_pause=1.0,
            energy=0.10,
            speech=0.0,
        )
    )

    assert result["score"] == 0.5


def test_invalid_features_are_safe():
    estimator = ConfidenceEstimator()

    result = estimator.estimate(
        {
            "features": {
                "number_of_pauses": "invalid",
                "average_pause_duration": None,
                "min_pitch": float("nan"),
                "max_pitch": "invalid",
                "mean_energy": None,
            },
            "audio": {
                "speech_duration": 10.0,
            },
        }
    )

    assert 0.0 <= result["score"] <= 1.0


def test_negative_values_are_safe():
    estimator = ConfidenceEstimator()

    result = estimator.estimate(
        make_speech_result(
            pauses=-5,
            average_pause=-2.0,
            min_pitch=-100,
            max_pitch=-50,
            energy=-0.5,
            speech=10,
        )
    )

    assert 0.0 <= result["score"] <= 1.0


def test_score_is_bounded():
    estimator = ConfidenceEstimator()

    result = estimator.estimate(
        make_speech_result(
            pauses=1000,
            average_pause=100,
            min_pitch=0,
            max_pitch=1000,
            energy=100,
            speech=1,
        )
    )

    assert 0.0 <= result["score"] <= 1.0