import pytest

from ai.dialogue.dialogue_service import DialogueService


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


def test_service_returns_dialogue_result():
    service = DialogueService()

    result = service.process(
        user_message="I don't understand this.",
        human_state=make_human_state(
            emotion="confused",
            hesitation=0.8,
            confidence=0.3,
            engagement=0.8,
            cognitive_load=0.5,
        ),
    )

    assert isinstance(result, dict)


def test_service_contains_required_fields():
    service = DialogueService()

    result = service.process(
        user_message="Explain this again.",
        human_state=make_human_state(),
    )

    assert {
        "dialogue_state",
        "policy",
        "prompt",
        "history",
    }.issubset(result.keys())


def test_struggling_user_gets_clarification_policy():
    service = DialogueService()

    result = service.process(
        user_message="I still don't understand.",
        human_state=make_human_state(
            emotion="confused",
            hesitation=0.8,
            confidence=0.3,
            engagement=0.8,
            cognitive_load=0.5,
        ),
    )

    assert result["policy"]["strategy"] == "clarify"
    assert result["policy"]["priority"] == "high"


def test_overloaded_user_gets_simplification_policy():
    service = DialogueService()

    result = service.process(
        user_message="This is too complicated.",
        human_state=make_human_state(
            hesitation=0.5,
            confidence=0.5,
            engagement=0.7,
            cognitive_load=0.9,
        ),
    )

    assert result["policy"]["strategy"] == "simplify"


def test_disengaged_user_gets_reengagement_policy():
    service = DialogueService()

    result = service.process(
        user_message="Okay...",
        human_state=make_human_state(
            hesitation=0.2,
            confidence=0.6,
            engagement=0.2,
            cognitive_load=0.3,
        ),
    )

    assert result["policy"]["strategy"] == "re_engage"


def test_confident_user_gets_continue_policy():
    service = DialogueService()

    result = service.process(
        user_message="I understand. Let's continue.",
        human_state=make_human_state(
            hesitation=0.1,
            confidence=0.9,
            engagement=0.9,
            cognitive_load=0.2,
        ),
    )

    assert result["policy"]["strategy"] == "continue"


def test_prompt_contains_user_message():
    service = DialogueService()

    result = service.process(
        user_message="Can you explain recursion?",
        human_state=make_human_state(),
    )

    assert "Can you explain recursion?" in result["prompt"]


def test_prompt_contains_dialogue_policy():
    service = DialogueService()

    result = service.process(
        user_message="I am confused.",
        human_state=make_human_state(
            emotion="confused",
            hesitation=0.8,
            confidence=0.3,
            engagement=0.8,
            cognitive_load=0.5,
        ),
    )

    assert "clarify" in result["prompt"]
    assert "high" in result["prompt"]


def test_conversation_history_is_used():
    service = DialogueService()

    service.add_response(
        user_message="What is machine learning?",
        assistant_message="It is a way for computers to learn patterns.",
    )

    result = service.process(
        user_message="Can you explain it simply?",
        human_state=make_human_state(),
    )

    assert "What is machine learning?" in result["prompt"]
    assert "It is a way for computers to learn patterns." in result["prompt"]

def test_none_human_state_is_safe():
    service = DialogueService()

    result = service.process(
        user_message="Hello",
        human_state=None,
    )

    assert isinstance(result, dict)
    assert "dialogue_state" in result
    assert "policy" in result
    assert "prompt" in result


def test_empty_human_state_is_safe():
    service = DialogueService()

    result = service.process(
        user_message="Hello",
        human_state={},
    )

    assert isinstance(result, dict)
    assert "prompt" in result


def test_invalid_user_message_raises_type_error():
    service = DialogueService()

    with pytest.raises(TypeError):
        service.process(
            user_message=123,
            human_state=make_human_state(),
        )