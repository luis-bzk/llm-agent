"""Environment variables configuration."""

import os


def get_agent_name() -> str:
    """Returns the agent/product name from environment variable."""
    return os.getenv("AGENT_NAME", "Assistant")
