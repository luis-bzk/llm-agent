"""
Estado del Agente mock_ai

Define el estado que fluye a través del grafo.
Incluye mensajes, contexto de cliente, y metadatos de memoria.

IMPORTANTE: Este agente es STATELESS. La BD es la única fuente de verdad.
Cada invocación del grafo:
1. Recibe SOLO el mensaje nuevo del usuario
2. Carga contexto/historial de BD
3. Procesa y guarda resultados en BD
4. Retorna respuesta

El reducer personalizado `replace_or_add_messages` permite que `load_context`
REEMPLACE los mensajes (para reconstruir desde BD), mientras otros nodos
pueden agregar mensajes normalmente.
"""

from typing import Annotated, Optional, Sequence, Union
from langchain_core.messages import AnyMessage
from langgraph.graph import MessagesState, add_messages
from pydantic import BaseModel, Field


def replace_or_add_messages(
    left: Sequence[AnyMessage],
    right: Union[Sequence[AnyMessage], Sequence[tuple[str, str]]],
) -> Sequence[AnyMessage]:
    """
    Reducer personalizado para mensajes.

    - Si el primer mensaje tiene content "__REPLACE_MESSAGES__": reemplaza todo
    - De lo contrario: usa add_messages normal (append con deduplicación)

    Esto permite que load_context reemplace los mensajes con los de BD,
    mientras que assistant y tools agregan mensajes normalmente.
    """
    if right and len(right) > 0:
        first_msg = right[0]
        if (
            hasattr(first_msg, "content")
            and first_msg.content == "__REPLACE_MESSAGES__"
        ):
            return list(right[1:])

    return add_messages(left, right)


class InputState(BaseModel):
    """
    Estado de entrada para el grafo.

    Contiene solo lo necesario para iniciar una invocación:
    - messages: El mensaje nuevo del usuario
    - from_number: Número de WhatsApp del usuario
    - to_number: Número de WhatsApp del negocio

    IMPORTANTE: Usa el mismo reducer que MockAiState para evitar conflictos.
    """

    messages: Annotated[Sequence[AnyMessage], replace_or_add_messages] = Field(
        default_factory=list
    )
    from_number: str = ""
    to_number: str = ""

    class Config:
        arbitrary_types_allowed = True


class MockAiState(BaseModel):
    """
    Estado completo del agente mock_ai.

    Contiene toda la información necesaria para procesar una conversación.
    Se puebla en load_context con datos de BD.
    """

    # Mensajes con reducer que permite reemplazo
    messages: Annotated[Sequence[AnyMessage], replace_or_add_messages] = Field(
        default_factory=list
    )

    # Entrada (desde WhatsApp)
    from_number: str = ""
    to_number: str = ""

    # Contexto del cliente (negocio)
    client_id: str = ""
    branch_id: Optional[str] = None

    # Contexto del usuario
    user_phone: str = ""
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    user_cedula: Optional[str] = None

    # Session y conversación
    session_id: Optional[str] = None
    conversation_id: Optional[str] = None

    # Memoria
    conversation_summary: Optional[str] = None
    user_profile_json: Optional[str] = None

    # Flujo de agendación
    selected_service_id: Optional[str] = None
    selected_calendar_id: Optional[str] = None
    pending_appointment: Optional[dict] = None

    # Control
    needs_escalation: bool = False
    escalation_reason: Optional[str] = None

    # Tracking de mensajes guardados en BD
    saved_messages_count: int = 0

    class Config:
        arbitrary_types_allowed = True


class ConversationConfig(BaseModel):
    """
    Configuración de la conversación.
    Se pasa como configurable al invocar el grafo.
    """

    # Identificación
    client_id: str = Field(..., description="ID del cliente/negocio")
    user_phone: str = Field(..., description="Número de WhatsApp del usuario")

    # Opcional: sucursal específica (si el cliente tiene solo una)
    branch_id: Optional[str] = Field(default=None)

    # Configuración de timeout
    conversation_timeout_hours: int = Field(
        default=2, description="Horas para expirar conversación"
    )

    # Multi-modelo
    model_name: str = Field(default="gpt-4o-mini", description="Modelo a usar")

    class Config:
        extra = "allow"
