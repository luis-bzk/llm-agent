"""
Tools para consultar servicios y categorías
"""

from langchain_core.tools import tool
from ..db import get_db


@tool
def get_categories(branch_id: str) -> list[dict] | str:
    """
    Obtiene las categorías de servicios disponibles en una sucursal.

    Args:
        branch_id: ID de la sucursal

    Returns:
        Lista de categorías con sus servicios
    """
    db = get_db()
    categories = db.get_categories_by_branch(branch_id)

    if not categories:
        return "No se encontraron categorías para esta sucursal."

    result = []
    for cat in categories:
        services = db.get_services_by_category(cat["id"])
        result.append(
            {
                "category_id": cat["id"],
                "category_name": cat["name"],
                "description": cat.get("description"),
                "services_count": len(services),
                "services": [
                    {
                        "service_id": s["id"],
                        "name": s["name"],
                        "price": float(s["price"]),
                        "duration_minutes": s["duration_minutes"],
                    }
                    for s in services
                ],
            }
        )

    return result


@tool
def get_services(branch_id: str) -> list[dict] | str:
    """
    Obtiene todos los servicios disponibles en una sucursal con precios y duración.
    Usa esta herramienta cuando el usuario pregunte qué servicios hay disponibles.

    Args:
        branch_id: ID de la sucursal

    Returns:
        Lista de servicios con detalles
    """
    db = get_db()
    services = db.get_services_by_branch(branch_id)

    if not services:
        return "No se encontraron servicios para esta sucursal."

    return [
        {
            "service_id": s["id"],
            "name": s["name"],
            "category": s.get("category_name", "Sin categoría"),
            "price": float(s["price"]),
            "price_formatted": f"${float(s['price']):.2f}",
            "duration_minutes": s["duration_minutes"],
            "duration_formatted": f"{s['duration_minutes']} min",
            "description": s.get("description"),
        }
        for s in services
    ]


@tool
def get_service_details(branch_id: str, service_name: str) -> dict | str:
    """
    Obtiene los detalles de un servicio específico por nombre.
    Usa esta herramienta cuando el usuario pregunte por un servicio en particular.

    Args:
        branch_id: ID de la sucursal
        service_name: Nombre del servicio (puede ser parcial)

    Returns:
        Detalles del servicio o mensaje de error
    """
    db = get_db()
    service = db.find_service_by_name(branch_id, service_name)

    if not service:
        # Sugerir servicios disponibles
        all_services = db.get_services_by_branch(branch_id)
        if all_services:
            names = [s["name"] for s in all_services]
            return f"No encontré el servicio '{service_name}'. Servicios disponibles: {', '.join(names)}"
        return f"No encontré el servicio '{service_name}'."

    # Obtener calendarios que atienden este servicio
    calendars = db.get_calendars_for_service(service["id"])

    return {
        "service_id": service["id"],
        "name": service["name"],
        "description": service.get("description"),
        "price": float(service["price"]),
        "price_formatted": f"${float(service['price']):.2f}",
        "duration_minutes": service["duration_minutes"],
        "duration_formatted": f"{service['duration_minutes']} min",
        "available_with": [
            {"calendar_id": c["id"], "name": c["name"]} for c in calendars
        ],
    }
