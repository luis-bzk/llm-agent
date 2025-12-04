"""Calendar entity - represents a schedulable resource (employee)."""

from dataclasses import dataclass
from datetime import datetime, time
from typing import Optional


@dataclass
class Calendar:
    """A calendar represents a schedulable resource linked to Google Calendar."""

    id: str
    branch_id: str
    name: str
    google_calendar_id: str
    google_account_email: Optional[str] = None
    default_start_time: Optional[time] = None
    default_end_time: Optional[time] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_active: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "Calendar":
        """Creates a Calendar from a dictionary."""
        return cls(
            id=data["id"],
            branch_id=data["branch_id"],
            name=data["name"],
            google_calendar_id=data["google_calendar_id"],
            google_account_email=data.get("google_account_email"),
            default_start_time=data.get("default_start_time"),
            default_end_time=data.get("default_end_time"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            is_active=bool(data.get("is_active", 1)),
        )

    def to_dict(self) -> dict:
        """Converts to dictionary."""
        return {
            "id": self.id,
            "branch_id": self.branch_id,
            "name": self.name,
            "google_calendar_id": self.google_calendar_id,
            "google_account_email": self.google_account_email,
            "default_start_time": self.default_start_time,
            "default_end_time": self.default_end_time,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "is_active": self.is_active,
        }
