import pytest

from ai.dialogue.policy.dialogue_policy import (
    DialoguePolicy,
    PolicyDecision,
)


def make_dialogue_state(
    emotion="neutral",
    emotion_score=0.7,
    hesitation=0.3,
    confidence=0.7,
    engagement=0.7,
    cognitive_load=0.3,
    interaction_state="neutral",
    needs_clarification=False,
    needs_encouragement=False,
):
    return {
        "emotion": emotion,
        "emotion_score": emotion_score,
        "hesitation": hesitation,
        "confidence": confidence,
        "engagement": engagement,
        "cognitive_load": cognitive_load,
        "interaction_state": interaction_state,
        "needs_clarification": needs_clarification,
        "needs_encouragement": needs_encouragement,
    }


def test_policy_returns_policy_decision():
    state = make_dialogue_state()

    result = DialoguePolicy.decide(state)

    assert isinstance(result, PolicyDecision)


def test_normal_state_returns_normal_response():
    state = make_dialogue_state()

    result = DialoguePolicy.decide_to_dict(state)

    assert result["strategy"] == "normal_response"
    assert result["priority"] == "low"


def test_struggling_state_returns_clarify():
    state = make_dialogue_state(
        interaction_state="struggling",
        needs_clarification=True,
        needs_encouragement=True,
    )

    result = DialoguePolicy.decide_to_dict(state)

    assert result["strategy"] == "clarify"
    assert result["priority"] == "high"


def test_overloaded_state_returns_simplify():
    state = make_dialogue_state(
        interaction_state="overloaded",
        cognitive_load=0.85,
        needs_clarification=True,
    )

    result = DialoguePolicy.decide_to_dict(state)

    assert result["strategy"] == "simplify"
    assert result["priority"] == "high"


def test_disengaged_state_returns_reengage():
    state = make_dialogue_state(
        interaction_state="disengaged",
        engagement=0.2,
        needs_encouragement=True,
    )

    result = DialoguePolicy.decide_to_dict(state)

    assert result["strategy"] == "re_engage"
    assert result["priority"] == "medium"


def test_confident_engaged_state_returns_continue():
    state = make_dialogue_state(
        interaction_state="confident_engaged",
        confidence=0.9,
        engagement=0.9,
    )

    result = DialoguePolicy.decide_to_dict(state)

    assert result["strategy"] == "continue"
    assert result["priority"] == "low"


def test_low_confidence_returns_encourage():
    state = make_dialogue_state(
        confidence=0.3,
        needs_encouragement=True,
    )

    result = DialoguePolicy.decide_to_dict(state)

    assert result["strategy"] == "encourage"
    assert result["priority"] == "medium"


def test_clarification_flag_returns_clarify():
    state = make_dialogue_state(
        needs_clarification=True,
    )

    result = DialoguePolicy.decide_to_dict(state)

    assert result["strategy"] == "clarify"
    assert result["priority"] == "medium"


def test_encouragement_flag_returns_encourage():
    state = make_dialogue_state(
        needs_encouragement=True,
    )

    result = DialoguePolicy.decide_to_dict(state)

    assert result["strategy"] == "encourage"
    assert result["priority"] == "medium"


def test_none_input_returns_safe_response():
    result = DialoguePolicy.decide_to_dict(None)

    assert isinstance(result, dict)
    assert result["strategy"] == "normal_response"
    assert result["priority"] == "low"


def test_empty_input_returns_safe_response():
    result = DialoguePolicy.decide_to_dict({})

    assert isinstance(result, dict)
    assert result["strategy"] == "normal_response"


def test_invalid_input_type_raises_type_error():
    with pytest.raises(TypeError):
        DialoguePolicy.decide("invalid")


def test_policy_result_contains_required_fields():
    state = make_dialogue_state()

    result = DialoguePolicy.decide_to_dict(state)

    assert set(result.keys()) == {
        "strategy",
        "reason",
        "priority",
    }


def test_reason_is_provided():
    state = make_dialogue_state(
        interaction_state="struggling",
        needs_clarification=True,
    )

    result = DialoguePolicy.decide_to_dict(state)

    assert isinstance(result["reason"], str)
    assert result["reason"]


def test_confused_state_can_trigger_clarification():
    state = make_dialogue_state(
        emotion="confused",
        needs_clarification=True,
    )

    result = DialoguePolicy.decide_to_dict(state)

    assert result["strategy"] == "clarify"