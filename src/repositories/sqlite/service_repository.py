"""SQLite implementation of ServiceRepository."""

from typing import Optional

from ..interfaces.service_repository import IServiceRepository
from ...domain.service import Service
from .connection import SQLiteConnection


class SQLiteServiceRepository(IServiceRepository):
    """SQLite implementation of service repository."""

    def __init__(self, connection: SQLiteConnection):
        self._conn = connection

    def get_by_id(self, service_id: str) -> Optional[Service]:
        """Gets a service by ID."""
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM services WHERE id = ?", (service_id,))
            row = cursor.fetchone()
            return Service.from_dict(dict(row)) if row else None

    def get_by_branch(self, branch_id: str) -> list[Service]:
        """Gets all active services for a branch."""
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT s.*, c.name as category_name
                   FROM services s
                   JOIN categories c ON s.category_id = c.id
                   WHERE s.branch_id = ? AND s.is_active = 1""",
                (branch_id,),
            )
            return [Service.from_dict(dict(row)) for row in cursor.fetchall()]

    def get_by_category(self, category_id: str) -> list[Service]:
        """Gets all active services for a category."""
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM services WHERE category_id = ? AND is_active = 1",
                (category_id,),
            )
            return [Service.from_dict(dict(row)) for row in cursor.fetchall()]

    def find_by_name(self, branch_id: str, name: str) -> Optional[Service]:
        """Finds a service by partial name within a branch."""
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM services
                   WHERE branch_id = ? AND is_active = 1
                   AND LOWER(name) LIKE LOWER(?)""",
                (branch_id, f"%{name}%"),
            )
            row = cursor.fetchone()
            return Service.from_dict(dict(row)) if row else None
