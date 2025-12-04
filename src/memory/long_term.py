"""
Nivel 2: Memoria Larga

Genera y actualiza resúmenes de la conversación usando LLM.
Se activa cuando la memoria corta excede el límite.
"""

from typing import Sequence
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.language_models import BaseChatModel


SUMMARIZATION_PROMPT = """Resume la siguiente conversación capturando:
- Identidad del usuario (nombre, cédula si se mencionó)
- Intención principal del usuario
- Decisiones tomadas hasta ahora
- Contexto relevante para continuar la conversación

Conversación a resumir:
{messages}

Resumen (máximo 3-4 oraciones):"""


UPDATE_SUMMARY_PROMPT = """Tienes un resumen previo de la conversación y nuevos mensajes.
Actualiza el resumen incorporando la información nueva.

Resumen previo:
{previous_summary}

Nuevos mensajes:
{new_messages}

Resumen actualizado (máximo 3-4 oraciones):"""


class LongTermMemory:
    """
    Gestiona la memoria larga mediante resúmenes de conversación.

    - Genera resumen inicial después de 6 mensajes
    - Actualiza el resumen cada 2 mensajes adicionales
    - Usa LLM para generar resúmenes contextuales
    """

    def __init__(self, llm: BaseChatModel):
        """
        Args:
            llm: Modelo de lenguaje para generar resúmenes
        """
        self.llm = llm

    def _format_messages(self, messages: Sequence[BaseMessage]) -> str:
        """Formatea mensajes para el prompt de resumen"""
        formatted = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                formatted.append(f"Usuario: {msg.content}")
            elif isinstance(msg, AIMessage):
                # Ignorar mensajes de tool calls para el resumen
                if msg.content and not msg.tool_calls:
                    formatted.append(f"Asistente: {msg.content}")
        return "\n".join(formatted)

    async def generate_summary(self, messages: Sequence[BaseMessage]) -> str:
        """
        Genera un resumen inicial de los mensajes.

        Args:
            messages: Mensajes a resumir (típicamente los primeros 6)

        Returns:
            Resumen de la conversación
        """
        formatted_messages = self._format_messages(messages)
        prompt = SUMMARIZATION_PROMPT.format(messages=formatted_messages)

        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        return response.content

    async def update_summary(
        self, previous_summary: str, new_messages: Sequence[BaseMessage]
    ) -> str:
        """
        Actualiza un resumen existente con nuevos mensajes.

        Args:
            previous_summary: Resumen previo
            new_messages: Nuevos mensajes a incorporar

        Returns:
            Resumen actualizado
        """
        formatted_messages = self._format_messages(new_messages)
        prompt = UPDATE_SUMMARY_PROMPT.format(
            previous_summary=previous_summary, new_messages=formatted_messages
        )

        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        return response.content

    def generate_summary_sync(self, messages: Sequence[BaseMessage]) -> str:
        """Versión síncrona de generate_summary"""
        formatted_messages = self._format_messages(messages)
        prompt = SUMMARIZATION_PROMPT.format(messages=formatted_messages)

        response = self.llm.invoke([HumanMessage(content=prompt)])
        return response.content

    def update_summary_sync(
        self, previous_summary: str, new_messages: Sequence[BaseMessage]
    ) -> str:
        """Versión síncrona de update_summary"""
        formatted_messages = self._format_messages(new_messages)
        prompt = UPDATE_SUMMARY_PROMPT.format(
            previous_summary=previous_summary, new_messages=formatted_messages
        )

        response = self.llm.invoke([HumanMessage(content=prompt)])
        return response.content
