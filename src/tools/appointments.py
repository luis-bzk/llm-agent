"""
Tools para gestión de citas
"""

import uuid
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from langchain_core.tools import tool
from ..db import get_db
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
    """
    Crea una cita para un usuario. Verifica disponibilidad antes de crear.
    Esta es la herramienta FINAL para confirmar una cita.

    IMPORTANTE: El user_id debe ser el ID del USUARIO obtenido de find_or_create_user,
    NO confundir con client_id que es el ID del negocio.

    Args:
        user_id: ID del USUARIO (el valor 'user_id' retornado por find_or_create_user, NO es client_id)
        branch_id: ID de la sucursal
        service_name: Nombre del servicio
        calendar_name: Nombre del empleado/calendario
        appointment_date: Fecha en formato YYYY-MM-DD
        appointment_time: Hora en formato HH:MM

    Returns:
        Detalles de la cita creada o mensaje de error
    """
    db = get_db()

    # VALIDACIÓN CRÍTICA: Verificar que user_id es un usuario válido, NO un client_id
    user = db.get_user(user_id)
    if not user:
        # Verificar si por error se pasó un client_id
        client = db.get_client(user_id)
        if client:
            return (
                f"ERROR: Pasaste client_id='{user_id}' en lugar de user_id. "
                f"Debes usar el 'user_id' retornado por find_or_create_user, NO el client_id. "
                f"Primero llama a find_or_create_user para obtener el user_id correcto."
            )
        return f"ERROR: No existe usuario con id='{user_id}'. Primero usa find_or_create_user para registrar al usuario."

    # Buscar servicio
    service = db.find_service_by_name(branch_id, service_name)
    if not service:
        return f"No encontré el servicio '{service_name}'."

    # Buscar calendario
    calendar = db.find_calendar_by_name(branch_id, calendar_name)
    if not calendar:
        return f"No encontré al empleado '{calendar_name}'."

    # Parsear fecha y hora
    try:
        apt_date = date.fromisoformat(appointment_date)
        apt_time = time.fromisoformat(appointment_time)
    except ValueError as e:
        return f"Formato de fecha/hora inválido: {e}"

    # Calcular hora de fin
    duration = service["duration_minutes"]
    start_datetime = datetime.combine(apt_date, apt_time)
    end_datetime = start_datetime + timedelta(minutes=duration)
    apt_end_time = end_datetime.time()

    # VERIFICACIÓN DE DISPONIBILIDAD EN TIEMPO REAL
    available_slots = _get_available_slots_for_calendar(
        calendar["id"],
        calendar["google_calendar_id"],
        apt_date,
        duration,
        use_google=True,
    )

    if apt_time not in available_slots:
        # Sugerir alternativas
        if available_slots:
            alternatives = [s.strftime("%H:%M") for s in available_slots[:5]]
            return (
                f"Lo siento, {appointment_time} no está disponible. "
                f"Horarios disponibles: {', '.join(alternatives)}"
            )
        return (
            f"No hay horarios disponibles para {appointment_date} con {calendar_name}."
        )

    # Crear evento en Google Calendar
    google_event_id = None
    try:
        calendar_client = get_calendar_client()

        # Usar datos del usuario (ya validado al inicio)
        user_name = user.get("full_name", "Usuario")
        user_cedula = user.get("identification_number", "")
        event_summary = f"{service['name']} - {user_name} ({user_cedula})"
        event_description = (
            f"Cita agendada via mock_ai\n"
            f"Cliente: {user_name}\n"
            f"Cédula: {user_cedula}\n"
            f"Teléfono: {user.get('phone_number', 'N/A')}"
        )

        google_event_id = calendar_client.create_appointment_event(
            calendar["google_calendar_id"],
            event_summary,
            start_datetime,
            end_datetime,
            event_description,
        )
    except Exception as e:
        print(f"Warning: No se pudo crear evento en Google Calendar: {e}")
        # Continuamos sin Google Calendar (solo BD local)

    # Crear cita en BD
    appointment_id = str(uuid.uuid4())
    appointment_data = {
        "id": appointment_id,
        "user_id": user_id,
        "calendar_id": calendar["id"],
        "service_id": service["id"],
        "branch_id": branch_id,
        "service_name_snapshot": service["name"],
        "service_price_snapshot": service["price"],
        "service_duration_snapshot": duration,
        "calendar_name_snapshot": calendar["name"],
        "appointment_date": apt_date,
        "start_time": apt_time,
        "end_time": apt_end_time,
        "google_event_id": google_event_id,
        "status": "scheduled",
    }

    db.create_appointment(appointment_data)

    # Obtener sucursal para la dirección
    branch = db.get_branch(branch_id)

    return {
        "success": True,
        "appointment_id": appointment_id,
        "message": "¡Cita confirmada!",
        "details": {
            "service": service["name"],
            "employee": calendar["name"],
            "date": apt_date.strftime("%A %d de %B"),
            "time": apt_time.strftime("%H:%M"),
            "duration": f"{duration} minutos",
            "price": f"${float(service['price']):.2f}",
            "location": f"{branch['name']} - {branch['address']}",
        },
        "reminder": "Te enviaré un recordatorio antes de tu cita.",
    }


@tool
def get_user_appointments(user_id: str) -> dict | str:
    """
    Obtiene las citas de un usuario.
    Útil para verificar citas existentes antes de agendar o modificar.

    Args:
        user_id: ID del usuario

    Returns:
        Lista de citas del usuario
    """
    db = get_db()

    upcoming = db.get_upcoming_appointments_by_user(user_id)

    if not upcoming:
        return "No tienes citas programadas."

    return {
        "upcoming_appointments": [
            {
                "appointment_id": apt["id"],
                "service": apt["service_name_snapshot"],
                "employee": apt["calendar_name_snapshot"],
                "date": (
                    apt["appointment_date"].isoformat()
                    if hasattr(apt["appointment_date"], "isoformat")
                    else apt["appointment_date"]
                ),
                "time": (
                    apt["start_time"].strftime("%H:%M")
                    if hasattr(apt["start_time"], "strftime")
                    else apt["start_time"]
                ),
                "status": apt["status"],
            }
            for apt in upcoming
        ],
        "count": len(upcoming),
    }


