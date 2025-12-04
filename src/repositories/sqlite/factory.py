"""Factory for creating Container with SQLite implementation."""

from ...container import Container
from .connection import SQLiteConnection
from .system_config_repository import SQLiteSystemConfigRepository
from .client_repository import SQLiteClientRepository
from .user_repository import SQLiteUserRepository
from .branch_repository import SQLiteBranchRepository
from .category_repository import SQLiteCategoryRepository
from .service_repository import SQLiteServiceRepository
from .calendar_repository import SQLiteCalendarRepository
from .appointment_repository import SQLiteAppointmentRepository
from .session_repository import SQLiteSessionRepository
from .conversation_repository import SQLiteConversationRepository


def create_sqlite_container(db_path: str = None) -> Container:
    """Creates a Container with SQLite repository implementations.

    Args:
        db_path: Path to database file. Uses default if not specified.

    Returns:
        Container: Configured with SQLite repositories.
    """
    connection = SQLiteConnection(db_path)

    return Container(
        config=SQLiteSystemConfigRepository(connection),
        clients=SQLiteClientRepository(connection),
        users=SQLiteUserRepository(connection),
        branches=SQLiteBranchRepository(connection),
        categories=SQLiteCategoryRepository(connection),
        services=SQLiteServiceRepository(connection),
        calendars=SQLiteCalendarRepository(connection),
        appointments=SQLiteAppointmentRepository(connection),
        sessions=SQLiteSessionRepository(connection),
        conversations=SQLiteConversationRepository(connection),
    )
