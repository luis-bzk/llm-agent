"""Interface for category repository."""

from abc import ABC, abstractmethod
from typing import Optional

from ...domain.category import Category


class ICategoryRepository(ABC):
    """Contract for category data access."""

    @abstractmethod
    def get_by_id(self, category_id: str) -> Optional[Category]:
        """Gets a category by ID."""
        pass

    @abstractmethod
    def get_by_branch(self, branch_id: str) -> list[Category]:
        """Gets all active categories for a branch."""
        pass
