"""Interface for conversation and message repository."""

from abc import ABC, abstractmethod
from typing import Optional

from ...domain.conversation import Conversation
from ...domain.message import Message


class IConversationRepository(ABC):
    """Contract for conversation and message data access."""

    @abstractmethod
    def get_by_id(self, conversation_id: str) -> Optional[Conversation]:
        """Gets a conversation by ID."""
        pass

    @abstractmethod
    def get_active(
        self, session_id: str, timeout_hours: int = 2
    ) -> Optional[Conversation]:
        """Gets the active conversation for a session within timeout."""
        pass

    @abstractmethod
    def create(self, session_id: str) -> Conversation:
        """Creates a new conversation."""
        pass

    @abstractmethod
    def update_summary(self, conversation_id: str, summary: str) -> None:
        """Updates the summary of a conversation."""
        pass

    @abstractmethod
    def escalate(self, conversation_id: str, reason: str) -> None:
        """Escalates a conversation to human operator."""
        pass

    @abstractmethod
    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        tool_call_id: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Message:
        """Adds a message to the conversation."""
        pass

    @abstractmethod
    def get_messages(
        self, conversation_id: str, limit: Optional[int] = None
    ) -> list[Message]:
        """Gets the messages of a conversation."""
        pass
