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

def test_high_hesitation_low_confidence_returns_reassure():
    state = make_dialogue_state(
        hesitation=0.8,
        confidence=0.3,
    )

    result = DialoguePolicy.decide_to_dict(state)

    assert result["strategy"] == "reassure"
    assert result["priority"] == "high"


def test_high_hesitation_returns_slow_down():
    state = make_dialogue_state(
        hesitation=0.8,
        confidence=0.7,
    )

    result = DialoguePolicy.decide_to_dict(state)

    assert result["strategy"] == "slow_down"
    assert result["priority"] == "medium"


def test_high_cognitive_load_returns_reduce_information():
    state = make_dialogue_state(
        cognitive_load=0.95,
        confidence=0.7,
        interaction_state="overloaded",
    )

    result = DialoguePolicy.decide_to_dict(state)

    assert result["strategy"] == "reduce_information"
    assert result["priority"] == "high"


def test_frustrated_emotion_returns_acknowledge_frustration():
    state = make_dialogue_state(
        emotion="frustrated",
        emotion_score=0.85,
    )

    result = DialoguePolicy.decide_to_dict(state)

    assert result["strategy"] == "acknowledge_frustration"
    assert result["priority"] == "high"


def test_low_engagement_returns_reengage():
    state = make_dialogue_state(
        engagement=0.2,
        interaction_state="disengaged",
    )

    result = DialoguePolicy.decide_to_dict(state)

    assert result["strategy"] == "re_engage"
    assert result["priority"] == "medium"


def test_ambiguous_state_returns_ask_follow_up():
    state = make_dialogue_state(
        emotion="uncertain",
        needs_clarification=True,
    )

    result = DialoguePolicy.decide_to_dict(state)

    assert result["strategy"] == "ask_follow_up"
    assert result["priority"] == "medium"