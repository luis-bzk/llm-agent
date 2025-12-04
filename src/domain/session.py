"""Session entity - represents a WhatsApp session."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Session:
    """A session represents a user's connection with a client (business)."""

    id: str
    client_id: str
    phone_number: str
    user_id: Optional[str] = None
    memory_profile_key: Optional[str] = None
    memory_profile: Optional[str] = None
    memory_profile_updated_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        """Creates a Session from a dictionary."""
        return cls(
            id=data["id"],
            client_id=data["client_id"],
            phone_number=data["phone_number"],
            user_id=data.get("user_id"),
            memory_profile_key=data.get("memory_profile_key"),
            memory_profile=data.get("memory_profile"),
            memory_profile_updated_at=data.get("memory_profile_updated_at"),
            created_at=data.get("created_at"),
            last_activity_at=data.get("last_activity_at"),
        )

    def to_dict(self) -> dict:
        """Converts to dictionary."""
        return {
            "id": self.id,
            "client_id": self.client_id,
            "phone_number": self.phone_number,
            "user_id": self.user_id,
            "memory_profile_key": self.memory_profile_key,
            "memory_profile": self.memory_profile,
            "memory_profile_updated_at": self.memory_profile_updated_at,
            "created_at": self.created_at,
            "last_activity_at": self.last_activity_at,
        }