@tool
def cancel_appointment(appointment_id: str, reason: str) -> dict | str:
    """
    Cancela una cita existente.

    Args:
        appointment_id: ID de la cita a cancelar
        reason: Motivo de la cancelación

    Returns:
        Confirmación de cancelación
    """
    db = get_db()

    # Verificar que existe
    appointment = db.get_appointment(appointment_id)
    if not appointment:
        return f"No se encontró la cita {appointment_id}."

    if appointment["status"] == "cancelled":
        return "Esta cita ya fue cancelada anteriormente."

    # Eliminar evento de Google Calendar si existe
    if appointment.get("google_event_id"):
        try:
            calendar = db.get_calendar(appointment["calendar_id"])
            client = get_calendar_client()
            client.delete_event(
                calendar["google_calendar_id"], appointment["google_event_id"]
            )
        except Exception as e:
            print(f"Warning: No se pudo eliminar evento de Google Calendar: {e}")

    # Cancelar en BD
    db.cancel_appointment(appointment_id, reason, "user")

    return {
        "success": True,
        "message": "Cita cancelada correctamente.",
        "cancelled_appointment": {
            "service": appointment["service_name_snapshot"],
            "date": (
                appointment["appointment_date"].isoformat()
                if hasattr(appointment["appointment_date"], "isoformat")
                else appointment["appointment_date"]
            ),
            "time": (
                appointment["start_time"].strftime("%H:%M")
                if hasattr(appointment["start_time"], "strftime")
                else appointment["start_time"]
            ),
            "reason": reason,
        },
    }


@tool
def reschedule_appointment(
    appointment_id: str, new_date: str, new_time: str
) -> dict | str:
    """
    Reagenda una cita existente a una nueva fecha y hora.

    Args:
        appointment_id: ID de la cita a reagendar
        new_date: Nueva fecha en formato YYYY-MM-DD
        new_time: Nueva hora en formato HH:MM

    Returns:
        Confirmación de reagendamiento
    """
    db = get_db()

    # Obtener cita actual
    appointment = db.get_appointment(appointment_id)
    if not appointment:
        return f"No se encontró la cita {appointment_id}."

    if appointment["status"] != "scheduled":
        return "Solo se pueden reagendar citas activas."

    # Parsear nueva fecha/hora
    try:
        apt_date = date.fromisoformat(new_date)
        apt_time = time.fromisoformat(new_time)
    except ValueError as e:
        return f"Formato de fecha/hora inválido: {e}"

    # Verificar disponibilidad
    calendar = db.get_calendar(appointment["calendar_id"])
    duration = appointment["service_duration_snapshot"]

    available_slots = _get_available_slots_for_calendar(
        calendar["id"],
        calendar["google_calendar_id"],
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

    # Calcular nueva hora de fin
    start_datetime = datetime.combine(apt_date, apt_time)
    end_datetime = start_datetime + timedelta(minutes=duration)

    # Actualizar en Google Calendar
    if appointment.get("google_event_id"):
        try:
            # Por simplicidad, eliminamos y recreamos
            client = get_calendar_client()
            client.delete_event(
                calendar["google_calendar_id"], appointment["google_event_id"]
            )

            # Obtener datos del usuario para el título del evento
            user = db.get_user(appointment["user_id"])
            if user:
                user_name = user.get("full_name", "Usuario")
                user_cedula = user.get("identification_number", "")
                event_summary = f"{appointment['service_name_snapshot']} - {user_name} ({user_cedula}) [Reagendada]"
                event_description = (
                    f"Cita reagendada via mock_ai\n"
                    f"Cliente: {user_name}\n"
                    f"Cédula: {user_cedula}\n"
                    f"Teléfono: {user.get('phone_number', 'N/A')}"
                )
            else:
                event_summary = f"{appointment['service_name_snapshot']} - Cita (reagendada)"
                event_description = "Cita reagendada via mock_ai"

            new_event_id = client.create_appointment_event(
                calendar["google_calendar_id"],
                event_summary,
                start_datetime,
                end_datetime,
                event_description,
            )
        except Exception as e:
            print(f"Warning: Error actualizando Google Calendar: {e}")
            new_event_id = None
    else:
        new_event_id = None

    # Actualizar en BD
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE appointments
               SET appointment_date = ?, start_time = ?, end_time = ?,
                   google_event_id = ?, updated_at = ?
               WHERE id = ?""",
            (
                apt_date,
                apt_time,
                end_datetime.time(),
                new_event_id,
                datetime.now(),
                appointment_id,
            ),
        )

    return {
        "success": True,
        "message": "Cita reagendada correctamente.",
        "new_appointment": {
            "service": appointment["service_name_snapshot"],
            "employee": appointment["calendar_name_snapshot"],
            "date": apt_date.strftime("%A %d de %B"),
            "time": apt_time.strftime("%H:%M"),
        },
        "previous": {
            "date": (
                appointment["appointment_date"].isoformat()
                if hasattr(appointment["appointment_date"], "isoformat")
                else appointment["appointment_date"]
            ),
            "time": (
                appointment["start_time"].strftime("%H:%M")
                if hasattr(appointment["start_time"], "strftime")
                else appointment["start_time"]
            ),
        },
    }
