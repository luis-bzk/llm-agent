"""
Tool wrapper para calendar_integration
Este archivo solo re-exporta get_calendar_availability para el __init__
"""

from .availability import get_calendar_availability

__all__ = ["get_calendar_availability"]
