"""SQLite implementation of ClientRepository."""

from typing import Optional

from ..interfaces.client_repository import IClientRepository
from ...domain.client import Client
from .connection import SQLiteConnection


class SQLiteClientRepository(IClientRepository):
    """SQLite implementation of client repository."""

    def __init__(self, connection: SQLiteConnection):
        self._conn = connection

    def get_by_id(self, client_id: str) -> Optional[Client]:
        """Gets a client by ID."""
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM clients WHERE id = ?", (client_id,))
            row = cursor.fetchone()
            return Client.from_dict(dict(row)) if row else None

    def get_by_whatsapp(self, whatsapp_number: str) -> Optional[Client]:
        """Gets a client by WhatsApp number."""
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM clients WHERE whatsapp_number = ?",
                (whatsapp_number,),
            )
            row = cursor.fetchone()
            return Client.from_dict(dict(row)) if row else None

    def get_by_email(self, email: str) -> Optional[Client]:
        """Gets a client by email."""
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM clients WHERE email = ?", (email,))
            row = cursor.fetchone()
            return Client.from_dict(dict(row)) if row else None

    def get_all_active(self) -> list[Client]:
        """Gets all active clients."""
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM clients WHERE is_active = 1")
            return [Client.from_dict(dict(row)) for row in cursor.fetchall()]
