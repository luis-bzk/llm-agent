"""Dependency injection container for repository access."""

from dataclasses import dataclass
from typing import Optional

from .repositories.interfaces.system_config_repository import ISystemConfigRepository
from .repositories.interfaces.client_repository import IClientRepository
from .repositories.interfaces.user_repository import IUserRepository
from .repositories.interfaces.branch_repository import IBranchRepository
from .repositories.interfaces.category_repository import ICategoryRepository
from .repositories.interfaces.service_repository import IServiceRepository
from .repositories.interfaces.calendar_repository import ICalendarRepository
from .repositories.interfaces.appointment_repository import IAppointmentRepository
from .repositories.interfaces.session_repository import ISessionRepository
from .repositories.interfaces.conversation_repository import IConversationRepository


@dataclass
class Container:
    """Holds all repository instances for dependency injection."""

    config: ISystemConfigRepository
    clients: IClientRepository
    users: IUserRepository
    branches: IBranchRepository
    categories: ICategoryRepository
    services: IServiceRepository
    calendars: ICalendarRepository
    appointments: IAppointmentRepository
    sessions: ISessionRepository
    conversations: IConversationRepository


_container: Optional[Container] = None


def get_container() -> Container:
    """Returns the global container instance.

    Raises:
        RuntimeError: If container has not been initialized.
    """
    if _container is None:
        raise RuntimeError(
            "Container not initialized. Call set_container() in the application entry point."
        )
    return _container


def set_container(container: Container) -> None:
    """Sets the global container instance.

    Args:
        container: Container with concrete repository implementations.
    """
    global _container
    _container = container


def reset_container() -> None:
    """Resets the global container. Useful for testing."""
    global _container
    _container = None
