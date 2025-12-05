"""SQLite implementation of ClientRepository."""

from typing import Optional

from ..interfaces.client_repository import IClientRepository
from ...domain.client import Client
from ...config import logger as log
from .connection import SQLiteConnection


class SQLiteClientRepository(IClientRepository):
    """SQLite implementation of client repository."""

    def __init__(self, connection: SQLiteConnection):
        self._conn = connection

    def get_by_id(self, client_id: str) -> Optional[Client]:
        """Gets a client by ID."""
        log.debug("repo.client", "get_by_id", client_id=client_id)
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM clients WHERE id = ?", (client_id,))
            row = cursor.fetchone()
            result = Client.from_dict(dict(row)) if row else None
            log.debug(
                "repo.client",
                "get_by_id result",
                found=result is not None,
                name=result.business_name if result else None,
                appointment_type=result.appointment_type if result else None,
            )
            return result

    def get_by_whatsapp(self, whatsapp_number: str) -> Optional[Client]:
        """Gets a client by WhatsApp number."""
        log.debug("repo.client", "get_by_whatsapp", whatsapp_number=whatsapp_number)
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM clients WHERE whatsapp_number = ?",
                (whatsapp_number,),
            )
            row = cursor.fetchone()
            result = Client.from_dict(dict(row)) if row else None
            log.debug(
                "repo.client",
                "get_by_whatsapp result",
                found=result is not None,
                client_id=result.id if result else None,
            )
            return result

    def get_by_email(self, email: str) -> Optional[Client]:
        """Gets a client by email."""
        log.debug("repo.client", "get_by_email", email=email)
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM clients WHERE email = ?", (email,))
            row = cursor.fetchone()
            result = Client.from_dict(dict(row)) if row else None
            log.debug("repo.client", "get_by_email result", found=result is not None)
            return result

    def get_all_active(self) -> list[Client]:
        """Gets all active clients."""
        log.debug("repo.client", "get_all_active")
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM clients WHERE is_active = 1")
            results = [Client.from_dict(dict(row)) for row in cursor.fetchall()]
            log.debug("repo.client", "get_all_active result", count=len(results))
            return results
