"""Tools for appointment management."""

import uuid
from datetime import datetime, date, time, timedelta
from langchain_core.tools import tool
from ..container import get_container
from ..config import logger as log
from ..config.env import get_agent_name
from ..constants.appointment_types import AppointmentType
from .calendar_integration import get_calendar_client
from .availability import _get_available_slots_for_calendar


@tool
def create_appointment(
    user_id: str,
    branch_id: str,
    service_name: str,
    calendar_name: str,
    appointment_date: str,
    appointment_time: str,
) -> dict | str:
    """Creates an appointment for a user. Verifies availability before creating.

    The user_id must be the USER ID obtained from find_or_create_user,
    NOT to be confused with client_id which is the business ID.

    Args:
        user_id: USER ID (the 'user_id' value returned by find_or_create_user, NOT client_id).
        branch_id: Branch ID.
        service_name: Service name.
        calendar_name: Employee/calendar name.
        appointment_date: Date in YYYY-MM-DD format.
        appointment_time: Time in HH:MM format.

    Returns:
        Created appointment details or error message.
    """
    container = get_container()

    user = container.users.get_by_id(user_id)
    if not user:
        client = container.clients.get_by_id(user_id)
        if client:
            return (
                f"ERROR: Pasaste client_id='{user_id}' en lugar de user_id. "
                f"Debes usar el 'user_id' retornado por find_or_create_user, NO el client_id. "
                f"Primero llama a find_or_create_user para obtener el user_id correcto."
            )
        return f"ERROR: No existe usuario con id='{user_id}'. Primero usa find_or_create_user para registrar al usuario."

    service = container.services.find_by_name(branch_id, service_name)
    if not service:
        return f"No encontré el servicio '{service_name}'."

    calendar = container.calendars.find_by_name(branch_id, calendar_name)
    if not calendar:
        return f"No encontré al empleado '{calendar_name}'."

    try:
        apt_date = date.fromisoformat(appointment_date)
        apt_time = time.fromisoformat(appointment_time)
    except ValueError as e:
        return f"Formato de fecha/hora inválido: {e}"

    duration = service.duration_minutes
    start_datetime = datetime.combine(apt_date, apt_time)
    end_datetime = start_datetime + timedelta(minutes=duration)
    apt_end_time = end_datetime.time()

    available_slots = _get_available_slots_for_calendar(
        calendar.id,
        calendar.google_calendar_id,
        apt_date,
        duration,
        use_google=True,
    )

    if apt_time not in available_slots:
        if available_slots:
            alternatives = [s.strftime("%H:%M") for s in available_slots[:5]]
            return (
                f"Lo siento, {appointment_time} no está disponible. "
                f"Horarios disponibles: {', '.join(alternatives)}"
            )
        return (
            f"No hay horarios disponibles para {appointment_date} con {calendar_name}."
        )

    # Get client to check appointment type
    client = container.clients.get_by_whatsapp(user.phone_number)
    is_virtual = client and client.appointment_type == AppointmentType.VIRTUAL

    google_event_id = None
    google_meet_link = None
    try:
        calendar_client = get_calendar_client()

        user_name = user.full_name or "Usuario"
        user_cedula = user.identification_number or ""
        event_summary = f"{service.name} - {user_name} ({user_cedula})"
        event_description = (
            f"Cita agendada via {get_agent_name()}\n"
            f"Cliente: {user_name}\n"
            f"Cédula: {user_cedula}\n"
            f"Teléfono: {user.phone_number or 'N/A'}"
        )

        google_event_id, google_meet_link = calendar_client.create_appointment_event(
            calendar.google_calendar_id,
            event_summary,
            start_datetime,
            end_datetime,
            event_description,
            include_meet_link=is_virtual,
        )

        # Add meet link to description if virtual
        if google_meet_link:
            event_description += f"\n\nEnlace Google Meet: {google_meet_link}"
    except Exception as e:
        log.warn(
            "appointments", "No se pudo crear evento en Google Calendar", error=str(e)
        )

    from ..domain.appointment import Appointment

    appointment = Appointment(
        id=str(uuid.uuid4()),
        user_id=user_id,
        calendar_id=calendar.id,
        service_id=service.id,
        branch_id=branch_id,
        service_name_snapshot=service.name,
        service_price_snapshot=service.price,
        service_duration_snapshot=duration,
        calendar_name_snapshot=calendar.name,
        appointment_date=apt_date,
        start_time=apt_time,
        end_time=apt_end_time,
        google_event_id=google_event_id,
        google_meet_link=google_meet_link,
        status="scheduled",
    )

    container.appointments.create(appointment)

    branch = container.branches.get_by_id(branch_id)

    result = {
        "success": True,
        "appointment_id": appointment.id,
        "message": "¡Cita confirmada!",
        "details": {
            "service": service.name,
            "employee": calendar.name,
            "date": apt_date.strftime("%A %d de %B"),
            "time": apt_time.strftime("%H:%M"),
            "duration": f"{duration} minutos",
            "price": f"${float(service.price):.2f}",
        },
        "reminder": "Te enviaré un recordatorio antes de tu cita.",
    }

    # Add location or meet link based on appointment type
    if google_meet_link:
        result["details"]["google_meet_link"] = google_meet_link
        result["details"]["type"] = "virtual"
    else:
        result["details"]["location"] = (
            f"{branch.name} - {branch.address}" if branch else "N/A"
        )
        result["details"]["type"] = "presencial"

    return result


