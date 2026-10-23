
import pytest

from ai.human_state.hsr import build_human_state
from ai.human_state.temporal_smoother import TemporalSmoother


def make_state(
    *,
    emotion="neutral",
    hesitation=0.2,
    confidence=0.8,
    engagement=0.7,
    cognitive_load=0.3,
    timestamp=None,
    observation_valid=True,
):
    return build_human_state(
        emotion_label=emotion,
        emotion_score=0.8,
        hesitation_score=hesitation,
        confidence_score=confidence,
        engagement_score=engagement,
        cognitive_load_score=cognitive_load,
        timestamp=timestamp,
        observation_valid=observation_valid,
    )


def test_first_observation_passes_through():
    smoother = TemporalSmoother()
    state = make_state()

    assert smoother.smooth(state) is state


def test_numeric_scores_are_smoothed():
    smoother = TemporalSmoother(alpha=0.4)

    smoother.smooth(make_state(engagement=0.2))
    result = smoother.smooth(make_state(engagement=0.8))

    assert result.engagement.score == pytest.approx(0.44)


def test_scores_remain_bounded():
    smoother = TemporalSmoother()

    smoother.smooth(make_state())
    result = smoother.smooth(make_state(engagement=1.0))

    for name in (
        "hesitation",
        "confidence",
        "engagement",
        "cognitive_load",
    ):
        assert 0.0 <= getattr(result, name).score <= 1.0


def test_emotion_change_requires_confirmation():
    smoother = TemporalSmoother(emotion_confirmation_count=2)

    first = smoother.smooth(make_state(emotion="neutral"))
    second = smoother.smooth(make_state(emotion="happy"))
    third = smoother.smooth(make_state(emotion="happy"))

    assert first.emotion.label == "neutral"
    assert second.emotion.label == "neutral"
    assert third.emotion.label == "happy"


def test_invalid_observation_does_not_update_baseline():
    smoother = TemporalSmoother(alpha=0.5)

    smoother.smooth(make_state(engagement=0.2))
    invalid = make_state(engagement=1.0, observation_valid=False)

    assert smoother.smooth(invalid) is invalid

    result = smoother.smooth(make_state(engagement=0.6))

    # Baseline remains 0.2: 0.5 * 0.6 + 0.5 * 0.2.
    assert result.engagement.score == pytest.approx(0.4)


def test_reset_clears_temporal_context():
    smoother = TemporalSmoother()

    smoother.smooth(make_state(engagement=0.2))
    smoother.reset()

    new_state = make_state(engagement=0.9)

    assert smoother.smooth(new_state) is new_state


def test_decreasing_timestamps_are_rejected():
    smoother = TemporalSmoother()

    smoother.smooth(make_state(timestamp=10.0))

    with pytest.raises(ValueError, match="non-decreasing"):
        smoother.smooth(make_state(timestamp=9.0))


def test_invalid_alpha_is_rejected():
    with pytest.raises(ValueError):
        TemporalSmoother(alpha=0.0)

    with pytest.raises(ValueError):
        TemporalSmoother(alpha=1.1)


def test_invalid_observation_does_not_change_smoother_baseline():
    from ai.human_state.hsr import build_human_state
    from ai.human_state.temporal_smoother import TemporalSmoother

    smoother = TemporalSmoother(alpha=0.4)

    baseline = build_human_state(
        emotion_label="neutral",
        emotion_score=0.8,
        hesitation_score=0.2,
        confidence_score=0.8,
        engagement_score=0.7,
        cognitive_load_score=0.3,
        timestamp=10.0,
        observation_valid=True,
    )
    smoother.smooth(baseline)

    candidate_before = (
        smoother._candidate_emotion,
        smoother._candidate_count,
    )
    previous_before = smoother._previous

    invalid = build_human_state(
        emotion_label="sad",
        emotion_score=0.9,
        hesitation_score=0.9,
        confidence_score=0.1,
        engagement_score=0.1,
        cognitive_load_score=0.9,
        timestamp=11.0,
        observation_valid=False,
    )

    returned = smoother.smooth(invalid)

    assert returned is invalid
    assert smoother._previous is previous_before
    assert (
        smoother._candidate_emotion,
        smoother._candidate_count,
    ) == candidate_before


def test_invalid_observation_does_not_interrupt_emotion_confirmation():
    from ai.human_state.hsr import build_human_state
    from ai.human_state.temporal_smoother import TemporalSmoother

    smoother = TemporalSmoother(
        alpha=0.4,
        emotion_confirmation_count=2,
    )

    def make_state(label, timestamp, valid=True):
        return build_human_state(
            emotion_label=label,
            emotion_score=0.8,
            hesitation_score=0.5,
            confidence_score=0.5,
            engagement_score=0.5,
            cognitive_load_score=0.5,
            timestamp=timestamp,
            observation_valid=valid,
        )

    smoother.smooth(make_state("neutral", 1.0))
    first_candidate = smoother.smooth(make_state("sad", 2.0))

    assert first_candidate.emotion.label == "neutral"
    assert smoother._candidate_emotion == "sad"
    assert smoother._candidate_count == 1

    smoother.smooth(make_state("excited", 3.0, valid=False))

    assert smoother._candidate_emotion == "sad"
    assert smoother._candidate_count == 1

    confirmed = smoother.smooth(make_state("sad", 4.0))

    assert confirmed.emotion.label == "sad"
    assert smoother._candidate_emotion is None
    assert smoother._candidate_count == 0