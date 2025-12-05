"""SQLite implementation of UserRepository."""

from datetime import datetime
from typing import Optional

from ..interfaces.user_repository import IUserRepository
from ...domain.user import User
from ...config import logger as log
from .connection import SQLiteConnection


class SQLiteUserRepository(IUserRepository):
    """SQLite implementation of user repository."""

    def __init__(self, connection: SQLiteConnection):
        self._conn = connection

    def get_by_id(self, user_id: str) -> Optional[User]:
        """Gets a user by ID."""
        log.debug("repo.user", "get_by_id", user_id=user_id)
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            result = User.from_dict(dict(row)) if row else None
            log.debug(
                "repo.user",
                "get_by_id result",
                found=result is not None,
                name=result.full_name if result else None,
                client_id=result.client_id if result else None,
            )
            return result

    def get_by_phone(self, client_id: str, phone_number: str) -> Optional[User]:
        """Gets a user by phone number within a client."""
        log.debug("repo.user", "get_by_phone", client_id=client_id, phone=phone_number)
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM users WHERE client_id = ? AND phone_number = ?",
                (client_id, phone_number),
            )
            row = cursor.fetchone()
            result = User.from_dict(dict(row)) if row else None
            log.debug(
                "repo.user",
                "get_by_phone result",
                found=result is not None,
                user_id=result.id if result else None,
            )
            return result

    def get_by_identification(
        self, client_id: str, identification_number: str
    ) -> Optional[User]:
        """Gets a user by ID number within a client."""
        log.debug(
            "repo.user",
            "get_by_identification",
            client_id=client_id,
            cedula=identification_number,
        )
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM users WHERE client_id = ? AND identification_number = ?",
                (client_id, identification_number),
            )
            row = cursor.fetchone()
            result = User.from_dict(dict(row)) if row else None
            log.debug(
                "repo.user",
                "get_by_identification result",
                found=result is not None,
                user_id=result.id if result else None,
                name=result.full_name if result else None,
            )
            return result

    def create(self, user: User) -> User:
        """Creates a new user."""
        log.info(
            "repo.user",
            "create",
            user_id=user.id,
            client_id=user.client_id,
            name=user.full_name,
            phone=user.phone_number,
        )
        now = datetime.now()
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO users (
                    id, client_id, phone_number, identification_number,
                    full_name, email, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    user.id,
                    user.client_id,
                    user.phone_number,
                    user.identification_number,
                    user.full_name,
                    user.email,
                    now,
                    now,
                ),
            )
        user.created_at = now
        user.updated_at = now
        log.debug("repo.user", "create success", user_id=user.id)
        return user

    def update(self, user: User) -> User:
        """Updates an existing user."""
        log.debug("repo.user", "update", user_id=user.id, name=user.full_name)
        now = datetime.now()
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE users SET
                    phone_number = ?,
                    identification_number = ?,
                    full_name = ?,
                    email = ?,
                    updated_at = ?,
                    last_interaction_at = ?
                WHERE id = ?""",
                (
                    user.phone_number,
                    user.identification_number,
                    user.full_name,
                    user.email,
                    now,
                    user.last_interaction_at or now,
                    user.id,
                ),
            )
        user.updated_at = now
        log.debug("repo.user", "update success", user_id=user.id)
        return user
