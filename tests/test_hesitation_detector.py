from ai.human_state.hesitation.detector import HesitationDetector


def make_speech_result(
    pauses=0,
    average_pause=0.0,
    max_pause=0.0,
    silence=0.0,
    speech=10.0,
):
    return {
        "features": {
            "number_of_pauses": pauses,
            "average_pause_duration": average_pause,
            "max_pause_duration": max_pause,
        },
        "audio": {
            "silence_duration": silence,
            "speech_duration": speech,
        },
    }


def test_low_hesitation():
    detector = HesitationDetector()

    result = detector.detect(
        make_speech_result(
            pauses=1,
            average_pause=0.1,
            max_pause=0.2,
            silence=0.5,
            speech=10.0,
        )
    )

    assert result["score"] < 0.3


def test_frequent_pauses_increase_hesitation():
    detector = HesitationDetector()

    low = detector.detect(
        make_speech_result(
            pauses=1,
            average_pause=0.2,
            max_pause=0.5,
            silence=1.0,
            speech=10.0,
        )
    )

    high = detector.detect(
        make_speech_result(
            pauses=8,
            average_pause=0.8,
            max_pause=2.0,
            silence=2.0,
            speech=10.0,
        )
    )

    assert high["score"] > low["score"]


def test_long_pauses_increase_hesitation():
    detector = HesitationDetector()

    short = detector.detect(
        make_speech_result(
            pauses=2,
            average_pause=0.2,
            max_pause=0.5,
            silence=1.0,
            speech=10.0,
        )
    )

    long = detector.detect(
        make_speech_result(
            pauses=2,
            average_pause=1.0,
            max_pause=4.0,
            silence=1.0,
            speech=10.0,
        )
    )

    assert long["score"] > short["score"]


def test_high_silence_ratio_increases_hesitation():
    detector = HesitationDetector()

    low_silence = detector.detect(
        make_speech_result(
            pauses=2,
            average_pause=0.3,
            max_pause=0.5,
            silence=1.0,
            speech=10.0,
        )
    )

    high_silence = detector.detect(
        make_speech_result(
            pauses=2,
            average_pause=0.3,
            max_pause=0.5,
            silence=10.0,
            speech=10.0,
        )
    )

    assert high_silence["score"] > low_silence["score"]


def test_zero_duration_returns_neutral_score():
    detector = HesitationDetector()

    result = detector.detect(
        make_speech_result(
            pauses=5,
            average_pause=1.0,
            max_pause=3.0,
            silence=0.0,
            speech=0.0,
        )
    )

    assert result["score"] == 0.5


def test_invalid_features_are_safe():
    detector = HesitationDetector()

    result = detector.detect(
        {
            "features": {
                "number_of_pauses": "invalid",
                "average_pause_duration": None,
                "max_pause_duration": float("nan"),
            },
            "audio": {
                "silence_duration": "invalid",
                "speech_duration": 10.0,
            },
        }
    )

    assert 0.0 <= result["score"] <= 1.0


def test_negative_values_are_safe():
    detector = HesitationDetector()

    result = detector.detect(
        make_speech_result(
            pauses=-10,
            average_pause=-2.0,
            max_pause=-4.0,
            silence=-5.0,
            speech=10.0,
        )
    )

    assert 0.0 <= result["score"] <= 1.0


def test_score_is_bounded():
    detector = HesitationDetector()

    result = detector.detect(
        make_speech_result(
            pauses=100,
            average_pause=100,
            max_pause=100,
            silence=100,
            speech=1,
        )
    )

    assert 0.0 <= result["score"] <= 1.0