@tool
def get_user_appointments(user_id: str) -> dict | str:
    """Gets appointments for a user.

    Args:
        user_id: User ID.

    Returns:
        List of user appointments.
    """
    container = get_container()

    upcoming = container.appointments.get_upcoming_by_user(user_id)

    if not upcoming:
        return "No tienes citas programadas."

    return {
        "upcoming_appointments": [
            {
                "appointment_id": apt.id,
                "service": apt.service_name_snapshot,
                "employee": apt.calendar_name_snapshot,
                "date": (
                    apt.appointment_date.isoformat()
                    if hasattr(apt.appointment_date, "isoformat")
                    else apt.appointment_date
                ),
                "time": (
                    apt.start_time.strftime("%H:%M")
                    if hasattr(apt.start_time, "strftime")
                    else apt.start_time
                ),
                "status": apt.status,
            }
            for apt in upcoming
        ],
        "count": len(upcoming),
    }


@tool
def cancel_appointment(appointment_id: str, reason: str) -> dict | str:
    """Cancels an existing appointment.

    Args:
        appointment_id: ID of appointment to cancel.
        reason: Cancellation reason.

    Returns:
        Cancellation confirmation.
    """
    container = get_container()

    appointment = container.appointments.get_by_id(appointment_id)
    if not appointment:
        return f"No se encontró la cita {appointment_id}."

    if appointment.status == "cancelled":
        return "Esta cita ya fue cancelada anteriormente."

    if appointment.google_event_id:
        try:
            calendar = container.calendars.get_by_id(appointment.calendar_id)
            client = get_calendar_client()
            client.delete_event(
                calendar.google_calendar_id, appointment.google_event_id
            )
        except Exception as e:
            log.warn(
                "appointments",
                "No se pudo eliminar evento de Google Calendar",
                error=str(e),
            )

    container.appointments.cancel(appointment_id, reason, "user")

    return {
        "success": True,
        "message": "Cita cancelada correctamente.",
        "cancelled_appointment": {
            "service": appointment.service_name_snapshot,
            "date": (
                appointment.appointment_date.isoformat()
                if hasattr(appointment.appointment_date, "isoformat")
                else appointment.appointment_date
            ),
            "time": (
                appointment.start_time.strftime("%H:%M")
                if hasattr(appointment.start_time, "strftime")
                else appointment.start_time
            ),
            "reason": reason,
        },
    }


@tool
def reschedule_appointment(
    appointment_id: str, new_date: str, new_time: str
) -> dict | str:
    """Reschedules an existing appointment to a new date and time.

    Args:
        appointment_id: ID of appointment to reschedule.
        new_date: New date in YYYY-MM-DD format.
        new_time: New time in HH:MM format.

    Returns:
        Reschedule confirmation.
    """
    container = get_container()

    appointment = container.appointments.get_by_id(appointment_id)
    if not appointment:
        return f"No se encontró la cita {appointment_id}."

    if appointment.status != "scheduled":
        return "Solo se pueden reagendar citas activas."

    try:
        apt_date = date.fromisoformat(new_date)
        apt_time = time.fromisoformat(new_time)
    except ValueError as e:
        return f"Formato de fecha/hora inválido: {e}"

    calendar = container.calendars.get_by_id(appointment.calendar_id)
    duration = appointment.service_duration_snapshot

    available_slots = _get_available_slots_for_calendar(
        calendar.id,
        calendar.google_calendar_id,
        apt_date,
        duration,
        use_google=True,
    )

    if apt_time not in available_slots:
        if available_slots:
            alternatives = [s.strftime("%H:%M") for s in available_slots[:5]]
            return (
                f"Lo siento, {new_time} no está disponible. "
                f"Horarios disponibles: {', '.join(alternatives)}"
            )
        return f"No hay horarios disponibles para {new_date}."

    start_datetime = datetime.combine(apt_date, apt_time)
    end_datetime = start_datetime + timedelta(minutes=duration)

    new_event_id = None
    if appointment.google_event_id:
        try:
            client = get_calendar_client()
            client.delete_event(
                calendar.google_calendar_id, appointment.google_event_id
            )

            user = container.users.get_by_id(appointment.user_id)
            if user:
                user_name = user.full_name or "Usuario"
                user_cedula = user.identification_number or ""
                event_summary = f"{appointment.service_name_snapshot} - {user_name} ({user_cedula}) [Reagendada]"
                event_description = (
                    f"Cita reagendada via {get_agent_name()}\n"
                    f"Cliente: {user_name}\n"
                    f"Cédula: {user_cedula}\n"
                    f"Teléfono: {user.phone_number or 'N/A'}"
                )
            else:
                event_summary = (
                    f"{appointment.service_name_snapshot} - Cita (reagendada)"
                )
                event_description = f"Cita reagendada via {get_agent_name()}"

            new_event_id, _ = client.create_appointment_event(
                calendar.google_calendar_id,
                event_summary,
                start_datetime,
                end_datetime,
                event_description,
            )
        except Exception as e:
            log.warn("appointments", "Error actualizando Google Calendar", error=str(e))
            new_event_id = None

    container.appointments.reschedule(
        appointment_id, apt_date, apt_time, end_datetime.time(), new_event_id
    )

    return {
        "success": True,
        "message": "Cita reagendada correctamente.",
        "new_appointment": {
            "service": appointment.service_name_snapshot,
            "employee": appointment.calendar_name_snapshot,
            "date": apt_date.strftime("%A %d de %B"),
            "time": apt_time.strftime("%H:%M"),
        },
        "previous": {
            "date": (
                appointment.appointment_date.isoformat()
                if hasattr(appointment.appointment_date, "isoformat")
                else appointment.appointment_date
            ),
            "time": (
                appointment.start_time.strftime("%H:%M")
                if hasattr(appointment.start_time, "strftime")
                else appointment.start_time
            ),
        },
    }
