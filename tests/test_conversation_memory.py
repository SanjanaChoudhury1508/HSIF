import pytest

from ai.dialogue.memory.conversation_memory import (
    ConversationMemory,
    ConversationTurn,
)


def test_memory_starts_empty():
    memory = ConversationMemory()

    assert len(memory) == 0
    assert memory.get_history() == []


def test_add_turn_stores_conversation():
    memory = ConversationMemory()

    memory.add_turn(
        "Hello",
        "Hi! How can I help?",
    )

    history = memory.get_history()

    assert len(history) == 1
    assert history[0]["user_message"] == "Hello"
    assert history[0]["assistant_message"] == "Hi! How can I help?"


def test_multiple_turns_are_stored():
    memory = ConversationMemory()

    memory.add_turn("Hello", "Hi!")
    memory.add_turn("How are you?", "I'm doing well.")

    assert len(memory) == 2


def test_memory_respects_max_turns():
    memory = ConversationMemory(max_turns=2)

    memory.add_turn("Message 1", "Response 1")
    memory.add_turn("Message 2", "Response 2")
    memory.add_turn("Message 3", "Response 3")

    history = memory.get_history()

    assert len(history) == 2
    assert history[0]["user_message"] == "Message 2"
    assert history[1]["user_message"] == "Message 3"


def test_get_recent_returns_latest_turns():
    memory = ConversationMemory()

    memory.add_turn("Message 1", "Response 1")
    memory.add_turn("Message 2", "Response 2")
    memory.add_turn("Message 3", "Response 3")

    recent = memory.get_recent(2)

    assert len(recent) == 2
    assert recent[0]["user_message"] == "Message 2"
    assert recent[1]["user_message"] == "Message 3"


def test_clear_removes_history():
    memory = ConversationMemory()

    memory.add_turn("Hello", "Hi!")

    memory.clear()

    assert len(memory) == 0
    assert memory.get_history() == []


def test_empty_messages_are_allowed():
    memory = ConversationMemory()

    memory.add_turn("", "")

    history = memory.get_history()

    assert history[0]["user_message"] == ""
    assert history[0]["assistant_message"] == ""


def test_invalid_user_message_raises_type_error():
    memory = ConversationMemory()

    with pytest.raises(TypeError):
        memory.add_turn(123, "Response")


def test_invalid_assistant_message_raises_type_error():
    memory = ConversationMemory()

    with pytest.raises(TypeError):
        memory.add_turn("Message", 123)


def test_invalid_max_turns_raises_error():
    with pytest.raises(ValueError):
        ConversationMemory(max_turns=0)


def test_conversation_turn_to_dict():
    turn = ConversationTurn(
        user_message="Hello",
        assistant_message="Hi!",
    )

    result = turn.to_dict()

    assert result == {
        "user_message": "Hello",
        "assistant_message": "Hi!",
    }