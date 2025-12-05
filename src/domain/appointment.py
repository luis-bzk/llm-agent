"""Appointment entity - represents a scheduled appointment."""

from dataclasses import dataclass
from datetime import datetime, date, time
from decimal import Decimal
from typing import Optional, Literal


AppointmentStatus = Literal["scheduled", "completed", "cancelled", "no_show"]


@dataclass
class Appointment:
    """An appointment is a service booking at a specific time."""

    id: str
    user_id: str
    calendar_id: str
    service_id: str
    branch_id: str
    service_name_snapshot: str
    service_price_snapshot: Decimal
    service_duration_snapshot: int
    calendar_name_snapshot: str
    appointment_date: date
    start_time: time
    end_time: time
    google_event_id: Optional[str] = None
    google_meet_link: Optional[str] = None
    status: AppointmentStatus = "scheduled"
    cancellation_reason: Optional[str] = None
    cancelled_at: Optional[datetime] = None
    cancelled_by: Optional[str] = None
    notes: Optional[str] = None
    reminder_sent: bool = False
    reminder_sent_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Appointment":
        """Creates an Appointment from a dictionary."""
        price = data["service_price_snapshot"]
        if not isinstance(price, Decimal):
            price = Decimal(str(price))

        return cls(
            id=data["id"],
            user_id=data["user_id"],
            calendar_id=data["calendar_id"],
            service_id=data["service_id"],
            branch_id=data["branch_id"],
            service_name_snapshot=data["service_name_snapshot"],
            service_price_snapshot=price,
            service_duration_snapshot=data["service_duration_snapshot"],
            calendar_name_snapshot=data["calendar_name_snapshot"],
            appointment_date=data["appointment_date"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            google_event_id=data.get("google_event_id"),
            google_meet_link=data.get("google_meet_link"),
            status=data.get("status", "scheduled"),
            cancellation_reason=data.get("cancellation_reason"),
            cancelled_at=data.get("cancelled_at"),
            cancelled_by=data.get("cancelled_by"),
            notes=data.get("notes"),
            reminder_sent=bool(data.get("reminder_sent", 0)),
            reminder_sent_at=data.get("reminder_sent_at"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    def to_dict(self) -> dict:
        """Converts to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "calendar_id": self.calendar_id,
            "service_id": self.service_id,
            "branch_id": self.branch_id,
            "service_name_snapshot": self.service_name_snapshot,
            "service_price_snapshot": self.service_price_snapshot,
            "service_duration_snapshot": self.service_duration_snapshot,
            "calendar_name_snapshot": self.calendar_name_snapshot,
            "appointment_date": self.appointment_date,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "google_event_id": self.google_event_id,
            "google_meet_link": self.google_meet_link,
            "status": self.status,
            "cancellation_reason": self.cancellation_reason,
            "cancelled_at": self.cancelled_at,
            "cancelled_by": self.cancelled_by,
            "notes": self.notes,
            "reminder_sent": self.reminder_sent,
            "reminder_sent_at": self.reminder_sent_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @property
    def is_cancelled(self) -> bool:
        """Checks if appointment is cancelled."""
        return self.status == "cancelled"

    @property
    def is_upcoming(self) -> bool:
        """Checks if appointment is upcoming."""
        today = date.today()
        return self.appointment_date >= today and self.status == "scheduled"
