"""Interface for system configuration repository."""

from abc import ABC, abstractmethod
from typing import Optional

from ...domain.system_config import SystemConfig


class ISystemConfigRepository(ABC):
    """Contract for system configuration data access."""

    @abstractmethod
    def get(self, key: str) -> Optional[SystemConfig]:
        """Gets a configuration by key."""
        pass

    @abstractmethod
    def get_value(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Gets a configuration value by key, returns default if not found."""
        pass

    @abstractmethod
    def get_all(self) -> list[SystemConfig]:
        """Gets all configuration entries."""
        pass

    @abstractmethod
    def set(
        self, key: str, value: str, description: Optional[str] = None
    ) -> SystemConfig:
        """Sets a configuration value (creates or updates)."""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Deletes a configuration entry."""
        pass
