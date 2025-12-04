"""SQLite implementation of CategoryRepository."""

from typing import Optional

from ..interfaces.category_repository import ICategoryRepository
from ...domain.category import Category
from .connection import SQLiteConnection


class SQLiteCategoryRepository(ICategoryRepository):
    """SQLite implementation of category repository."""

    def __init__(self, connection: SQLiteConnection):
        self._conn = connection

    def get_by_id(self, category_id: str) -> Optional[Category]:
        """Gets a category by ID."""
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM categories WHERE id = ?", (category_id,))
            row = cursor.fetchone()
            return Category.from_dict(dict(row)) if row else None

    def get_by_branch(self, branch_id: str) -> list[Category]:
        """Gets all active categories for a branch."""
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM categories
                   WHERE branch_id = ? AND is_active = 1
                   ORDER BY display_order""",
                (branch_id,),
            )
            return [Category.from_dict(dict(row)) for row in cursor.fetchall()]
