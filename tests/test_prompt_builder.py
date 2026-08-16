import pytest

from ai.dialogue.prompts.prompt_builder import PromptBuilder


def make_state():
    return {
        "emotion": "confused",
        "interaction_state": "struggling",
        "confidence": 0.3,
        "hesitation": 0.8,
        "engagement": 0.8,
        "cognitive_load": 0.5,
    }


def make_policy():
    return {
        "strategy": "clarify",
        "reason": "The user appears to be struggling.",
        "priority": "high",
    }


def make_history():
    return [
        {
            "user_message": "What is machine learning?",
            "assistant_message": "It is a way for computers to learn patterns.",
        }
    ]


def test_build_returns_string():
    result = PromptBuilder.build(
        "I don't understand.",
        make_state(),
        make_policy(),
    )

    assert isinstance(result, str)
    assert result


def test_prompt_contains_user_message():
    result = PromptBuilder.build(
        "Please explain this again.",
        make_state(),
        make_policy(),
    )

    assert "Please explain this again." in result


def test_prompt_contains_human_state():
    result = PromptBuilder.build(
        "I am confused.",
        make_state(),
        make_policy(),
    )

    assert "confused" in result
    assert "struggling" in result
    assert "0.3" in result
    assert "0.8" in result


def test_prompt_contains_policy():
    result = PromptBuilder.build(
        "Explain again.",
        make_state(),
        make_policy(),
    )

    assert "clarify" in result
    assert "high" in result
    assert "The user appears to be struggling." in result


def test_prompt_contains_conversation_history():
    result = PromptBuilder.build(
        "I still don't understand.",
        make_state(),
        make_policy(),
        make_history(),
    )

    assert "What is machine learning?" in result
    assert "It is a way for computers to learn patterns." in result


def test_prompt_handles_empty_history():
    result = PromptBuilder.build(
        "Hello",
        make_state(),
        make_policy(),
        [],
    )

    assert "No previous conversation." in result


def test_prompt_handles_none_state():
    result = PromptBuilder.build(
        "Hello",
        None,
        None,
    )

    assert "neutral" in result
    assert "normal_response" in result


def test_prompt_rejects_invalid_user_message():
    with pytest.raises(TypeError):
        PromptBuilder.build(
            123,
            make_state(),
            make_policy(),
        )


def test_prompt_rejects_invalid_dialogue_state():
    with pytest.raises(TypeError):
        PromptBuilder.build(
            "Hello",
            "invalid",
            make_policy(),
        )


def test_prompt_rejects_invalid_policy():
    with pytest.raises(TypeError):
        PromptBuilder.build(
            "Hello",
            make_state(),
            "invalid",
        )


def test_prompt_rejects_invalid_history():
    with pytest.raises(TypeError):
        PromptBuilder.build(
            "Hello",
            make_state(),
            make_policy(),
            "invalid",
        )


def test_prompt_limits_history_to_recent_five_turns():
    history = []

    for i in range(7):
        history.append(
            {
                "user_message": f"User message {i}",
                "assistant_message": f"Assistant response {i}",
            }
        )

    result = PromptBuilder.build(
        "Current message",
        make_state(),
        make_policy(),
        history,
    )

    assert "User message 0" not in result
    assert "User message 1" not in result
    assert "User message 2" in result
    assert "User message 6" in result