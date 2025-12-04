"""
Categoría y Servicio - Tipos de atención ofrecida
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class Category(BaseModel):
    """
    Categoría agrupa servicios relacionados.
    Ejemplo: "Servicios Dentales", "Consultas Generales"
    """

    id: str = Field(..., description="UUID de la categoría")
    branch_id: str = Field(..., description="ID de la sucursal")

    name: str = Field(..., description="Nombre de la categoría")
    description: Optional[str] = Field(None, description="Descripción")
    display_order: int = Field(default=0, description="Orden de display")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = Field(default=True)

    class Config:
        from_attributes = True


class Service(BaseModel):
    """
    Servicio es el tipo de atención que se ofrece.
    Tiene precio, duración y puede ser atendido por múltiples calendarios.
    """

    id: str = Field(..., description="UUID del servicio")
    category_id: str = Field(..., description="ID de la categoría")
    branch_id: str = Field(..., description="ID de la sucursal (denormalizado)")

    name: str = Field(..., description="Nombre del servicio")
    description: Optional[str] = Field(None, description="Descripción")
    price: Decimal = Field(..., description="Precio del servicio")
    duration_minutes: int = Field(..., description="Duración en minutos")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    is_active: bool = Field(default=True)

    class Config:
        from_attributes = True

    def format_price(self) -> str:
        """Formatea el precio para mostrar"""
        return f"${self.price:.2f}"

    def format_duration(self) -> str:
        """Formatea la duración para mostrar"""
        if self.duration_minutes >= 60:
            hours = self.duration_minutes // 60
            mins = self.duration_minutes % 60
            if mins:
                return f"{hours}h {mins}min"
            return f"{hours}h"
        return f"{self.duration_minutes} min"
