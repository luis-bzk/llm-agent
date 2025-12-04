"""
Conversation, Session y Message - Gestión de conversaciones
"""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


MessageRole = Literal["user", "assistant", "system", "tool"]
ConversationStatus = Literal["active", "expired", "escalated"]


class Message(BaseModel):
    """
    Mensaje individual en una conversación.
    """

    id: str = Field(..., description="UUID del mensaje")
    conversation_id: str = Field(..., description="ID de la conversación")

    role: MessageRole = Field(..., description="Rol del mensaje")
    content: str = Field(..., description="Contenido del mensaje")

    # Para mensajes de tool
    tool_call_id: Optional[str] = Field(None)
    tool_name: Optional[str] = Field(None)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True


class Conversation(BaseModel):
    """
    Conversación es un conjunto de mensajes durante un periodo.
    Se crea una nueva si pasa más de X horas desde el último mensaje.
    """

    id: str = Field(..., description="UUID de la conversación")
    session_id: str = Field(..., description="ID de la sesión WhatsApp")

    # Estado
    status: ConversationStatus = Field(default="active")

    # Escalamiento a Chatwoot
    escalated_to_chatwoot: bool = Field(default=False)
    escalated_at: Optional[datetime] = Field(None)
    escalation_reason: Optional[str] = Field(None)

    # Memoria larga (resumen de la conversación)
    summary: Optional[str] = Field(None, description="Resumen generado por LLM")
    summary_updated_at: Optional[datetime] = Field(None)

    # Contadores
    message_count: int = Field(default=0)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    last_message_at: datetime = Field(default_factory=datetime.now)
    expired_at: Optional[datetime] = Field(None)

    class Config:
        from_attributes = True


class Session(BaseModel):
    """
    Sesión agrupa todas las conversaciones de un número de WhatsApp.
    También llamado "WhatsApp Chat" en el documento.
    """

    id: str = Field(..., description="UUID de la sesión")
    client_id: str = Field(..., description="ID del cliente (negocio)")
    user_id: Optional[str] = Field(
        None, description="ID del usuario si está identificado"
    )

    # Identificación
    phone_number: str = Field(..., description="Número de WhatsApp")

    # Memoria total (perfil persistente del usuario)
    # Esto se guarda en el LangGraph Store, aquí solo referencia
    memory_profile_key: Optional[str] = Field(
        None, description="Key en el Store para el perfil"
    )

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    last_activity_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True
