import pytest

from ai.dialogue.fusion.state_fusion import (
    DialogueState,
    StateFusion,
)


def make_human_state(
    emotion="neutral",
    emotion_score=0.7,
    hesitation=0.3,
    confidence=0.7,
    engagement=0.7,
    cognitive_load=0.3,
):
    return {
        "emotion": {
            "label": emotion,
            "score": emotion_score,
        },
        "hesitation": {
            "score": hesitation,
        },
        "confidence": {
            "score": confidence,
        },
        "engagement": {
            "score": engagement,
        },
        "cognitive_load": {
            "score": cognitive_load,
        },
    }


def test_fusion_returns_dialogue_state():
    human_state = make_human_state()

    result = StateFusion.fuse(human_state)

    assert isinstance(result, DialogueState)


def test_normal_state_is_neutral():
    human_state = make_human_state()

    result = StateFusion.fuse_to_dict(human_state)

    assert result["interaction_state"] == "neutral"
    assert result["needs_clarification"] is False


def test_struggling_state_needs_clarification():
    human_state = make_human_state(
        emotion="confused",
        hesitation=0.8,
        confidence=0.3,
        engagement=0.8,
        cognitive_load=0.5,
    )

    result = StateFusion.fuse_to_dict(human_state)

    assert result["interaction_state"] == "struggling"
    assert result["needs_clarification"] is True
    assert result["needs_encouragement"] is True


def test_high_cognitive_load_is_overloaded():
    human_state = make_human_state(
        hesitation=0.4,
        confidence=0.6,
        engagement=0.7,
        cognitive_load=0.8,
    )

    result = StateFusion.fuse_to_dict(human_state)

    assert result["interaction_state"] == "overloaded"
    assert result["needs_clarification"] is True


def test_low_engagement_is_disengaged():
    human_state = make_human_state(
        hesitation=0.2,
        confidence=0.6,
        engagement=0.2,
        cognitive_load=0.3,
    )

    result = StateFusion.fuse_to_dict(human_state)

    assert result["interaction_state"] == "disengaged"
    assert result["needs_encouragement"] is True


def test_confident_engaged_state():
    human_state = make_human_state(
        hesitation=0.1,
        confidence=0.9,
        engagement=0.9,
        cognitive_load=0.2,
    )

    result = StateFusion.fuse_to_dict(human_state)

    assert result["interaction_state"] == "confident_engaged"
    assert result["needs_clarification"] is False
    assert result["needs_encouragement"] is False


def test_none_input_is_safe():
    result = StateFusion.fuse_to_dict(None)

    assert isinstance(result, dict)
    assert result["emotion"] == "neutral"


def test_empty_input_is_safe():
    result = StateFusion.fuse_to_dict({})

    assert result["emotion"] == "neutral"
    assert 0.0 <= result["confidence"] <= 1.0


def test_invalid_input_type_raises_type_error():
    with pytest.raises(TypeError):
        StateFusion.fuse("invalid")


def test_invalid_scores_are_safe():
    human_state = make_human_state(
        hesitation="invalid",
        confidence=None,
        engagement=float("nan"),
        cognitive_load=2.0,
    )

    result = StateFusion.fuse_to_dict(human_state)

    assert 0.0 <= result["hesitation"] <= 1.0
    assert 0.0 <= result["confidence"] <= 1.0
    assert 0.0 <= result["engagement"] <= 1.0
    assert 0.0 <= result["cognitive_load"] <= 1.0