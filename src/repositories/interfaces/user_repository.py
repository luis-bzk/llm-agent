"""Interface for user repository."""

from abc import ABC, abstractmethod
from typing import Optional

from ...domain.user import User


class IUserRepository(ABC):
    """Contract for user data access."""

    @abstractmethod
    def get_by_id(self, user_id: str) -> Optional[User]:
        """Gets a user by ID."""
        pass

    @abstractmethod
    def get_by_phone(self, client_id: str, phone_number: str) -> Optional[User]:
        """Gets a user by phone number within a client."""
        pass

    @abstractmethod
    def get_by_identification(
        self, client_id: str, identification_number: str
    ) -> Optional[User]:
        """Gets a user by ID number within a client."""
        pass

    @abstractmethod
    def create(self, user: User) -> User:
        """Creates a new user."""
        pass

    @abstractmethod
    def update(self, user: User) -> User:
        """Updates an existing user."""
        pass
