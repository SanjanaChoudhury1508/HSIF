from uuid import uuid4
from database.repository import SessionRepository

def test_postgres_session_turn_persistence_and_isolation():
    repository = SessionRepository()
    session_a = f"phase5-test-{uuid4()}"
    session_b = f"phase5-test-{uuid4()}"

    state = {
        "emotion": {"label": "neutral", "score": 0.2},
        "hesitation": {"score": 0.1},
        "confidence": {"score": 0.8},
        "engagement": {"score": 0.7},
        "cognitive_load": {"score": 0.3},
    }

    try:
        repository.add_turn(
            session_id=session_a,
            user_message="First test message",
            assistant_message="First test response",
            human_state=state,
            dialogue_strategy="continue",
        )
        repository.add_turn(
            session_id=session_a,
            user_message="Second test message",
            assistant_message="Second test response",
            human_state=state,
            dialogue_strategy="simplify",
        )
        repository.add_turn(
            session_id=session_b,
            user_message="Separate session message",
            assistant_message="Separate session response",
            human_state=state,
            dialogue_strategy="continue",
        )

        turns_a = repository.get_turns(session_a, limit=5)
        turns_b = repository.get_turns(session_b, limit=5)

        assert len(turns_a) == 2
        assert [turn.user_message for turn in turns_a] == [
            "First test message",
            "Second test message",
        ]
        assert [turn.dialogue_strategy for turn in turns_a] == [
            "continue",
            "simplify",
        ]
        assert turns_a[0].human_state == state

        assert len(turns_b) == 1
        assert turns_b[0].user_message == "Separate session message"

    finally:
        repository.clear_session(session_a)
        repository.clear_session(session_b)
