"""
Nivel 1: Memoria Corta

Almacena los últimos N mensajes de la conversación activa.
Cuando se alcanza el límite, activa la memoria larga (resumen).
"""

from typing import Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage


class ShortTermMemory:
    """
    Gestiona la memoria corta de la conversación.

    - Límite de 6 mensajes (3 intercambios usuario-asistente)
    - Cuando se excede, los mensajes antiguos se "gradúan" a memoria larga
    """

    MAX_MESSAGES = 6

    @staticmethod
    def get_recent_messages(messages: Sequence[BaseMessage]) -> list[BaseMessage]:
        """
        Obtiene los mensajes más recientes hasta el límite.

        IMPORTANTE: Preserva la integridad de los pares tool_call/tool_response.
        Los mensajes ToolMessage siempre deben estar precedidos por un AIMessage
        con tool_calls, de lo contrario OpenAI rechaza la petición.

        Args:
            messages: Lista completa de mensajes

        Returns:
            Últimos mensajes, asegurando que los pares tool estén completos
        """
        if len(messages) <= ShortTermMemory.MAX_MESSAGES:
            return list(messages)

        messages_list = list(messages)

        # Encontrar un punto de corte seguro
        # Empezamos desde el índice que daría MAX_MESSAGES
        start_idx = len(messages_list) - ShortTermMemory.MAX_MESSAGES

        # Retroceder si el primer mensaje sería un ToolMessage
        # ya que necesita su AIMessage con tool_calls previo
        while start_idx > 0 and isinstance(messages_list[start_idx], ToolMessage):
            start_idx -= 1

        return messages_list[start_idx:]

    @staticmethod
    def needs_summarization(messages: Sequence[BaseMessage]) -> bool:
        """
        Verifica si se necesita generar/actualizar el resumen.

        La lógica es:
        - Después de los primeros 6 mensajes, generar resumen
        - Cada 2 mensajes adicionales, actualizar resumen

        Args:
            messages: Lista completa de mensajes

        Returns:
            True si se necesita resumir
        """
        count = len(messages)

        # Primer resumen: justo después del mensaje 7
        if count == 7:
            return True

        # Actualizaciones: cada 2 mensajes después del 7
        if count > 7 and (count - 7) % 2 == 0:
            return True

        return False

    @staticmethod
    def get_messages_for_summarization(
        messages: Sequence[BaseMessage], existing_summary: str | None
    ) -> tuple[str | None, list[BaseMessage]]:
        """
        Obtiene los mensajes que necesitan ser resumidos.

        Si es el primer resumen (mensaje 7), resume los primeros 6.
        Si es una actualización, devuelve los 2 mensajes nuevos desde el último resumen.

        Args:
            messages: Lista completa de mensajes
            existing_summary: Resumen existente (None si es el primero)

        Returns:
            Tupla de (resumen_existente, mensajes_a_resumir)
        """
        count = len(messages)

        if count == 7:
            # Primer resumen: los primeros 6 mensajes
            return None, list(messages[:6])

        if count > 7 and existing_summary:
            # Actualización: los últimos 2 mensajes antes de los últimos 2
            # Es decir, mensajes [count-4:count-2]
            return existing_summary, list(messages[-4:-2])

        return existing_summary, []

    @staticmethod
    def format_context_with_summary(
        summary: str | None, recent_messages: list[BaseMessage]
    ) -> str:
        """
        Formatea el contexto combinando resumen y mensajes recientes.

        Args:
            summary: Resumen de la conversación (puede ser None)
            recent_messages: Mensajes recientes (últimos 2-3)

        Returns:
            Contexto formateado para el prompt
        """
        parts = []

        if summary:
            parts.append(f"[Resumen de la conversación anterior]\n{summary}")

        if recent_messages:
            parts.append("\n[Mensajes recientes]")
            for msg in recent_messages:
                role = "Usuario" if isinstance(msg, HumanMessage) else "Asistente"
                parts.append(f"{role}: {msg.content}")

        return "\n".join(parts)
