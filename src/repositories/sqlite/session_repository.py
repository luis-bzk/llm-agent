"""SQLite implementation of SessionRepository."""

import uuid
from datetime import datetime
from typing import Optional

from ..interfaces.session_repository import ISessionRepository
from ...domain.session import Session
from .connection import SQLiteConnection


class SQLiteSessionRepository(ISessionRepository):
    """SQLite implementation of session repository."""

    def __init__(self, connection: SQLiteConnection):
        self._conn = connection

    def get_by_id(self, session_id: str) -> Optional[Session]:
        """Gets a session by ID."""
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            return Session.from_dict(dict(row)) if row else None

    def get_or_create(self, client_id: str, phone_number: str) -> Session:
        """Gets an existing session or creates a new one."""
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM sessions WHERE client_id = ? AND phone_number = ?",
                (client_id, phone_number),
            )
            row = cursor.fetchone()

            if row:
                now = datetime.now()
                cursor.execute(
                    "UPDATE sessions SET last_activity_at = ? WHERE id = ?",
                    (now, row["id"]),
                )
                session = Session.from_dict(dict(row))
                session.last_activity_at = now
                return session

            now = datetime.now()
            session_id = str(uuid.uuid4())
            cursor.execute(
                """INSERT INTO sessions (id, client_id, phone_number, created_at, last_activity_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (session_id, client_id, phone_number, now, now),
            )

            return Session(
                id=session_id,
                client_id=client_id,
                phone_number=phone_number,
                created_at=now,
                last_activity_at=now,
            )

    def link_to_user(self, session_id: str, user_id: str) -> None:
        """Links a session to a user."""
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE sessions SET user_id = ? WHERE id = ?",
                (user_id, session_id),
            )

    def get_memory_profile(self, session_id: str) -> Optional[str]:
        """Gets the memory_profile JSON from a session."""
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT memory_profile FROM sessions WHERE id = ?",
                (session_id,),
            )
            row = cursor.fetchone()
            return row["memory_profile"] if row else None

    def update_memory_profile(self, session_id: str, memory_profile_json: str) -> None:
        """Updates the memory_profile of a session."""
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE sessions
                   SET memory_profile = ?, memory_profile_updated_at = ?
                   WHERE id = ?""",
                (memory_profile_json, datetime.now(), session_id),
            )

    def update_activity(self, session_id: str) -> None:
        """Updates the last activity timestamp."""
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE sessions SET last_activity_at = ? WHERE id = ?",
                (datetime.now(), session_id),
            )
