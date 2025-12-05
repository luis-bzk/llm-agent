"""Client entity - represents a business in the system."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ..constants.appointment_types import AppointmentType


@dataclass
class Client:
    """A client is a business that uses the scheduling system."""

    id: str
    email: str
    business_name: str
    owner_name: str
    phone: Optional[str] = None
    plan_id: Optional[str] = None
    max_branches: int = 1
    max_calendars: int = 1
    max_appointments_monthly: int = 50
    booking_window_days: int = 7
    bot_name: str = "Asistente"
    greeting_message: Optional[str] = None
    whatsapp_number: Optional[str] = None
    appointment_type: str = AppointmentType.PRESENCIAL
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_active: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "Client":
        """Creates a Client from a dictionary."""
        return cls(
            id=data["id"],
            email=data["email"],
            business_name=data["business_name"],
            owner_name=data["owner_name"],
            phone=data.get("phone"),
            plan_id=data.get("plan_id"),
            max_branches=data.get("max_branches", 1),
            max_calendars=data.get("max_calendars", 1),
            max_appointments_monthly=data.get("max_appointments_monthly", 50),
            booking_window_days=data.get("booking_window_days", 7),
            bot_name=data.get("bot_name", "Asistente"),
            greeting_message=data.get("greeting_message"),
            whatsapp_number=data.get("whatsapp_number"),
            appointment_type=data.get("appointment_type", AppointmentType.PRESENCIAL),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            is_active=bool(data.get("is_active", 1)),
        )

    def to_dict(self) -> dict:
        """Converts to dictionary."""
        return {
            "id": self.id,
            "email": self.email,
            "business_name": self.business_name,
            "owner_name": self.owner_name,
            "phone": self.phone,
            "plan_id": self.plan_id,
            "max_branches": self.max_branches,
            "max_calendars": self.max_calendars,
            "max_appointments_monthly": self.max_appointments_monthly,
            "booking_window_days": self.booking_window_days,
            "bot_name": self.bot_name,
            "greeting_message": self.greeting_message,
            "whatsapp_number": self.whatsapp_number,
            "appointment_type": self.appointment_type,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "is_active": self.is_active,
        }
