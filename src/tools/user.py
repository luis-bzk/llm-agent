"""Tools for user management."""

import uuid
from datetime import datetime
from langchain_core.tools import tool
from ..container import get_container
from ..domain.user import User


@tool
def find_or_create_user(
    client_id: str, phone_number: str, identification_number: str, full_name: str
) -> dict:
    """Finds a user by ID number. If not found, creates one.

    Args:
        client_id: Client ID (business).
        phone_number: User's WhatsApp number.
        identification_number: ID number.
        full_name: User's full name.

    Returns:
        User data (existing or newly created).
    """
    container = get_container()

    existing = container.users.get_by_identification(client_id, identification_number)

    if existing:
        return {
            "user_id": existing.id,
            "full_name": existing.full_name,
            "identification_number": existing.identification_number,
            "phone_number": existing.phone_number,
            "is_new": False,
            "message": f"Usuario encontrado: {existing.full_name}. IMPORTANTE: Usa user_id='{existing.id}' para create_appointment (NO uses client_id).",
        }

    user_id = str(uuid.uuid4())
    new_user = User(
        id=user_id,
        client_id=client_id,
        phone_number=phone_number,
        identification_number=identification_number,
        full_name=full_name,
    )
    container.users.create(new_user)

    return {
        "user_id": new_user.id,
        "full_name": new_user.full_name,
        "identification_number": new_user.identification_number,
        "phone_number": new_user.phone_number,
        "is_new": True,
        "message": f"Usuario registrado: {new_user.full_name}. IMPORTANTE: Usa user_id='{new_user.id}' para create_appointment (NO uses client_id).",
    }


@tool
def get_user_info(client_id: str, identification_number: str) -> dict | str:
    """Gets user information by ID number.

    Args:
        client_id: Client ID (business).
        identification_number: ID number.

    Returns:
        User information with appointment history.
    """
    container = get_container()

    user = container.users.get_by_identification(client_id, identification_number)
    if not user:
        return f"No se encontró usuario con cédula {identification_number}"

    appointments = container.appointments.get_by_user(user.id)

    today = datetime.now().date()
    upcoming = []
    past = []

    for apt in appointments:
        apt_info = {
            "appointment_id": apt.id,
            "service": apt.service_name_snapshot,
            "date": apt.appointment_date.isoformat(),
            "time": apt.start_time.strftime("%H:%M"),
            "employee": apt.calendar_name_snapshot,
            "status": apt.status,
        }

        if apt.appointment_date >= today and apt.status == "scheduled":
            upcoming.append(apt_info)
        else:
            past.append(apt_info)

    return {
        "user_id": user.id,
        "full_name": user.full_name,
        "identification_number": user.identification_number,
        "phone_number": user.phone_number,
        "upcoming_appointments": upcoming,
        "past_appointments": past[:5],
        "total_appointments": len(appointments),
    }
