"""Interface for session repository."""

from abc import ABC, abstractmethod
from typing import Optional

from ...domain.session import Session


class ISessionRepository(ABC):
    """Contract for session data access."""

    @abstractmethod
    def get_by_id(self, session_id: str) -> Optional[Session]:
        """Gets a session by ID."""
        pass

    @abstractmethod
    def get_or_create(self, client_id: str, phone_number: str) -> Session:
        """Gets an existing session or creates a new one."""
        pass

    @abstractmethod
    def link_to_user(self, session_id: str, user_id: str) -> None:
        """Links a session to a user."""
        pass

    @abstractmethod
    def get_memory_profile(self, session_id: str) -> Optional[str]:
        """Gets the memory_profile JSON from a session."""
        pass

    @abstractmethod
    def update_memory_profile(self, session_id: str, memory_profile_json: str) -> None:
        """Updates the memory_profile of a session."""
        pass

    @abstractmethod
    def update_activity(self, session_id: str) -> None:
        """Updates the last activity timestamp."""
        pass
