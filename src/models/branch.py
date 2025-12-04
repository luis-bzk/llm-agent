"""
Sucursal - Ubicación física del negocio
"""

from datetime import datetime, time
from typing import Optional
from pydantic import BaseModel, Field


class Branch(BaseModel):
    """
    Sucursal es una ubicación física donde se presta el servicio.
    Un cliente puede tener múltiples sucursales.
    """

    id: str = Field(..., description="UUID de la sucursal")
    client_id: str = Field(..., description="ID del cliente dueño")

    name: str = Field(..., description="Nombre de la sucursal")
    address: str = Field(..., description="Dirección física")
    city: Optional[str] = Field(None, description="Ciudad")

    # Horario general del local (referencia, no restricción absoluta)
    opening_time: time = Field(default=time(9, 0), description="Hora de apertura")
    closing_time: time = Field(default=time(18, 0), description="Hora de cierre")
    working_days: str = Field(
        default="1,2,3,4,5",  # Lunes a Viernes
        description="Días laborables (1=Lunes, 7=Domingo)",
    )

    # Contacto
    phone: Optional[str] = Field(None, description="Teléfono de la sucursal")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = Field(default=True)

    class Config:
        from_attributes = True

    def get_working_days_list(self) -> list[int]:
        """Retorna lista de días laborables como enteros"""
        return [int(d) for d in self.working_days.split(",")]
