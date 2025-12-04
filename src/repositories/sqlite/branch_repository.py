"""SQLite implementation of BranchRepository."""

from typing import Optional

from ..interfaces.branch_repository import IBranchRepository
from ...domain.branch import Branch
from .connection import SQLiteConnection


class SQLiteBranchRepository(IBranchRepository):
    """SQLite implementation of branch repository."""

    def __init__(self, connection: SQLiteConnection):
        self._conn = connection

    def get_by_id(self, branch_id: str) -> Optional[Branch]:
        """Gets a branch by ID."""
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM branches WHERE id = ?", (branch_id,))
            row = cursor.fetchone()
            return Branch.from_dict(dict(row)) if row else None

    def get_by_client(self, client_id: str) -> list[Branch]:
        """Gets all active branches for a client."""
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM branches WHERE client_id = ? AND is_active = 1",
                (client_id,),
            )
            return [Branch.from_dict(dict(row)) for row in cursor.fetchall()]

    def get_all_active(self, client_id: str) -> list[Branch]:
        """Gets all active branches for a client."""
        return self.get_by_client(client_id)
