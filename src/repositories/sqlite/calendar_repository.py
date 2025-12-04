"""SQLite implementation of CalendarRepository."""

from typing import Optional

from ..interfaces.calendar_repository import ICalendarRepository
from ...domain.calendar import Calendar
from .connection import SQLiteConnection


class SQLiteCalendarRepository(ICalendarRepository):
    """SQLite implementation of calendar repository."""

    def __init__(self, connection: SQLiteConnection):
        self._conn = connection

    def get_by_id(self, calendar_id: str) -> Optional[Calendar]:
        """Gets a calendar by ID."""
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM calendars WHERE id = ?", (calendar_id,))
            row = cursor.fetchone()
            return Calendar.from_dict(dict(row)) if row else None

    def get_by_branch(self, branch_id: str) -> list[Calendar]:
        """Gets all active calendars for a branch."""
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM calendars WHERE branch_id = ? AND is_active = 1",
                (branch_id,),
            )
            return [Calendar.from_dict(dict(row)) for row in cursor.fetchall()]

    def get_for_service(self, service_id: str) -> list[Calendar]:
        """Gets all calendars that offer a service."""
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT c.* FROM calendars c
                   JOIN calendar_services cs ON c.id = cs.calendar_id
                   WHERE cs.service_id = ? AND c.is_active = 1""",
                (service_id,),
            )
            return [Calendar.from_dict(dict(row)) for row in cursor.fetchall()]

    def find_by_name(self, branch_id: str, name: str) -> Optional[Calendar]:
        """Finds a calendar by partial name within a branch."""
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM calendars
                   WHERE branch_id = ? AND is_active = 1
                   AND LOWER(name) LIKE LOWER(?)""",
                (branch_id, f"%{name}%"),
            )
            row = cursor.fetchone()
            return Calendar.from_dict(dict(row)) if row else None
