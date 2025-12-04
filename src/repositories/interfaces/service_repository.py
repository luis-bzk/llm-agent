"""Interface for service repository."""

from abc import ABC, abstractmethod
from typing import Optional

from ...domain.service import Service


class IServiceRepository(ABC):
    """Contract for service data access."""

    @abstractmethod
    def get_by_id(self, service_id: str) -> Optional[Service]:
        """Gets a service by ID."""
        pass

    @abstractmethod
    def get_by_branch(self, branch_id: str) -> list[Service]:
        """Gets all active services for a branch."""
        pass

    @abstractmethod
    def get_by_category(self, category_id: str) -> list[Service]:
        """Gets all active services for a category."""
        pass

    @abstractmethod
    def find_by_name(self, branch_id: str, name: str) -> Optional[Service]:
        """Finds a service by partial name within a branch."""
        pass
