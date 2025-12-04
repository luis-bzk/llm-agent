"""Interface for appointment repository."""

from abc import ABC, abstractmethod
from datetime import date, time
from typing import Optional

from ...domain.appointment import Appointment


class IAppointmentRepository(ABC):
    """Contract for appointment data access."""

    @abstractmethod
    def get_by_id(self, appointment_id: str) -> Optional[Appointment]:
        """Gets an appointment by ID."""
        pass

    @abstractmethod
    def get_by_user(self, user_id: str) -> list[Appointment]:
        """Gets all appointments for a user."""
        pass

    @abstractmethod
    def get_upcoming_by_user(self, user_id: str) -> list[Appointment]:
        """Gets future appointments for a user."""
        pass

    @abstractmethod
    def get_by_calendar_and_date(
        self, calendar_id: str, appointment_date: date
    ) -> list[Appointment]:
        """Gets appointments for a calendar on a specific date."""
        pass

    @abstractmethod
    def create(self, appointment: Appointment) -> Appointment:
        """Creates a new appointment."""
        pass

    @abstractmethod
    def update(self, appointment: Appointment) -> Appointment:
        """Updates an existing appointment."""
        pass

    @abstractmethod
    def cancel(self, appointment_id: str, reason: str, cancelled_by: str) -> bool:
        """Cancels an appointment."""
        pass

    @abstractmethod
    def reschedule(
        self,
        appointment_id: str,
        new_date: date,
        new_start_time: time,
        new_end_time: time,
        new_google_event_id: Optional[str] = None,
    ) -> bool:
        """Reschedules an appointment to a new date/time."""
        pass
