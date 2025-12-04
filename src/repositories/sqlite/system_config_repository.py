"""SQLite implementation of SystemConfigRepository."""

from datetime import datetime
from typing import Optional

from ..interfaces.system_config_repository import ISystemConfigRepository
from ...domain.system_config import SystemConfig
from .connection import SQLiteConnection


class SQLiteSystemConfigRepository(ISystemConfigRepository):
    """SQLite implementation of system configuration repository."""

    def __init__(self, connection: SQLiteConnection):
        self._conn = connection

    def get(self, key: str) -> Optional[SystemConfig]:
        """Gets a configuration by key."""
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM system_config WHERE key = ?", (key,))
            row = cursor.fetchone()
            return SystemConfig.from_dict(dict(row)) if row else None

    def get_value(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Gets a configuration value by key, returns default if not found."""
        config = self.get(key)
        return config.value if config else default

    def get_all(self) -> list[SystemConfig]:
        """Gets all configuration entries."""
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM system_config ORDER BY key")
            return [SystemConfig.from_dict(dict(row)) for row in cursor.fetchall()]

    def set(
        self, key: str, value: str, description: Optional[str] = None
    ) -> SystemConfig:
        """Sets a configuration value (creates or updates)."""
        now = datetime.now()
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key FROM system_config WHERE key = ?", (key,))
            exists = cursor.fetchone()

            if exists:
                cursor.execute(
                    """UPDATE system_config
                       SET value = ?, description = COALESCE(?, description), updated_at = ?
                       WHERE key = ?""",
                    (value, description, now, key),
                )
            else:
                cursor.execute(
                    """INSERT INTO system_config (key, value, description, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?)""",
                    (key, value, description, now, now),
                )

        return SystemConfig(
            key=key,
            value=value,
            description=description,
            created_at=now if not exists else None,
            updated_at=now,
        )

    def delete(self, key: str) -> bool:
        """Deletes a configuration entry."""
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM system_config WHERE key = ?", (key,))
            return cursor.rowcount > 0
