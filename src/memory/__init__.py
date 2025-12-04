"""
Sistema de Memoria en 3 Niveles para mock_ai

Nivel 1 - Memoria Corta: Últimos 6 mensajes de la conversación activa
Nivel 2 - Memoria Larga: Resumen de la conversación generado por LLM
Nivel 3 - Memoria Total: Perfil persistente del usuario a través de todas las conversaciones
"""

from .short_term import ShortTermMemory
from .long_term import LongTermMemory
from .total import TotalMemory, UserProfile

__all__ = [
    "ShortTermMemory",
    "LongTermMemory",
    "TotalMemory",
    "UserProfile",
]
