from datetime import datetime, timezone

from sqlalchemy import select

from database.database import SessionLocal
from database.models import ConversationTurn, Session


class SessionRepository:
    """Handles persistent HSIF conversation sessions and turns."""

    def __init__(self, db_session_factory=SessionLocal):
        self.db_session_factory = db_session_factory

    def get_or_create_session(self, session_id: str) -> Session:
        with self.db_session_factory() as db:
            session = db.get(Session, session_id)

            if session is None:
                session = Session(
                    id=session_id,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                db.add(session)
                db.commit()
                db.refresh(session)

            return session

    def add_turn(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
        human_state: dict,
        dialogue_strategy: str,
    ) -> ConversationTurn:
        with self.db_session_factory() as db:
            session = db.get(Session, session_id)

            if session is None:
                session = Session(
                    id=session_id,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                db.add(session)
                db.flush()

            turn = ConversationTurn(
                session_id=session_id,
                user_message=user_message,
                assistant_message=assistant_message,
                human_state=human_state,
                dialogue_strategy=dialogue_strategy,
                created_at=datetime.now(timezone.utc),
            )

            session.updated_at = datetime.now(timezone.utc)

            db.add(turn)
            db.commit()
            db.refresh(turn)

            return turn

    def get_turns(
        self,
        session_id: str,
        limit: int = 5,
    ) -> list[ConversationTurn]:
        with self.db_session_factory() as db:
            statement = (
                select(ConversationTurn)
                .where(ConversationTurn.session_id == session_id)
                .order_by(ConversationTurn.created_at.desc())
                .limit(limit)
            )

            turns = list(db.scalars(statement).all())

            # Return chronological order for conversation history.
            turns.reverse()

            return turns

    def clear_session(self, session_id: str) -> bool:
        with self.db_session_factory() as db:
            session = db.get(Session, session_id)

            if session is None:
                return False

            db.delete(session)
            db.commit()

            return True