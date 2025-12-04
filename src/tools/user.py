"""
Tools para gestión de usuarios
"""

import uuid
from datetime import datetime
from langchain_core.tools import tool
from ..db import get_db


@tool
def find_or_create_user(
    client_id: str, phone_number: str, identification_number: str, full_name: str
) -> dict:
    """
    Busca un usuario por cédula. Si no existe, lo crea.
    Usa esta herramienta cuando el usuario proporcione su nombre y cédula.

    Args:
        client_id: ID del cliente (negocio)
        phone_number: Número de WhatsApp del usuario
        identification_number: Número de cédula
        full_name: Nombre completo del usuario

    Returns:
        Datos del usuario (existente o recién creado)
    """
    db = get_db()

    # Buscar por cédula
    existing = db.get_user_by_identification(client_id, identification_number)

    if existing:
        return {
            "user_id": existing["id"],
            "full_name": existing["full_name"],
            "identification_number": existing["identification_number"],
            "phone_number": existing["phone_number"],
            "is_new": False,
            "message": f"Usuario encontrado: {existing['full_name']}. IMPORTANTE: Usa user_id='{existing['id']}' para create_appointment (NO uses client_id).",
        }

    # Crear nuevo usuario
    user_id = str(uuid.uuid4())
    new_user = db.create_user(
        {
            "id": user_id,
            "client_id": client_id,
            "phone_number": phone_number,
            "identification_number": identification_number,
            "full_name": full_name,
        }
    )

    return {
        "user_id": new_user["id"],
        "full_name": new_user["full_name"],
        "identification_number": new_user["identification_number"],
        "phone_number": new_user["phone_number"],
        "is_new": True,
        "message": f"Usuario registrado: {new_user['full_name']}. IMPORTANTE: Usa user_id='{new_user['id']}' para create_appointment (NO uses client_id).",
    }


@tool
def get_user_info(client_id: str, identification_number: str) -> dict | str:
    """
    Obtiene información de un usuario por su cédula.
    Incluye historial de citas si existe.

    Args:
        client_id: ID del cliente (negocio)
        identification_number: Número de cédula

    Returns:
        Información del usuario con historial de citas
    """
    db = get_db()

    user = db.get_user_by_identification(client_id, identification_number)
    if not user:
        return f"No se encontró usuario con cédula {identification_number}"

    # Obtener citas
    appointments = db.get_appointments_by_user(user["id"])

    # Separar en pasadas y futuras
    today = datetime.now().date()
    upcoming = []
    past = []

    for apt in appointments:
        apt_info = {
            "appointment_id": apt["id"],
            "service": apt["service_name_snapshot"],
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
            "employee": apt["calendar_name_snapshot"],
            "status": apt["status"],
        }

        apt_date = (
            apt["appointment_date"]
            if hasattr(apt["appointment_date"], "isoformat")
            else datetime.strptime(apt["appointment_date"], "%Y-%m-%d").date()
        )

        if apt_date >= today and apt["status"] == "scheduled":
            upcoming.append(apt_info)
        else:
            past.append(apt_info)

    return {
        "user_id": user["id"],
        "full_name": user["full_name"],
        "identification_number": user["identification_number"],
        "phone_number": user["phone_number"],
        "upcoming_appointments": upcoming,
        "past_appointments": past[:5],  # Últimas 5 citas pasadas
        "total_appointments": len(appointments),
    }
