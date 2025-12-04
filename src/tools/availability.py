"""
Tools para consultar disponibilidad de horarios
"""

from datetime import date, time, datetime, timedelta
from langchain_core.tools import tool
from ..db import get_db
from .calendar_integration import (
    get_calendar_client,
    calculate_available_slots,
    GoogleCalendarClient,
)


def _get_available_slots_for_calendar(
    calendar_id: str,
    google_calendar_id: str,
    target_date: date,
    duration_minutes: int,
    use_google: bool = True,
) -> list[time]:
    """
    Obtiene slots disponibles para un calendario específico.

    IMPORTANTE: Solo devuelve slots si hay eventos "mock_ai" que marquen disponibilidad.
    Si no hay eventos "mock_ai" para esa fecha, el empleado NO está disponible.

    Args:
        calendar_id: ID del calendario en BD
        google_calendar_id: ID del calendario en Google
        target_date: Fecha a consultar
        duration_minutes: Duración del servicio
        use_google: Si usar Google Calendar (default True)

    Returns:
        Lista de horarios disponibles (vacía si no hay disponibilidad)
    """
    db = get_db()

    if use_google and google_calendar_id:
        try:
            client = get_calendar_client()

            # Obtener bloques de disponibilidad (eventos "mock_ai")
            availability_blocks = client.get_mock_ai_availability(
                google_calendar_id, target_date
            )

            print(f"[DEBUG] Calendar {google_calendar_id} - Date {target_date}")
            print(f"[DEBUG] mock_ai availability blocks: {availability_blocks}")

            # Si NO hay eventos "mock_ai", el empleado NO está disponible ese día
            if not availability_blocks:
                print(f"[DEBUG] No mock_ai events found - employee not available")
                return []

            # Obtener slots ocupados (otros eventos)
            booked_slots = client.get_booked_slots(google_calendar_id, target_date)
            print(f"[DEBUG] Booked slots: {booked_slots}")

            return calculate_available_slots(
                availability_blocks, booked_slots, duration_minutes
            )

        except Exception as e:
            print(f"[ERROR] Error consultando Google Calendar: {e}")
            import traceback

            traceback.print_exc()
            # Si falla Google Calendar, NO usar fallback - mejor no mostrar disponibilidad
            return []

    # Si no hay google_calendar_id configurado, usar BD como fallback
    # Pero solo si hay citas registradas para validar que trabaja ese día
    calendar = db.get_calendar(calendar_id)
    if not calendar:
        return []

    # Usar horario por defecto SOLO como referencia
    availability_blocks = [
        (calendar["default_start_time"], calendar["default_end_time"])
    ]

    # Obtener citas existentes de la BD
    appointments = db.get_appointments_by_calendar_and_date(calendar_id, target_date)
    booked_slots = [(apt["start_time"], apt["end_time"]) for apt in appointments]

    return calculate_available_slots(
        availability_blocks, booked_slots, duration_minutes
    )


