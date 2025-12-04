"""
Nivel 3: Memoria Total

Perfil persistente del usuario a través de todas las conversaciones.
Se almacena en LangGraph Store con namespace por usuario.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage
from langchain_core.language_models import BaseChatModel


class UserProfile(BaseModel):
    """
    Perfil persistente del usuario.
    Almacena información clave para personalizar el servicio.
    """

    # Identificación
    full_name: Optional[str] = Field(None, description="Nombre completo")
    identification_number: Optional[str] = Field(None, description="Número de cédula")
    phone_number: Optional[str] = Field(None, description="Número de WhatsApp")

    # Historial resumido
    total_appointments: int = Field(default=0, description="Total de citas agendadas")
    cancelled_appointments: int = Field(default=0, description="Citas canceladas")
    last_appointment_date: Optional[str] = Field(
        None, description="Fecha de última cita"
    )
    last_appointment_service: Optional[str] = Field(
        None, description="Servicio de última cita"
    )

    # Preferencias detectadas
    preferred_services: list[str] = Field(
        default_factory=list, description="Servicios más solicitados"
    )
    preferred_employees: list[str] = Field(
        default_factory=list, description="Empleados preferidos"
    )
    preferred_time_slots: list[str] = Field(
        default_factory=list, description="Horarios preferidos (mañana/tarde)"
    )
    preferred_branch: Optional[str] = Field(None, description="Sucursal preferida")

    # Notas
    notes: list[str] = Field(
        default_factory=list, description="Notas relevantes sobre el usuario"
    )

    # Metadata
    first_interaction: Optional[str] = Field(
        None, description="Fecha de primera interacción"
    )
    last_interaction: Optional[str] = Field(
        None, description="Fecha de última interacción"
    )

    def format_for_prompt(self) -> str:
        """Formatea el perfil para incluir en el prompt del agente"""
        parts = []

        if self.full_name:
            parts.append(f"Usuario conocido: {self.full_name}")
            if self.identification_number:
                parts.append(f"Cédula: {self.identification_number}")

        if self.total_appointments > 0:
            parts.append(f"Ha agendado {self.total_appointments} citas")
            if self.cancelled_appointments > 0:
                parts.append(f"({self.cancelled_appointments} canceladas)")

        if self.last_appointment_service:
            parts.append(
                f"Última cita: {self.last_appointment_service} ({self.last_appointment_date})"
            )

        if self.preferred_services:
            parts.append(
                f"Servicios frecuentes: {', '.join(self.preferred_services[:3])}"
            )

        if self.preferred_employees:
            parts.append(
                f"Empleados preferidos: {', '.join(self.preferred_employees[:2])}"
            )

        if self.preferred_time_slots:
            parts.append(f"Horarios preferidos: {', '.join(self.preferred_time_slots)}")

        if self.notes:
            parts.append(f"Notas: {'; '.join(self.notes[-2:])}")  # Últimas 2 notas

        return "\n".join(parts) if parts else "Usuario nuevo (primera interacción)"


PROFILE_EXTRACTION_PROMPT = """Analiza la siguiente conversación y extrae información relevante para el perfil del usuario.
Solo extrae información que fue explícitamente mencionada o demostrada.

Conversación:
{conversation}

Perfil actual del usuario:
{current_profile}

Responde en formato JSON con los campos que se deben actualizar:
- full_name: nombre si se mencionó
- preferred_services: servicios que solicitó o mostró interés
- preferred_employees: si mencionó preferencia por algún empleado
- preferred_time_slots: si mostró preferencia por horarios (ej: "mañana", "tarde", "específico como 10:00")
- notes: cualquier información relevante (máximo 1 nota nueva)

Solo incluye campos que tengan información nueva. Responde SOLO el JSON, nada más."""


class TotalMemory:
    """
    Gestiona la memoria total (perfil persistente) del usuario.

    - Se almacena en LangGraph Store por usuario
    - Se actualiza después de cada conversación significativa
    - Permite personalización del servicio
    """

    def __init__(self, llm: BaseChatModel):
        """
        Args:
            llm: Modelo de lenguaje para extracción de información
        """
        self.llm = llm

    async def extract_profile_updates(
        self, conversation_summary: str, current_profile: UserProfile
    ) -> dict:
        """
        Extrae actualizaciones del perfil desde una conversación.

        Args:
            conversation_summary: Resumen de la conversación
            current_profile: Perfil actual del usuario

        Returns:
            Diccionario con campos a actualizar
        """
        prompt = PROFILE_EXTRACTION_PROMPT.format(
            conversation=conversation_summary,
            current_profile=current_profile.model_dump_json(indent=2),
        )

        response = await self.llm.ainvoke([HumanMessage(content=prompt)])

        try:
            import json

            updates = json.loads(response.content)
            return updates
        except json.JSONDecodeError:
            return {}

    def update_profile(self, profile: UserProfile, updates: dict) -> UserProfile:
        """
        Aplica actualizaciones al perfil.

        Args:
            profile: Perfil actual
            updates: Diccionario con actualizaciones

        Returns:
            Perfil actualizado
        """
        # Crear copia del perfil
        data = profile.model_dump()

        # Aplicar actualizaciones
        for key, value in updates.items():
            if key in data:
                if isinstance(data[key], list) and isinstance(value, list):
                    # Combinar listas sin duplicados
                    existing = set(data[key])
                    for item in value:
                        if item not in existing:
                            data[key].append(item)
                elif isinstance(data[key], list) and isinstance(value, str):
                    # Agregar a lista si no existe
                    if value not in data[key]:
                        data[key].append(value)
                else:
                    data[key] = value

        # Actualizar timestamp
        data["last_interaction"] = datetime.now().isoformat()

        return UserProfile(**data)

    def update_after_appointment(
        self,
        profile: UserProfile,
        service_name: str,
        employee_name: str,
        appointment_date: str,
        appointment_time: str,
    ) -> UserProfile:
        """
        Actualiza el perfil después de crear una cita.

        Args:
            profile: Perfil actual
            service_name: Nombre del servicio
            employee_name: Nombre del empleado
            appointment_date: Fecha de la cita
            appointment_time: Hora de la cita

        Returns:
            Perfil actualizado
        """
        data = profile.model_dump()

        # Incrementar contador
        data["total_appointments"] = data.get("total_appointments", 0) + 1

        # Actualizar última cita
        data["last_appointment_date"] = appointment_date
        data["last_appointment_service"] = service_name

        # Agregar a preferencias si no existe
        if service_name not in data.get("preferred_services", []):
            data.setdefault("preferred_services", []).append(service_name)
            # Mantener solo los 5 más recientes
            data["preferred_services"] = data["preferred_services"][-5:]

        if employee_name not in data.get("preferred_employees", []):
            data.setdefault("preferred_employees", []).append(employee_name)
            data["preferred_employees"] = data["preferred_employees"][-3:]

        # Detectar preferencia de horario
        hour = int(appointment_time.split(":")[0])
        time_slot = "mañana" if hour < 12 else "tarde"
        if time_slot not in data.get("preferred_time_slots", []):
            data.setdefault("preferred_time_slots", []).append(time_slot)

        data["last_interaction"] = datetime.now().isoformat()

        return UserProfile(**data)

    def update_after_cancellation(self, profile: UserProfile) -> UserProfile:
        """Actualiza el perfil después de una cancelación"""
        data = profile.model_dump()
        data["cancelled_appointments"] = data.get("cancelled_appointments", 0) + 1
        data["last_interaction"] = datetime.now().isoformat()
        return UserProfile(**data)
