"""
User - Persona que agenda citas por WhatsApp
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class User(BaseModel):
    """
    Usuario es la persona que escribe al WhatsApp para agendar citas.
    Se identifica por su número de teléfono y cédula.
    """

    id: str = Field(..., description="UUID del usuario")
    client_id: str = Field(..., description="ID del cliente (negocio) al que pertenece")

    # Identificación
    phone_number: str = Field(..., description="Número de WhatsApp del usuario")
    identification_number: str = Field(..., description="Número de cédula")
    full_name: str = Field(..., description="Nombre completo")

    # Datos opcionales
    email: Optional[str] = Field(None)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_interaction_at: Optional[datetime] = Field(
        None, description="Última vez que escribió"
    )

    class Config:
        from_attributes = True
