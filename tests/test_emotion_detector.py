import pytest
from ai.human_state.emotion.detector import EmotionDetector

def make_speech_result(
    mean_pitch,
    min_pitch,
    max_pitch,
    mean_energy,
):
    return {
        "features": {
            "mean_pitch": mean_pitch,
            "min_pitch": min_pitch,
            "max_pitch": max_pitch,
            "mean_energy": mean_energy,
        }
    }


def test_missing_features_return_neutral():
    detector = EmotionDetector()

    result = detector.detect({"features": {}})

    assert result["label"] == "neutral"
    assert 0.0 <= result["score"] <= 1.0


def test_excited_speech():
    detector = EmotionDetector()

    result = detector.detect(
        make_speech_result(
            mean_pitch=250,
            min_pitch=120,
            max_pitch=300,
            mean_energy=0.14,
        )
    )

    assert result["label"] == "excited"
    assert result["score"] >= 0.65


def test_sad_speech():
    detector = EmotionDetector()

    result = detector.detect(
        make_speech_result(
            mean_pitch=150,
            min_pitch=130,
            max_pitch=165,
            mean_energy=0.02,
        )
    )

    assert result["label"] == "sad"
    assert result["score"] >= 0.65


def test_happy_speech():
    detector = EmotionDetector()

    result = detector.detect(
        make_speech_result(
            mean_pitch=240,
            min_pitch=190,
            max_pitch=250,
            mean_energy=0.10,
        )
    )

    assert result["label"] == "happy"
    assert result["score"] >= 0.65


def test_normal_speech_is_neutral():
    detector = EmotionDetector()

    result = detector.detect(
        make_speech_result(
            mean_pitch=170,
            min_pitch=150,
            max_pitch=190,
            mean_energy=0.06,
        )
    )

    assert result["label"] == "neutral"


def test_invalid_numeric_features_are_safe():
    detector = EmotionDetector()

    result = detector.detect(
        make_speech_result(
            mean_pitch="invalid",
            min_pitch=None,
            max_pitch=float("nan"),
            mean_energy="invalid",
        )
    )

    assert result["label"] == "neutral"
    assert 0.0 <= result["score"] <= 1.0


def test_emotion_score_is_bounded():
    detector = EmotionDetector()

    result = detector.detect(
        make_speech_result(
            mean_pitch=300,
            min_pitch=50,
            max_pitch=400,
            mean_energy=1.0,
        )
    )

    assert 0.0 <= result["score"] <= 1.0

@pytest.mark.parametrize(
    "speech_result",
    [
        {"features": None},
        {"features": []},
        {"features": "invalid"},
        None,
        [],
        "invalid",
    ],
)
def test_malformed_input_does_not_crash(speech_result):
    detector = EmotionDetector()

    try:
        result = detector.detect(speech_result)
    except (AttributeError, TypeError):
        pytest.fail("EmotionDetector.detect crashed on malformed input")

    assert result["label"] in {"neutral", "excited", "sad", "happy"}
    assert 0.0 <= result["score"] <= 1.0

def test_inconsistent_pitch_bounds_return_bounded_result():
    detector = EmotionDetector()

    result = detector.detect(
        make_speech_result(
            mean_pitch=180.0,
            min_pitch=250.0,
            max_pitch=100.0,
            mean_energy=0.10,
        )
    )

    assert result["label"] in {"neutral", "excited", "sad", "happy"}
    assert isinstance(result["score"], float)
    assert 0.0 <= result["score"] <= 1.0


def test_non_finite_features_return_bounded_result():
    detector = EmotionDetector()

    result = detector.detect(
        make_speech_result(
            mean_pitch=float("inf"),
            min_pitch=100.0,
            max_pitch=float("nan"),
            mean_energy=0.10,
        )
    )

    assert result["label"] in {"neutral", "excited", "sad", "happy"}
    assert isinstance(result["score"], float)
    assert 0.0 <= result["score"] <= 1.0