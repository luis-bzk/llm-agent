"""Interface for calendar repository."""

from abc import ABC, abstractmethod
from typing import Optional

from ...domain.calendar import Calendar


class ICalendarRepository(ABC):
    """Contract for calendar data access."""

    @abstractmethod
    def get_by_id(self, calendar_id: str) -> Optional[Calendar]:
        """Gets a calendar by ID."""
        pass

    @abstractmethod
    def get_by_branch(self, branch_id: str) -> list[Calendar]:
        """Gets all active calendars for a branch."""
        pass

    @abstractmethod
    def get_for_service(self, service_id: str) -> list[Calendar]:
        """Gets all calendars that offer a service."""
        pass

    @abstractmethod
    def find_by_name(self, branch_id: str, name: str) -> Optional[Calendar]:
        """Finds a calendar by partial name within a branch."""
        pass