@tool
def get_available_slots(
    branch_id: str, service_name: str, target_date: str, calendar_name: str = None
) -> dict | str:
    """
    Obtiene los horarios disponibles para un servicio en una fecha específica.
    Consulta Google Calendar para verificar disponibilidad real.

    Args:
        branch_id: ID de la sucursal
        service_name: Nombre del servicio (puede ser parcial)
        target_date: Fecha en formato YYYY-MM-DD
        calendar_name: Nombre del empleado/calendario (opcional, si no se especifica muestra todos)

    Returns:
        Diccionario con slots disponibles por calendario
    """
    db = get_db()

    # Buscar servicio
    service = db.find_service_by_name(branch_id, service_name)
    if not service:
        all_services = db.get_services_by_branch(branch_id)
        if all_services:
            names = [s["name"] for s in all_services]
            return f"No encontré el servicio '{service_name}'. Disponibles: {', '.join(names)}"
        return f"No encontré el servicio '{service_name}'."

    # Parsear fecha
    try:
        parsed_date = date.fromisoformat(target_date)
    except ValueError:
        return f"Fecha inválida: {target_date}. Usa formato YYYY-MM-DD."

    # Verificar que la fecha no sea pasada
    today = date.today()
    if parsed_date < today:
        return "No puedo agendar en fechas pasadas. Por favor elige una fecha futura."

    # Verificar límite de días (booking_window)
    # Esto debería venir del cliente, por ahora usamos un valor por defecto
    max_days = 30
    if (parsed_date - today).days > max_days:
        return f"Solo puedo agendar dentro de los próximos {max_days} días."

    # Obtener calendarios que atienden este servicio
    calendars = db.get_calendars_for_service(service["id"])

    if not calendars:
        return f"No hay empleados asignados para '{service['name']}'."

    # Filtrar por nombre de calendario si se especifica
    if calendar_name:
        calendars = [c for c in calendars if calendar_name.lower() in c["name"].lower()]
        if not calendars:
            return (
                f"No encontré empleado con nombre '{calendar_name}' para este servicio."
            )

    # Obtener disponibilidad de cada calendario
    result = {
        "service": service["name"],
        "date": target_date,
        "duration_minutes": service["duration_minutes"],
        "price": float(service["price"]),
        "availability": [],
    }

    for calendar in calendars:
        slots = _get_available_slots_for_calendar(
            calendar["id"],
            calendar["google_calendar_id"],
            parsed_date,
            service["duration_minutes"],
            use_google=True,  # Intentar usar Google Calendar
        )

        if slots:
            result["availability"].append(
                {
                    "calendar_id": calendar["id"],
                    "calendar_name": calendar["name"],
                    "available_times": [s.strftime("%H:%M") for s in slots],
                }
            )

    if not result["availability"]:
        return f"No hay horarios disponibles para '{service['name']}' el {target_date}."

    return result


@tool
def get_calendar_availability(
    branch_id: str, calendar_name: str, target_date: str
) -> dict | str:
    """
    Obtiene la disponibilidad general de un empleado/calendario para una fecha.
    Útil cuando el usuario quiere saber cuándo trabaja un empleado específico.

    Args:
        branch_id: ID de la sucursal
        calendar_name: Nombre del empleado/calendario
        target_date: Fecha en formato YYYY-MM-DD

    Returns:
        Información de disponibilidad del calendario
    """
    db = get_db()

    # Buscar calendario
    calendar = db.find_calendar_by_name(branch_id, calendar_name)
    if not calendar:
        calendars = db.get_calendars_by_branch(branch_id)
        if calendars:
            names = [c["name"] for c in calendars]
            return f"No encontré a '{calendar_name}'. Empleados disponibles: {', '.join(names)}"
        return f"No encontré a '{calendar_name}'."

    # Parsear fecha
    try:
        parsed_date = date.fromisoformat(target_date)
    except ValueError:
        return f"Fecha inválida: {target_date}. Usa formato YYYY-MM-DD."

    # Intentar obtener disponibilidad de Google Calendar
    try:
        client = get_calendar_client()
        availability_blocks = client.get_mock_ai_availability(
            calendar["google_calendar_id"], parsed_date
        )
        booked_slots = client.get_booked_slots(
            calendar["google_calendar_id"], parsed_date
        )

        return {
            "calendar_name": calendar["name"],
            "date": target_date,
            "working_hours": [
                {"from": start.strftime("%H:%M"), "to": end.strftime("%H:%M")}
                for start, end in availability_blocks
            ],
            "booked_slots_count": len(booked_slots),
            "is_available": len(availability_blocks) > 0,
        }

    except Exception as e:
        # Fallback a horario por defecto
        return {
            "calendar_name": calendar["name"],
            "date": target_date,
            "working_hours": [
                {
                    "from": calendar["default_start_time"].strftime("%H:%M"),
                    "to": calendar["default_end_time"].strftime("%H:%M"),
                }
            ],
            "note": "Horario por defecto (no se pudo consultar Google Calendar)",
        }
