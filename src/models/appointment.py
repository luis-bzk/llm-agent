"""
Appointment - Cita agendada
"""

from datetime import datetime, date, time
from decimal import Decimal
from typing import Optional, Literal
from pydantic import BaseModel, Field


AppointmentStatus = Literal[
    "scheduled", "confirmed", "completed", "cancelled", "no_show"
]


class Appointment(BaseModel):
    """
    Cita agendada con un empleado para un servicio específico.
    """

    id: str = Field(..., description="UUID de la cita")

    # Relaciones
    user_id: str = Field(..., description="ID del usuario que agenda")
    calendar_id: str = Field(..., description="ID del calendario/empleado")
    service_id: str = Field(..., description="ID del servicio")
    branch_id: str = Field(..., description="ID de la sucursal")

    # Snapshot del servicio (por si cambia después)
    service_name_snapshot: str = Field(
        ..., description="Nombre del servicio al momento de agendar"
    )
    service_price_snapshot: Decimal = Field(
        ..., description="Precio al momento de agendar"
    )
    service_duration_snapshot: int = Field(..., description="Duración en minutos")

    # Snapshot del empleado
    calendar_name_snapshot: str = Field(..., description="Nombre del empleado")

    # Fecha y hora
    appointment_date: date = Field(..., description="Fecha de la cita")
    start_time: time = Field(..., description="Hora de inicio")
    end_time: time = Field(..., description="Hora de fin")

    # Google Calendar
    google_event_id: Optional[str] = Field(
        None, description="ID del evento en Google Calendar"
    )

    # Estado
    status: AppointmentStatus = Field(default="scheduled")

    # Cancelación
    cancellation_reason: Optional[str] = Field(None)
    cancelled_at: Optional[datetime] = Field(None)
    cancelled_by: Optional[str] = Field(None, description="'user' o 'admin'")

    # Notas
    notes: Optional[str] = Field(None, description="Notas adicionales")

    # Recordatorio
    reminder_sent: bool = Field(default=False)
    reminder_sent_at: Optional[datetime] = Field(None)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True

    def format_datetime(self) -> str:
        """Formatea fecha y hora para mostrar"""
        return f"{self.appointment_date.strftime('%A %d de %B')} a las {self.start_time.strftime('%H:%M')}"
