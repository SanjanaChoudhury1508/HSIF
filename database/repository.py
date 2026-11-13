
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

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
                .order_by(
                    ConversationTurn.created_at.desc(),
                    ConversationTurn.id.desc(),
                )
                .limit(limit)
            )

            turns = list(db.scalars(statement).all())
            turns.reverse()

            return turns

    def list_sessions(self) -> list[dict]:
        """Return all saved sessions, newest first."""

        with self.db_session_factory() as db:
            statement = (
                select(Session)
                .options(selectinload(Session.turns))
                .order_by(Session.updated_at.desc())
            )

            sessions = db.scalars(statement).all()

            results = []

            for session in sessions:
                turns = sorted(
                    session.turns,
                    key=lambda turn: (turn.created_at, turn.id),
                )

                latest_turn = turns[-1] if turns else None

                results.append({
                    "session_id": session.id,
                    "created_at": session.created_at,
                    "updated_at": session.updated_at,
                    "turn_count": len(turns),
                    "preview": (
                        latest_turn.user_message
                        if latest_turn
                        else ""
                    ),
                })

            return results

    def get_session_history(self, session_id: str) -> dict | None:
        """Return one session and all its conversation turns."""

        with self.db_session_factory() as db:
            session = db.get(Session, session_id)

            if session is None:
                return None

            statement = (
                select(ConversationTurn)
                .where(ConversationTurn.session_id == session_id)
                .order_by(
                    ConversationTurn.created_at.asc(),
                    ConversationTurn.id.asc(),
                )
            )

            turns = db.scalars(statement).all()

            return {
                "session_id": session.id,
                "created_at": session.created_at,
                "updated_at": session.updated_at,
                "turns": [
                    {
                        "id": turn.id,
                        "user_message": turn.user_message,
                        "assistant_message": turn.assistant_message,
                        "human_state": turn.human_state,
                        "dialogue_strategy": turn.dialogue_strategy,
                        "created_at": turn.created_at,
                    }
                    for turn in turns
                ],
            }

    def clear_session(self, session_id: str) -> bool:
        with self.db_session_factory() as db:
            session = db.get(Session, session_id)

            if session is None:
                return False

            db.delete(session)
            db.commit()

            return True