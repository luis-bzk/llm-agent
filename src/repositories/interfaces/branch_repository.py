"""Interface for branch repository."""

from abc import ABC, abstractmethod
from typing import Optional

from ...domain.branch import Branch


class IBranchRepository(ABC):
    """Contract for branch data access."""

    @abstractmethod
    def get_by_id(self, branch_id: str) -> Optional[Branch]:
        """Gets a branch by ID."""
        pass

    @abstractmethod
    def get_by_client(self, client_id: str) -> list[Branch]:
        """Gets all active branches for a client."""
        pass

    @abstractmethod
    def get_all_active(self, client_id: str) -> list[Branch]:
        """Gets all active branches for a client."""
        pass
