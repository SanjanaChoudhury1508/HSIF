from ai.human_state.cognitive_load.estimator import (
    estimate_cognitive_load,
)


def make_speech_result(
    duration=10.0,
    speech=9.0,
    pauses=1,
    average_pause=0.2,
    max_pause=0.4,
    energy=0.10,
    mean_pitch=180.0,
    min_pitch=120.0,
    max_pitch=230.0,
):
    return {
        "audio": {
            "duration": duration,
            "speech_duration": speech,
            "silence_duration": duration - speech,
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


def test_low_load_speech():
    result = estimate_cognitive_load(
        make_speech_result(
            duration=10,
            speech=9.5,
            pauses=0,
            average_pause=0.0,
            max_pause=0.0,
            energy=0.12,
            mean_pitch=180,
            min_pitch=130,
            max_pitch=220,
        )
    )

    assert result["score"] < 0.4


def test_frequent_pauses_increase_load():
    low = estimate_cognitive_load(
        make_speech_result(
            pauses=1,
            speech=9.0,
        )
    )

    high = estimate_cognitive_load(
        make_speech_result(
            pauses=8,
            speech=9.0,
        )
    )

    assert high["score"] > low["score"]


def test_long_pauses_increase_load():
    short = estimate_cognitive_load(
        make_speech_result(
            pauses=2,
            average_pause=0.2,
            max_pause=0.3,
        )
    )

    long = estimate_cognitive_load(
        make_speech_result(
            pauses=2,
            average_pause=1.0,
            max_pause=3.0,
        )
    )

    assert long["score"] > short["score"]


def test_low_speech_activity_increases_load():
    active = estimate_cognitive_load(
        make_speech_result(
            speech=9.5,
        )
    )

    inactive = estimate_cognitive_load(
        make_speech_result(
            speech=4.0,
        )
    )

    assert inactive["score"] > active["score"]


def test_low_energy_increases_load():
    high_energy = estimate_cognitive_load(
        make_speech_result(
            energy=0.12,
        )
    )

    low_energy = estimate_cognitive_load(
        make_speech_result(
            energy=0.02,
        )
    )

    assert low_energy["score"] > high_energy["score"]


def test_flat_pitch_increases_load():
    natural = estimate_cognitive_load(
        make_speech_result(
            mean_pitch=180,
            min_pitch=130,
            max_pitch=230,
        )
    )

    flat = estimate_cognitive_load(
        make_speech_result(
            mean_pitch=180,
            min_pitch=175,
            max_pitch=185,
        )
    )

    assert flat["score"] > natural["score"]


def test_zero_duration_returns_neutral():
    result = estimate_cognitive_load(
        make_speech_result(
            duration=0.0,
            speech=0.0,
        )
    )

    assert result["score"] == 0.5


def test_invalid_features_are_safe():
    result = estimate_cognitive_load(
        {
            "audio": {
                "duration": 10.0,
                "speech_duration": "invalid",
            },
            "features": {
                "number_of_pauses": None,
                "average_pause_duration": "invalid",
                "max_pause_duration": float("nan"),
                "mean_energy": "invalid",
                "mean_pitch": None,
                "min_pitch": "invalid",
                "max_pitch": float("nan"),
            },
        }
    )

    assert 0.0 <= result["score"] <= 1.0


def test_negative_values_are_safe():
    result = estimate_cognitive_load(
        make_speech_result(
            duration=10,
            speech=-5,
            pauses=-10,
            average_pause=-2,
            max_pause=-4,
            energy=-0.5,
            mean_pitch=-100,
            min_pitch=-200,
            max_pitch=-50,
        )
    )

    assert 0.0 <= result["score"] <= 1.0


def test_score_is_bounded():
    result = estimate_cognitive_load(
        make_speech_result(
            duration=1,
            speech=1,
            pauses=1000,
            average_pause=100,
            max_pause=100,
            energy=100,
            mean_pitch=1,
            min_pitch=0,
            max_pitch=1000,
        )
    )

    assert 0.0 <= result["score"] <= 1.0