"""Branch entity - represents a business location."""

from dataclasses import dataclass
from datetime import datetime, time
from typing import Optional


@dataclass
class Branch:
    """A branch is a physical location of a business."""

    id: str
    client_id: str
    name: str
    address: str
    city: Optional[str] = None
    opening_time: Optional[time] = None
    closing_time: Optional[time] = None
    working_days: str = "1,2,3,4,5"
    phone: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_active: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "Branch":
        """Creates a Branch from a dictionary."""
        return cls(
            id=data["id"],
            client_id=data["client_id"],
            name=data["name"],
            address=data["address"],
            city=data.get("city"),
            opening_time=data.get("opening_time"),
            closing_time=data.get("closing_time"),
            working_days=data.get("working_days", "1,2,3,4,5"),
            phone=data.get("phone"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            is_active=bool(data.get("is_active", 1)),
        )

    def to_dict(self) -> dict:
        """Converts to dictionary."""
        return {
            "id": self.id,
            "client_id": self.client_id,
            "name": self.name,
            "address": self.address,
            "city": self.city,
            "opening_time": self.opening_time,
            "closing_time": self.closing_time,
            "working_days": self.working_days,
            "phone": self.phone,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "is_active": self.is_active,
        }
