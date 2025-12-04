"""
Calendar - Representa a un empleado y su Google Calendar
"""

from datetime import datetime, time
from typing import Optional
from pydantic import BaseModel, Field


class Calendar(BaseModel):
    """
    Calendar representa a un empleado y su Google Calendar vinculado.
    La disponibilidad se determina por eventos "mock_ai" en el calendario.
    """

    id: str = Field(..., description="UUID del calendario")
    branch_id: str = Field(..., description="ID de la sucursal")

    name: str = Field(..., description="Nombre del empleado/calendario")

    # Google Calendar
    google_calendar_id: str = Field(..., description="ID del calendario en Google")
    google_account_email: Optional[str] = Field(
        None, description="Email de la cuenta Google"
    )

    # El horario base ahora viene de los eventos "mock_ai" en Google Calendar
    # Estos campos son solo referencia/fallback
    default_start_time: time = Field(
        default=time(9, 0), description="Hora inicio por defecto"
    )
    default_end_time: time = Field(
        default=time(17, 0), description="Hora fin por defecto"
    )

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = Field(default=True)

    class Config:
        from_attributes = True


class CalendarService(BaseModel):
    """
    Relación muchos-a-muchos entre Calendar y Service.
    Un calendario puede atender múltiples servicios.
    Un servicio puede ser atendido por múltiples calendarios.
    """

    id: str = Field(..., description="UUID de la relación")
    calendar_id: str = Field(..., description="ID del calendario")
    service_id: str = Field(..., description="ID del servicio")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True
