"""User entity - represents an end user (business customer)."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """A user is an end customer of a business."""

    id: str
    client_id: str
    phone_number: str
    identification_number: str
    full_name: str
    email: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_interaction_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """Creates a User from a dictionary."""
        return cls(
            id=data["id"],
            client_id=data["client_id"],
            phone_number=data["phone_number"],
            identification_number=data["identification_number"],
            full_name=data["full_name"],
            email=data.get("email"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            last_interaction_at=data.get("last_interaction_at"),
        )

    def to_dict(self) -> dict:
        """Converts to dictionary."""
        return {
            "id": self.id,
            "client_id": self.client_id,
            "phone_number": self.phone_number,
            "identification_number": self.identification_number,
            "full_name": self.full_name,
            "email": self.email,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_interaction_at": self.last_interaction_at,
        }
