"""SQLite implementation of CalendarRepository."""

from typing import Optional

from ..interfaces.calendar_repository import ICalendarRepository
from ...domain.calendar import Calendar
from ...config import logger as log
from .connection import SQLiteConnection


class SQLiteCalendarRepository(ICalendarRepository):
    """SQLite implementation of calendar repository."""

    def __init__(self, connection: SQLiteConnection):
        self._conn = connection

    def get_by_id(self, calendar_id: str) -> Optional[Calendar]:
        """Gets a calendar by ID."""
        log.debug("repo.calendar", "get_by_id", calendar_id=calendar_id)
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM calendars WHERE id = ?", (calendar_id,))
            row = cursor.fetchone()
            result = Calendar.from_dict(dict(row)) if row else None
            log.debug(
                "repo.calendar",
                "get_by_id result",
                found=result is not None,
                name=result.name if result else None,
                google_id=result.google_calendar_id if result else None,
            )
            return result

    def get_by_branch(self, branch_id: str) -> list[Calendar]:
        """Gets all active calendars for a branch."""
        log.debug("repo.calendar", "get_by_branch", branch_id=branch_id)
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM calendars WHERE branch_id = ? AND is_active = 1",
                (branch_id,),
            )
            results = [Calendar.from_dict(dict(row)) for row in cursor.fetchall()]
            log.debug("repo.calendar", "get_by_branch result", count=len(results))
            return results

    def get_for_service(self, service_id: str) -> list[Calendar]:
        """Gets all calendars that offer a service."""
        log.debug("repo.calendar", "get_for_service", service_id=service_id)
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT c.* FROM calendars c
                   JOIN calendar_services cs ON c.id = cs.calendar_id
                   WHERE cs.service_id = ? AND c.is_active = 1""",
                (service_id,),
            )
            results = [Calendar.from_dict(dict(row)) for row in cursor.fetchall()]
            log.debug(
                "repo.calendar",
                "get_for_service result",
                count=len(results),
                names=[c.name for c in results],
            )
            return results

    def find_by_name(self, branch_id: str, name: str) -> Optional[Calendar]:
        """Finds a calendar by partial name within a branch."""
        log.debug("repo.calendar", "find_by_name", branch_id=branch_id, name=name)
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM calendars
                   WHERE branch_id = ? AND is_active = 1
                   AND LOWER(name) LIKE LOWER(?)""",
                (branch_id, f"%{name}%"),
            )
            row = cursor.fetchone()
            result = Calendar.from_dict(dict(row)) if row else None
            log.debug(
                "repo.calendar",
                "find_by_name result",
                found=result is not None,
                calendar_id=result.id if result else None,
                matched_name=result.name if result else None,
            )
            return result
