"""System configuration keys."""


class ConfigKeys:
    """Keys for system configuration values stored in database."""

    # AI Model configuration
    AI_MODEL = "ai_model"
    AI_TEMPERATURE = "ai_temperature"
    AI_MAX_TOKENS = "ai_max_tokens"

    # Memory configuration
    SUMMARY_MESSAGE_THRESHOLD = "summary_message_threshold"
    CONVERSATION_TIMEOUT_HOURS = "conversation_timeout_hours"
    MAX_MESSAGES_IN_CONTEXT = "max_messages_in_context"

    # Booking configuration
    DEFAULT_BOOKING_WINDOW_DAYS = "default_booking_window_days"
    DEFAULT_SLOT_INTERVAL_MINUTES = "default_slot_interval_minutes"

    # System limits
    MAX_TOOL_RETRIES = "max_tool_retries"


class ConfigDefaults:
    """Default values for system configuration."""

    AI_MODEL = "gpt-4o-mini"
    AI_TEMPERATURE = "0.7"
    AI_MAX_TOKENS = "1024"

    SUMMARY_MESSAGE_THRESHOLD = "10"
    CONVERSATION_TIMEOUT_HOURS = "2"
    MAX_MESSAGES_IN_CONTEXT = "20"

    DEFAULT_BOOKING_WINDOW_DAYS = "30"
    DEFAULT_SLOT_INTERVAL_MINUTES = "15"

    MAX_TOOL_RETRIES = "3"
