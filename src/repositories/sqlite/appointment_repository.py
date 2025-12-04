"""SQLite implementation of AppointmentRepository."""

from datetime import datetime, date, time
from typing import Optional

from ..interfaces.appointment_repository import IAppointmentRepository
from ...domain.appointment import Appointment
from .connection import SQLiteConnection


class SQLiteAppointmentRepository(IAppointmentRepository):
    """SQLite implementation of appointment repository."""

    def __init__(self, connection: SQLiteConnection):
        self._conn = connection

    def get_by_id(self, appointment_id: str) -> Optional[Appointment]:
        """Gets an appointment by ID."""
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM appointments WHERE id = ?", (appointment_id,))
            row = cursor.fetchone()
            return Appointment.from_dict(dict(row)) if row else None

    def get_by_user(self, user_id: str) -> list[Appointment]:
        """Gets all appointments for a user."""
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM appointments
                   WHERE user_id = ?
                   ORDER BY appointment_date DESC, start_time DESC""",
                (user_id,),
            )
            return [Appointment.from_dict(dict(row)) for row in cursor.fetchall()]

    def get_upcoming_by_user(self, user_id: str) -> list[Appointment]:
        """Gets future appointments for a user."""
        today = date.today()
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM appointments
                   WHERE user_id = ? AND appointment_date >= ? AND status = 'scheduled'
                   ORDER BY appointment_date, start_time""",
                (user_id, today),
            )
            return [Appointment.from_dict(dict(row)) for row in cursor.fetchall()]

    def get_by_calendar_and_date(
        self, calendar_id: str, appointment_date: date
    ) -> list[Appointment]:
        """Gets appointments for a calendar on a specific date."""
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM appointments
                   WHERE calendar_id = ? AND appointment_date = ? AND status = 'scheduled'
                   ORDER BY start_time""",
                (calendar_id, appointment_date),
            )
            return [Appointment.from_dict(dict(row)) for row in cursor.fetchall()]

    def create(self, appointment: Appointment) -> Appointment:
        """Creates a new appointment."""
        now = datetime.now()
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO appointments (
                    id, user_id, calendar_id, service_id, branch_id,
                    service_name_snapshot, service_price_snapshot, service_duration_snapshot,
                    calendar_name_snapshot, appointment_date, start_time, end_time,
                    google_event_id, status, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    appointment.id,
                    appointment.user_id,
                    appointment.calendar_id,
                    appointment.service_id,
                    appointment.branch_id,
                    appointment.service_name_snapshot,
                    appointment.service_price_snapshot,
                    appointment.service_duration_snapshot,
                    appointment.calendar_name_snapshot,
                    appointment.appointment_date,
                    appointment.start_time,
                    appointment.end_time,
                    appointment.google_event_id,
                    appointment.status,
                    appointment.notes,
                    now,
                    now,
                ),
            )
        appointment.created_at = now
        appointment.updated_at = now
        return appointment

    def update(self, appointment: Appointment) -> Appointment:
        """Updates an existing appointment."""
        now = datetime.now()
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE appointments SET
                    appointment_date = ?,
                    start_time = ?,
                    end_time = ?,
                    google_event_id = ?,
                    status = ?,
                    notes = ?,
                    updated_at = ?
                WHERE id = ?""",
                (
                    appointment.appointment_date,
                    appointment.start_time,
                    appointment.end_time,
                    appointment.google_event_id,
                    appointment.status,
                    appointment.notes,
                    now,
                    appointment.id,
                ),
            )
        appointment.updated_at = now
        return appointment

    def cancel(self, appointment_id: str, reason: str, cancelled_by: str) -> bool:
        """Cancels an appointment."""
        now = datetime.now()
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE appointments
                   SET status = 'cancelled', cancellation_reason = ?,
                       cancelled_at = ?, cancelled_by = ?, updated_at = ?
                   WHERE id = ?""",
                (reason, now, cancelled_by, now, appointment_id),
            )
            return cursor.rowcount > 0

    def reschedule(
        self,
        appointment_id: str,
        new_date: date,
        new_start_time: time,
        new_end_time: time,
        new_google_event_id: Optional[str] = None,
    ) -> bool:
        """Reschedules an appointment to a new date/time."""
        now = datetime.now()
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE appointments
                   SET appointment_date = ?, start_time = ?, end_time = ?,
                       google_event_id = ?, updated_at = ?
                   WHERE id = ?""",
                (
                    new_date,
                    new_start_time,
                    new_end_time,
                    new_google_event_id,
                    now,
                    appointment_id,
                ),
            )
            return cursor.rowcount > 0
