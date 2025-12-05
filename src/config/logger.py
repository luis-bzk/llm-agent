"""Centralized logger for mock_ai agent."""

import os
from datetime import datetime
from typing import Any

from rich.console import Console

console = Console()

LEVELS = {"debug": 10, "info": 20, "warn": 30, "error": 40}
_current_level = LEVELS.get(os.getenv("LOG_LEVEL", "debug").lower(), 10)


def _should_log(level: str) -> bool:
    return LEVELS.get(level, 0) >= _current_level


def _format_value(value: Any, max_length: int = 150) -> str:
    if value is None:
        return "None"
    s = str(value)
    if len(s) > max_length:
        return s[:max_length] + "..."
    return s


def log(level: str, context: str, message: str, **data):
    if not _should_log(level):
        return

    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    colors = {"debug": "dim", "info": "cyan", "warn": "yellow", "error": "red bold"}
    color = colors.get(level, "white")
    level_str = level.upper().ljust(5)

    data_str = ""
    if data:
        parts = [f"{k}={_format_value(v)}" for k, v in data.items()]
        data_str = " | " + ", ".join(parts)

    console.print(
        f"[dim]{timestamp}[/dim] [{color}]{level_str}[/{color}] "
        f"[blue][{context}][/blue] {message}{data_str}"
    )


def debug(context: str, message: str, **data):
    log("debug", context, message, **data)


def info(context: str, message: str, **data):
    log("info", context, message, **data)


def warn(context: str, message: str, **data):
    log("warn", context, message, **data)


def error(context: str, message: str, **data):
    log("error", context, message, **data)
