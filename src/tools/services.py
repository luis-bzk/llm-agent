"""Tools for querying services and categories."""

from langchain_core.tools import tool
from ..container import get_container
from ..config import logger as log


@tool
def get_categories(branch_id: str) -> list[dict] | str:
    """Gets service categories available at a branch.

    Args:
        branch_id: Branch ID.

    Returns:
        List of categories with their services.
    """
    log.info("services", "get_categories called", branch_id=branch_id)
    container = get_container()
    categories = container.categories.get_by_branch(branch_id)

    if not categories:
        log.warn("services", "No categories found", branch_id=branch_id)
        return "No se encontraron categorías para esta sucursal."

    log.debug("services", "Categories found", count=len(categories))
    result = []
    for cat in categories:
        services = container.services.get_by_category(cat.id)
        result.append(
            {
                "category_id": cat.id,
                "category_name": cat.name,
                "description": cat.description,
                "services_count": len(services),
                "services": [
                    {
                        "service_id": s.id,
                        "name": s.name,
                        "price": float(s.price),
                        "duration_minutes": s.duration_minutes,
                    }
                    for s in services
                ],
            }
        )

    return result


@tool
def get_services(branch_id: str) -> list[dict] | str:
    """Gets all services available at a branch with prices and duration.

    Args:
        branch_id: Branch ID.

    Returns:
        List of services with details.
    """
    log.info("services", "get_services called", branch_id=branch_id)
    container = get_container()
    services = container.services.get_by_branch(branch_id)

    if not services:
        log.warn("services", "No services found", branch_id=branch_id)
        return "No se encontraron servicios para esta sucursal."

    log.debug("services", "Services found", count=len(services))

    return [
        {
            "service_id": s.id,
            "name": s.name,
            "category": s.category_name or "Sin categoría",
            "price": float(s.price),
            "price_formatted": s.price_formatted,
            "duration_minutes": s.duration_minutes,
            "duration_formatted": s.duration_formatted,
            "description": s.description,
        }
        for s in services
    ]


@tool
def get_service_details(branch_id: str, service_name: str) -> dict | str:
    """Gets details of a specific service by name.

    Args:
        branch_id: Branch ID.
        service_name: Service name (can be partial).

    Returns:
        Service details or error message.
    """
    log.info("services", "get_service_details called", branch_id=branch_id, service_name=service_name)
    container = get_container()
    service = container.services.find_by_name(branch_id, service_name)

    if not service:
        log.warn("services", "Service not found", service_name=service_name)
        all_services = container.services.get_by_branch(branch_id)
        if all_services:
            names = [s.name for s in all_services]
            return f"No encontré el servicio '{service_name}'. Servicios disponibles: {', '.join(names)}"
        return f"No encontré el servicio '{service_name}'."

    log.debug("services", "Service found", service_id=service.id, duration=service.duration_minutes)
    calendars = container.calendars.get_for_service(service.id)
    log.debug("services", "Available calendars", count=len(calendars))

    return {
        "service_id": service.id,
        "name": service.name,
        "description": service.description,
        "price": float(service.price),
        "price_formatted": service.price_formatted,
        "duration_minutes": service.duration_minutes,
        "duration_formatted": service.duration_formatted,
        "available_with": [{"calendar_id": c.id, "name": c.name} for c in calendars],
    }
