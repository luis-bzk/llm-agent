"""Interface for client (business) repository."""

from abc import ABC, abstractmethod
from typing import Optional

from ...domain.client import Client


class IClientRepository(ABC):
    """Contract for client data access."""

    @abstractmethod
    def get_by_id(self, client_id: str) -> Optional[Client]:
        """Gets a client by ID."""
        pass

    @abstractmethod
    def get_by_whatsapp(self, whatsapp_number: str) -> Optional[Client]:
        """Gets a client by WhatsApp number."""
        pass

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[Client]:
        """Gets a client by email."""
        pass

    @abstractmethod
    def get_all_active(self) -> list[Client]:
        """Gets all active clients."""
        pass
