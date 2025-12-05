"""Tools for querying schedule availability."""

from datetime import date, time, datetime, timedelta
from langchain_core.tools import tool
from ..container import get_container
from ..config import logger as log
from ..constants.config_keys import ConfigKeys, ConfigDefaults
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
    """Gets available slots for a specific calendar.

    Only returns slots if there are "mock_ai" events marking availability.
    If no "mock_ai" events exist for that date, the employee is NOT available.

    Args:
        calendar_id: Calendar ID in database.
        google_calendar_id: Calendar ID in Google.
        target_date: Date to query.
        duration_minutes: Service duration.
        use_google: Whether to use Google Calendar (default True).

    Returns:
        List of available times (empty if no availability).
    """
    container = get_container()

    if use_google and google_calendar_id:
        try:
            client = get_calendar_client()

            availability_blocks = client.get_mock_ai_availability(
                google_calendar_id, target_date
            )

            log.debug("availability", "Checking calendar", calendar_id=google_calendar_id, date=target_date, blocks=availability_blocks)

            if not availability_blocks:
                log.debug("availability", "No mock_ai events - employee not available")
                return []

            booked_slots = client.get_booked_slots(google_calendar_id, target_date)
            log.debug("availability", "Booked slots", count=len(booked_slots), slots=booked_slots)

            return calculate_available_slots(
                availability_blocks, booked_slots, duration_minutes
            )

        except Exception as e:
            log.error("availability", "Error consultando Google Calendar", error=str(e))
            return []

    calendar = container.calendars.get_by_id(calendar_id)
    if not calendar:
        return []

    availability_blocks = [(calendar.default_start_time, calendar.default_end_time)]

    appointments = container.appointments.get_by_calendar_and_date(
        calendar_id, target_date
    )
    booked_slots = [(apt.start_time, apt.end_time) for apt in appointments]

    return calculate_available_slots(
        availability_blocks, booked_slots, duration_minutes
    )


@tool
def get_available_slots(
    branch_id: str, service_name: str, target_date: str, calendar_name: str = None
) -> dict | str:
    """Gets available times for a service on a specific date.

    Args:
        branch_id: Branch ID.
        service_name: Service name (can be partial).
        target_date: Date in YYYY-MM-DD format.
        calendar_name: Employee/calendar name (optional).

    Returns:
        Dictionary with available slots per calendar.
    """
    container = get_container()

    service = container.services.find_by_name(branch_id, service_name)
    if not service:
        all_services = container.services.get_by_branch(branch_id)
        if all_services:
            names = [s.name for s in all_services]
            return f"No encontré el servicio '{service_name}'. Disponibles: {', '.join(names)}"
        return f"No encontré el servicio '{service_name}'."

    try:
        parsed_date = date.fromisoformat(target_date)
    except ValueError:
        return f"Fecha inválida: {target_date}. Usa formato YYYY-MM-DD."

    today = date.today()
    if parsed_date < today:
        return "No puedo agendar en fechas pasadas. Por favor elige una fecha futura."

    max_days = int(container.config.get_value(
        ConfigKeys.DEFAULT_BOOKING_WINDOW_DAYS,
        ConfigDefaults.DEFAULT_BOOKING_WINDOW_DAYS
    ))
    if (parsed_date - today).days > max_days:
        return f"Solo puedo agendar dentro de los próximos {max_days} días."

    calendars = container.calendars.get_for_service(service.id)

    if not calendars:
        return f"No hay empleados asignados para '{service.name}'."

    if calendar_name:
        calendars = [c for c in calendars if calendar_name.lower() in c.name.lower()]
        if not calendars:
            return (
                f"No encontré empleado con nombre '{calendar_name}' para este servicio."
            )

    result = {
        "service": service.name,
        "date": target_date,
        "duration_minutes": service.duration_minutes,
        "price": float(service.price),
        "availability": [],
    }

    for calendar in calendars:
        log.debug("availability", "Processing calendar", name=calendar.name, calendar_id=calendar.id, google_id=calendar.google_calendar_id, duration=service.duration_minutes)

        slots = _get_available_slots_for_calendar(
            calendar.id,
            calendar.google_calendar_id,
            parsed_date,
            service.duration_minutes,
            use_google=True,
        )

        log.debug("availability", f"Returned {len(slots)} slots", sample=[s.strftime('%H:%M') for s in slots[:5]] if slots else [])

        if slots:
            result["availability"].append(
                {
                    "calendar_id": calendar.id,
                    "calendar_name": calendar.name,
                    "available_times": [s.strftime("%H:%M") for s in slots],
                }
            )

    if not result["availability"]:
        return f"No hay horarios disponibles para '{service.name}' el {target_date}."

    return result


@tool
def get_calendar_availability(
    branch_id: str, calendar_name: str, target_date: str
) -> dict | str:
    """Gets general availability of an employee/calendar for a date.

    Args:
        branch_id: Branch ID.
        calendar_name: Employee/calendar name.
        target_date: Date in YYYY-MM-DD format.

    Returns:
        Calendar availability information.
    """
    container = get_container()

    calendar = container.calendars.find_by_name(branch_id, calendar_name)
    if not calendar:
        calendars = container.calendars.get_by_branch(branch_id)
        if calendars:
            names = [c.name for c in calendars]
            return f"No encontré a '{calendar_name}'. Empleados disponibles: {', '.join(names)}"
        return f"No encontré a '{calendar_name}'."

    try:
        parsed_date = date.fromisoformat(target_date)
    except ValueError:
        return f"Fecha inválida: {target_date}. Usa formato YYYY-MM-DD."

    try:
        client = get_calendar_client()
        availability_blocks = client.get_mock_ai_availability(
            calendar.google_calendar_id, parsed_date
        )
        booked_slots = client.get_booked_slots(calendar.google_calendar_id, parsed_date)

        return {
            "calendar_name": calendar.name,
            "date": target_date,
            "working_hours": [
                {"from": start.strftime("%H:%M"), "to": end.strftime("%H:%M")}
                for start, end in availability_blocks
            ],
            "booked_slots_count": len(booked_slots),
            "is_available": len(availability_blocks) > 0,
        }

    except Exception as e:
        return {
            "calendar_name": calendar.name,
            "date": target_date,
            "working_hours": [
                {
                    "from": calendar.default_start_time.strftime("%H:%M"),
                    "to": calendar.default_end_time.strftime("%H:%M"),
                }
            ],
            "note": "Horario por defecto (no se pudo consultar Google Calendar)",
        }
