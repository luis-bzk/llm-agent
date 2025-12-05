"""SQLite implementation of BranchRepository."""

from typing import Optional

from ..interfaces.branch_repository import IBranchRepository
from ...domain.branch import Branch
from ...config import logger as log
from .connection import SQLiteConnection


class SQLiteBranchRepository(IBranchRepository):
    """SQLite implementation of branch repository."""

    def __init__(self, connection: SQLiteConnection):
        self._conn = connection

    def get_by_id(self, branch_id: str) -> Optional[Branch]:
        """Gets a branch by ID."""
        log.debug("repo.branch", "get_by_id", branch_id=branch_id)
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM branches WHERE id = ?", (branch_id,))
            row = cursor.fetchone()
            result = Branch.from_dict(dict(row)) if row else None
            log.debug(
                "repo.branch",
                "get_by_id result",
                found=result is not None,
                name=result.name if result else None,
                address=result.address if result else None,
            )
            return result

    def get_by_client(self, client_id: str) -> list[Branch]:
        """Gets all active branches for a client."""
        log.debug("repo.branch", "get_by_client", client_id=client_id)
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM branches WHERE client_id = ? AND is_active = 1",
                (client_id,),
            )
            results = [Branch.from_dict(dict(row)) for row in cursor.fetchall()]
            log.debug("repo.branch", "get_by_client result", count=len(results))
            return results

    def get_all_active(self, client_id: str) -> list[Branch]:
        """Gets all active branches for a client."""
        log.debug("repo.branch", "get_all_active", client_id=client_id)
        return self.get_by_client(client_id)
