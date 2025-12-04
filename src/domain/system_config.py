"""SystemConfig entity - represents a system configuration entry."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class SystemConfig:
    """A key-value configuration entry for the system."""

    key: str
    value: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: dict) -> "SystemConfig":
        """Creates a SystemConfig from a dictionary."""
        return cls(
            key=data["key"],
            value=data["value"],
            description=data.get("description"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    def to_dict(self) -> dict:
        """Converts to dictionary."""
        return {
            "key": self.key,
            "value": self.value,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def as_int(self) -> int:
        """Returns value as integer."""
        return int(self.value)

    def as_float(self) -> float:
        """Returns value as float."""
        return float(self.value)

    def as_bool(self) -> bool:
        """Returns value as boolean."""
        return self.value.lower() in ("true", "1", "yes")
