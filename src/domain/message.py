"""Message entity - represents a message in a conversation."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Literal


MessageRole = Literal["human", "ai", "system", "tool"]


@dataclass
class Message:
    """A message is a unit of communication in a conversation."""

    id: str
    conversation_id: str
    role: MessageRole
    content: str
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None
    created_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Message":
        """Creates a Message from a dictionary."""
        return cls(
            id=data["id"],
            conversation_id=data["conversation_id"],
            role=data["role"],
            content=data["content"],
            tool_call_id=data.get("tool_call_id"),
            tool_name=data.get("tool_name"),
            created_at=data.get("created_at"),
        )

    def to_dict(self) -> dict:
        """Converts to dictionary."""
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "tool_call_id": self.tool_call_id,
            "tool_name": self.tool_name,
            "created_at": self.created_at,
        }

    @property
    def is_human(self) -> bool:
        """Checks if message is from user."""
        return self.role == "human"

    @property
    def is_ai(self) -> bool:
        """Checks if message is from assistant."""
        return self.role == "ai"
