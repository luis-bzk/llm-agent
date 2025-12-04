"""
State definitions for the mock_ai agent graph.

The agent is stateless - the database is the single source of truth.
Each graph invocation receives a new user message, loads context from DB,
processes it, saves results to DB, and returns a response.

The custom reducer `replace_or_add_messages` allows load_context to replace
messages (reconstructing from DB), while other nodes append normally.
"""

from typing import Annotated, Optional, Sequence, Union
from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from pydantic import BaseModel, Field

from .constants.config_keys import ConfigDefaults


def replace_or_add_messages(
    left: Sequence[AnyMessage],
    right: Union[Sequence[AnyMessage], Sequence[tuple[str, str]]],
) -> Sequence[AnyMessage]:
    """
    Custom reducer for messages.

    If the first message has content "__REPLACE_MESSAGES__", replaces all messages.
    Otherwise, uses the standard add_messages reducer (append with deduplication).
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
    """Input state for the graph - contains only what's needed to start an invocation."""

    messages: Annotated[Sequence[AnyMessage], replace_or_add_messages] = Field(
        default_factory=list
    )
    from_number: str = ""
    to_number: str = ""

    class Config:
        arbitrary_types_allowed = True


class MockAiState(BaseModel):
    """Full agent state - populated in load_context with data from DB."""

    messages: Annotated[Sequence[AnyMessage], replace_or_add_messages] = Field(
        default_factory=list
    )

    from_number: str = ""
    to_number: str = ""

    client_id: str = ""
    branch_id: Optional[str] = None

    user_phone: str = ""
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    user_cedula: Optional[str] = None

    session_id: Optional[str] = None
    conversation_id: Optional[str] = None

    conversation_summary: Optional[str] = None
    memory_profile_json: Optional[str] = None

    selected_service_id: Optional[str] = None
    selected_calendar_id: Optional[str] = None
    pending_appointment: Optional[dict] = None

    needs_escalation: bool = False
    escalation_reason: Optional[str] = None

    saved_messages_count: int = 0

    class Config:
        arbitrary_types_allowed = True


class ConversationConfig(BaseModel):
    """Conversation configuration passed as configurable when invoking the graph."""

    client_id: str = Field(..., description="Client/business ID")
    user_phone: str = Field(..., description="User's WhatsApp number")
    branch_id: Optional[str] = Field(default=None)
    conversation_timeout_hours: int = Field(default=int(ConfigDefaults.CONVERSATION_TIMEOUT_HOURS))
    model_name: Optional[str] = Field(default=None, description="Model override")

    class Config:
        extra = "allow"
