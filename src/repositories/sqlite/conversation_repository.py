"""SQLite implementation of ConversationRepository."""

import uuid
from datetime import datetime
from typing import Optional

from ..interfaces.conversation_repository import IConversationRepository
from ...domain.conversation import Conversation
from ...domain.message import Message
from .connection import SQLiteConnection


class SQLiteConversationRepository(IConversationRepository):
    """SQLite implementation of conversation repository."""

    def __init__(self, connection: SQLiteConnection):
        self._conn = connection

    def get_by_id(self, conversation_id: str) -> Optional[Conversation]:
        """Gets a conversation by ID."""
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
            )
            row = cursor.fetchone()
            return Conversation.from_dict(dict(row)) if row else None

    def get_active(
        self, session_id: str, timeout_hours: int = 2
    ) -> Optional[Conversation]:
        """Gets the active conversation for a session within timeout."""
        from datetime import timedelta

        cutoff_time = datetime.now() - timedelta(hours=timeout_hours)

        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM conversations
                   WHERE session_id = ? AND status = 'active'
                   AND last_message_at > ?
                   ORDER BY created_at DESC LIMIT 1""",
                (session_id, cutoff_time.isoformat()),
            )
            row = cursor.fetchone()
            return Conversation.from_dict(dict(row)) if row else None

    def create(self, session_id: str) -> Conversation:
        """Creates a new conversation."""
        now = datetime.now()
        conversation_id = str(uuid.uuid4())

        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO conversations (id, session_id, status, created_at, last_message_at)
                   VALUES (?, ?, 'active', ?, ?)""",
                (conversation_id, session_id, now, now),
            )

        return Conversation(
            id=conversation_id,
            session_id=session_id,
            status="active",
            message_count=0,
            created_at=now,
            last_message_at=now,
        )

    def update_summary(self, conversation_id: str, summary: str) -> None:
        """Updates the summary of a conversation."""
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE conversations
                   SET summary = ?, summary_updated_at = ?
                   WHERE id = ?""",
                (summary, datetime.now(), conversation_id),
            )

    def escalate(self, conversation_id: str, reason: str) -> None:
        """Escalates a conversation to human operator."""
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE conversations
                   SET escalated_to_chatwoot = 1, escalated_at = ?, escalation_reason = ?
                   WHERE id = ?""",
                (datetime.now(), reason, conversation_id),
            )

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        tool_call_id: Optional[str] = None,
        tool_name: Optional[str] = None,
    ) -> Message:
        """Adds a message to the conversation."""
        now = datetime.now()
        message_id = str(uuid.uuid4())

        with self._conn.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO messages (id, conversation_id, role, content, tool_call_id, tool_name, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    message_id,
                    conversation_id,
                    role,
                    content,
                    tool_call_id,
                    tool_name,
                    now,
                ),
            )
            cursor.execute(
                """UPDATE conversations
                   SET message_count = message_count + 1, last_message_at = ?
                   WHERE id = ?""",
                (now, conversation_id),
            )

        return Message(
            id=message_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            created_at=now,
        )

    def get_messages(
        self, conversation_id: str, limit: Optional[int] = None
    ) -> list[Message]:
        """Gets the messages of a conversation."""
        with self._conn.get_connection() as conn:
            cursor = conn.cursor()

            if limit:
                cursor.execute(
                    """SELECT * FROM messages
                       WHERE conversation_id = ?
                       ORDER BY created_at DESC LIMIT ?""",
                    (conversation_id, limit),
                )
                rows = cursor.fetchall()
                return [Message.from_dict(dict(row)) for row in reversed(rows)]
            else:
                cursor.execute(
                    """SELECT * FROM messages
                       WHERE conversation_id = ?
                       ORDER BY created_at""",
                    (conversation_id,),
                )
                return [Message.from_dict(dict(row)) for row in cursor.fetchall()]
