"""Tools for querying services and categories."""

from langchain_core.tools import tool
from ..container import get_container


@tool
def get_categories(branch_id: str) -> list[dict] | str:
    """Gets service categories available at a branch.

    Args:
        branch_id: Branch ID.

    Returns:
        List of categories with their services.
    """
    container = get_container()
    categories = container.categories.get_by_branch(branch_id)

    if not categories:
        return "No se encontraron categorías para esta sucursal."

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
    container = get_container()
    services = container.services.get_by_branch(branch_id)

    if not services:
        return "No se encontraron servicios para esta sucursal."

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
    container = get_container()
    service = container.services.find_by_name(branch_id, service_name)

    if not service:
        all_services = container.services.get_by_branch(branch_id)
        if all_services:
            names = [s.name for s in all_services]
            return f"No encontré el servicio '{service_name}'. Servicios disponibles: {', '.join(names)}"
        return f"No encontré el servicio '{service_name}'."

    calendars = container.calendars.get_for_service(service.id)

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
