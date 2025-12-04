"""
Cliente - Dueño del negocio que contrata mock_ai
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Client(BaseModel):
    """
    Cliente es la persona o empresa que contrata el servicio mock_ai.
    Puede tener múltiples sucursales y empleados.
    """

    id: str = Field(..., description="UUID del cliente")
    email: str = Field(..., description="Email del cliente")
    business_name: str = Field(..., description="Nombre del negocio")
    owner_name: str = Field(..., description="Nombre del dueño")
    phone: Optional[str] = Field(None, description="Teléfono de contacto")

    # Configuración del plan
    plan_id: Optional[str] = Field(None, description="ID del plan de Stripe")
    max_branches: int = Field(default=1, description="Máximo de sucursales permitidas")
    max_calendars: int = Field(default=1, description="Máximo de calendarios/empleados")
    max_appointments_monthly: int = Field(
        default=50, description="Máximo de citas mensuales"
    )
    booking_window_days: int = Field(
        default=7, description="Días hacia adelante para agendar"
    )

    # Configuración del bot
    bot_name: str = Field(default="mock_ai", description="Nombre del asistente")
    greeting_message: Optional[str] = Field(None, description="Saludo personalizado")

    # WhatsApp
    whatsapp_number: Optional[str] = Field(
        None, description="Número de WhatsApp Business"
    )

    # Modelo AI preferido
    ai_model: str = Field(default="gpt-4o-mini", description="Modelo AI a usar")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = Field(default=True)

    class Config:
        from_attributes = True
