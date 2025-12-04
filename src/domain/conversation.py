"""Conversation entity - represents a conversation within a session."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Conversation:
    """A conversation is a dialogue with a start and end."""

    id: str
    session_id: str
    status: str = "active"
    escalated_to_chatwoot: bool = False
    escalated_at: Optional[datetime] = None
    escalation_reason: Optional[str] = None
    summary: Optional[str] = None
    summary_updated_at: Optional[datetime] = None
    message_count: int = 0
    created_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Conversation":
        """Creates a Conversation from a dictionary."""
        return cls(
            id=data["id"],
            session_id=data["session_id"],
            status=data.get("status", "active"),
            escalated_to_chatwoot=bool(data.get("escalated_to_chatwoot", 0)),
            escalated_at=data.get("escalated_at"),
            escalation_reason=data.get("escalation_reason"),
            summary=data.get("summary"),
            summary_updated_at=data.get("summary_updated_at"),
            message_count=data.get("message_count", 0),
            created_at=data.get("created_at"),
            last_message_at=data.get("last_message_at"),
            expired_at=data.get("expired_at"),
        )

    def to_dict(self) -> dict:
        """Converts to dictionary."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "status": self.status,
            "escalated_to_chatwoot": self.escalated_to_chatwoot,
            "escalated_at": self.escalated_at,
            "escalation_reason": self.escalation_reason,
            "summary": self.summary,
            "summary_updated_at": self.summary_updated_at,
            "message_count": self.message_count,
            "created_at": self.created_at,
            "last_message_at": self.last_message_at,
            "expired_at": self.expired_at,
        }

    @property
    def is_active(self) -> bool:
        """Checks if conversation is active."""
        return self.status == "active"
