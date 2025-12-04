"""Service entity - represents a service offered by the business."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class Service:
    """A service is something the business offers to customers."""

    id: str
    category_id: str
    branch_id: str
    name: str
    price: Decimal
    duration_minutes: int
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    is_active: bool = True
    category_name: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Service":
        """Creates a Service from a dictionary."""
        price = data["price"]
        if not isinstance(price, Decimal):
            price = Decimal(str(price))

        return cls(
            id=data["id"],
            category_id=data["category_id"],
            branch_id=data["branch_id"],
            name=data["name"],
            price=price,
            duration_minutes=data["duration_minutes"],
            description=data.get("description"),
            created_at=data.get("created_at"),
            is_active=bool(data.get("is_active", 1)),
            category_name=data.get("category_name"),
        )

    def to_dict(self) -> dict:
        """Converts to dictionary."""
        return {
            "id": self.id,
            "category_id": self.category_id,
            "branch_id": self.branch_id,
            "name": self.name,
            "price": self.price,
            "duration_minutes": self.duration_minutes,
            "description": self.description,
            "created_at": self.created_at,
            "is_active": self.is_active,
            "category_name": self.category_name,
        }

    @property
    def price_formatted(self) -> str:
        """Price formatted with currency symbol."""
        return f"${float(self.price):.2f}"

    @property
    def duration_formatted(self) -> str:
        """Formatted duration."""
        return f"{self.duration_minutes} min"
