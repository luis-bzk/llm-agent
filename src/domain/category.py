"""Category entity - represents a service category."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Category:
    """A category groups related services."""

    id: str
    branch_id: str
    name: str
    description: Optional[str] = None
    display_order: int = 0
    created_at: Optional[datetime] = None
    is_active: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "Category":
        """Creates a Category from a dictionary."""
        return cls(
            id=data["id"],
            branch_id=data["branch_id"],
            name=data["name"],
            description=data.get("description"),
            display_order=data.get("display_order", 0),
            created_at=data.get("created_at"),
            is_active=bool(data.get("is_active", 1)),
        )

    def to_dict(self) -> dict:
        """Converts to dictionary."""
        return {
            "id": self.id,
            "branch_id": self.branch_id,
            "name": self.name,
            "description": self.description,
            "display_order": self.display_order,
            "created_at": self.created_at,
            "is_active": self.is_active,
        }
