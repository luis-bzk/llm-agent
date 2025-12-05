"""Main LangGraph agent for appointment scheduling."""

import json
from dataclasses import dataclass
from typing import Literal

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from .state import AgentState, InputState
from .prompts import get_system_prompt
from .container import get_container
from .domain.message import Message
from .config import logger as log
from .config.env import get_agent_name
from .constants.config_keys import ConfigKeys, ConfigDefaults
from .tools.services import get_services, get_categories, get_service_details
from .tools.availability import get_available_slots
from .tools.user import find_or_create_user, get_user_info
from .tools.appointments import (
    create_appointment,
    cancel_appointment,
    get_user_appointments,
    reschedule_appointment,
)

load_dotenv()


@dataclass
class AgentSettings:
    """Runtime settings loaded from system configuration."""

    model_name: str
    temperature: float
    max_messages_in_context: int
    summary_threshold: int
    conversation_timeout_hours: int

    @classmethod
    def load(cls) -> "AgentSettings":
        """Loads settings from system configuration."""
        container = get_container()
        config = container.config

        return cls(
            model_name=config.get_value(ConfigKeys.AI_MODEL, ConfigDefaults.AI_MODEL),
            temperature=float(
                config.get_value(
                    ConfigKeys.AI_TEMPERATURE, ConfigDefaults.AI_TEMPERATURE
                )
            ),
            max_messages_in_context=int(
                config.get_value(
                    ConfigKeys.MAX_MESSAGES_IN_CONTEXT,
                    ConfigDefaults.MAX_MESSAGES_IN_CONTEXT,
                )
            ),
            summary_threshold=int(
                config.get_value(
                    ConfigKeys.SUMMARY_MESSAGE_THRESHOLD,
                    ConfigDefaults.SUMMARY_MESSAGE_THRESHOLD,
                )
            ),
            conversation_timeout_hours=int(
                config.get_value(
                    ConfigKeys.CONVERSATION_TIMEOUT_HOURS,
                    ConfigDefaults.CONVERSATION_TIMEOUT_HOURS,
                )
            ),
        )


def create_llm(model_name: str, temperature: float):
    """Creates LLM instance for the specified model.

    Args:
        model_name: Model identifier (e.g., 'gpt-4o-mini', 'claude-3-sonnet').
        temperature: Temperature setting for responses.

    Returns:
        Configured LLM instance.
    """
    if model_name.startswith("gpt"):
        return ChatOpenAI(model=model_name, temperature=temperature)
    elif model_name.startswith("claude"):
        return ChatAnthropic(model=model_name, temperature=temperature)
    elif model_name.startswith("gemini"):
        return ChatGoogleGenerativeAI(model=model_name, temperature=temperature)
    else:
        return ChatOpenAI(model=model_name, temperature=temperature)


tools = [
    get_services,
    get_categories,
    get_service_details,
    get_available_slots,
    find_or_create_user,
    get_user_info,
    create_appointment,
    cancel_appointment,
    get_user_appointments,
    reschedule_appointment,
]


def get_state_value(state, key: str, default=None):
    """Gets value from state regardless of dict or typed object."""
    if isinstance(state, dict):
        return state.get(key, default)
    return getattr(state, key, default)


def messages_to_langchain(messages: list[Message]) -> list[BaseMessage]:
    """Converts domain messages to LangChain message objects."""
    result = []
    for msg in messages:
        if msg.role in ("human", "user"):
            result.append(HumanMessage(content=msg.content))
        elif msg.role in ("ai", "assistant"):
            result.append(AIMessage(content=msg.content))
    return result


SUMMARY_PROMPT = """You are an assistant that summarizes conversations concisely.
Summarize the following conversation keeping key points:
- User information (name, ID if mentioned)
- Services or appointments discussed
- Any preferences expressed
- Current conversation state

Conversation:
{conversation}

Concise summary:"""

UPDATE_SUMMARY_PROMPT = """You are an assistant that updates conversation summaries.

Previous summary:
{existing_summary}

New messages:
{new_messages}

Update the summary incorporating the new information concisely:"""

MEMORY_PROFILE_PROMPT = """Analyze the following conversation summary and extract key user profile information.
ONLY extract information that is EXPLICITLY mentioned in the summary.

Conversation summary:
{summary}

Current user profile (if exists):
{current_profile}

Respond ONLY with valid JSON with fields that have new or updated information:
{{
    "full_name": "name if mentioned",
    "identification_number": "ID if mentioned",
    "preferred_services": ["list of services requested"],
    "preferred_employees": ["employees mentioned as preferred"],
    "preferred_time_slots": ["morning" or "afternoon" if preference shown],
    "last_appointment_service": "last scheduled service",
    "last_appointment_date": "last appointment date in YYYY-MM-DD format",
    "notes": ["relevant notes about user"]
}}

IMPORTANT: Only include fields with real information from summary. If no info for a field, don't include it."""


def load_context(state, config: RunnableConfig) -> dict:
    """Loads context from database including session, conversation, and messages.

    Args:
        state: Current graph state.
        config: Runnable configuration with client settings.

    Returns:
        dict: Updated state with loaded context.
    """
    container = get_container()
    configurable = config.get("configurable", {})
    settings: AgentSettings = configurable.get("settings")

    if isinstance(state, dict):
        from_number = state.get("from_number", "")
        to_number = state.get("to_number", "")
        client_id_from_state = state.get("client_id", "")
        user_phone_from_state = state.get("user_phone", "")
        all_messages = state.get("messages", [])
    else:
        from_number = state.from_number
        to_number = state.to_number
        client_id_from_state = state.client_id
        user_phone_from_state = state.user_phone
        all_messages = state.messages

    new_user_message = None
    for msg in reversed(all_messages):
        if isinstance(msg, HumanMessage):
            new_user_message = msg
            break

    client_id = None
    if to_number:
        client = container.clients.get_by_whatsapp(to_number)
        if client:
            client_id = client.id

    if not client_id:
        client_id = configurable.get("client_id", client_id_from_state)

    user_phone = from_number or configurable.get("user_phone", user_phone_from_state)

    if not client_id or not user_phone:
        replace_marker = SystemMessage(content="__REPLACE_MESSAGES__")
        msgs = [replace_marker]
        if new_user_message:
            msgs.append(new_user_message)
        return {"messages": msgs, "user_phone": user_phone}

    updates = {
        "client_id": client_id,
        "user_phone": user_phone,
        "from_number": from_number,
        "to_number": to_number,
    }

    client = container.clients.get_by_id(client_id)
    if not client:
        replace_marker = SystemMessage(content="__REPLACE_MESSAGES__")
        msgs = [replace_marker]
        if new_user_message:
            msgs.append(new_user_message)
        updates["messages"] = msgs
        return updates

    branches = container.branches.get_by_client(client_id)
    if len(branches) == 1:
        updates["branch_id"] = branches[0].id

    user = container.users.get_by_phone(client_id, user_phone)
    if user:
        updates["user_id"] = user.id
        updates["user_name"] = user.full_name
        updates["user_cedula"] = user.identification_number

    session = container.sessions.get_or_create(client_id, user_phone)
    updates["session_id"] = session.id

    if user and not session.user_id:
        container.sessions.link_to_user(session.id, user.id)

    if session.memory_profile:
        updates["memory_profile_json"] = session.memory_profile

    conversation = container.conversations.get_active(
        session.id, settings.conversation_timeout_hours
    )

    if not conversation:
        conversation = container.conversations.create(session.id)

    conversation_id = conversation.id
    updates["conversation_id"] = conversation_id

    conversation_summary = conversation.summary

    if conversation_summary:
        updates["conversation_summary"] = conversation_summary
        db_messages = container.conversations.get_messages(conversation_id, limit=6)
    else:
        db_messages = container.conversations.get_messages(conversation_id)

    historical_messages = messages_to_langchain(db_messages) if db_messages else []

    if new_user_message:
        should_save = True
        if db_messages:
            last_db_msg = db_messages[-1]
            if (
                last_db_msg.role == "human"
                and last_db_msg.content == new_user_message.content
            ):
                should_save = False

        if should_save:
            container.conversations.add_message(
                conversation_id=conversation_id,
                role="human",
                content=new_user_message.content,
            )

    replace_marker = SystemMessage(content="__REPLACE_MESSAGES__")
    final_messages = [replace_marker] + historical_messages
    if new_user_message:
        final_messages.append(new_user_message)

    updates["messages"] = final_messages
    updates["saved_messages_count"] = len(historical_messages) + (
        1 if new_user_message else 0
    )

    return updates


def assistant(state, config: RunnableConfig) -> dict:
    """Main assistant node that generates responses using LLM.

    Args:
        state: Current graph state with messages.
        config: Runnable configuration.

    Returns:
        dict: State update with LLM response.
    """
    container = get_container()
    configurable = config.get("configurable", {})
    settings: AgentSettings = configurable.get("settings")

    llm = create_llm(settings.model_name, settings.temperature)
    llm_with_tools = llm.bind_tools(tools)

    messages = get_state_value(state, "messages", [])
    conversation_summary = get_state_value(state, "conversation_summary")
    memory_profile_json = get_state_value(state, "memory_profile_json")
    client_id = get_state_value(state, "client_id", "")
    branch_id = get_state_value(state, "branch_id")
    user_phone = get_state_value(state, "user_phone", "")

    business_name = "Business"
    bot_name = get_agent_name().lower()
    greeting_message = None
    branch_info = None
    has_multiple_branches = False
    branches_data = []

    if client_id:
        client = container.clients.get_by_id(client_id)
        if client:
            business_name = client.business_name
            bot_name = client.bot_name
            greeting_message = client.greeting_message

        branches = container.branches.get_by_client(client_id)
        has_multiple_branches = len(branches) > 1
        branches_data = [b.to_dict() for b in branches]

        if branch_id:
            branch = container.branches.get_by_id(branch_id)
            if branch:
                branch_info = branch.to_dict()

    system_prompt = get_system_prompt(
        business_name=business_name,
        bot_name=bot_name,
        greeting_message=greeting_message,
        branch_info=branch_info,
        user_profile_context=memory_profile_json,
        conversation_summary=conversation_summary,
        has_multiple_branches=has_multiple_branches,
        branches=branches_data,
        user_phone=user_phone,
        client_id=client_id,
    )

    recent_messages = _limit_messages(messages, settings.max_messages_in_context)
    llm_messages = [SystemMessage(content=system_prompt)] + recent_messages
    response = llm_with_tools.invoke(llm_messages)

    return {"messages": [response]}


def _limit_messages(messages: list, max_count: int) -> list:
    """Limits messages to specified count, keeping most recent."""
    if not messages:
        return []

    if len(messages) <= max_count:
        return list(messages)

    return list(messages)[-max_count:]


def save_final_response(state, config: RunnableConfig) -> dict:
    """Saves final LLM response to database.

    Args:
        state: Current graph state.
        config: Runnable configuration.

    Returns:
        dict: Empty dict (no state updates needed).
    """
    container = get_container()

    conversation_id = get_state_value(state, "conversation_id")
    if not conversation_id:
        return {}

    messages = get_state_value(state, "messages", [])
    if not messages:
        return {}

    last_msg = messages[-1]

    if isinstance(last_msg, AIMessage) and last_msg.content and not last_msg.tool_calls:
        container.conversations.add_message(
            conversation_id=conversation_id, role="ai", content=last_msg.content
        )

    return {}


def summarize_if_needed(state, config: RunnableConfig) -> dict:
    """Creates or updates conversation summary and memory profile if needed.

    Args:
        state: Current graph state.
        config: Runnable configuration.

    Returns:
        dict: State updates with new summary/profile if created.
    """
    container = get_container()
    configurable = config.get("configurable", {})
    settings: AgentSettings = configurable.get("settings")

    conversation_id = get_state_value(state, "conversation_id")
    session_id = get_state_value(state, "session_id")

    if not conversation_id:
        return {}

    db_messages = container.conversations.get_messages(conversation_id)
    message_count = len(db_messages)

    updates = {}

    if message_count <= settings.summary_threshold:
        return {}

    conversation = container.conversations.get_active(
        session_id, settings.conversation_timeout_hours
    )
    existing_summary = conversation.summary if conversation else None

    llm = create_llm(settings.model_name, settings.temperature)

    def format_messages_for_summary(msgs: list[Message]) -> str:
        formatted = []
        for msg in msgs:
            if msg.role == "human":
                formatted.append(f"User: {msg.content}")
            elif msg.role == "ai" and not msg.tool_name:
                formatted.append(f"Assistant: {msg.content}")
        return "\n".join(formatted)

    try:
        if existing_summary:
            recent_msgs = db_messages[-4:]
            new_messages_text = format_messages_for_summary(recent_msgs)
            prompt = UPDATE_SUMMARY_PROMPT.format(
                existing_summary=existing_summary, new_messages=new_messages_text
            )
        else:
            msgs_to_summarize = db_messages[:-2]
            conversation_text = format_messages_for_summary(msgs_to_summarize)
            prompt = SUMMARY_PROMPT.format(conversation=conversation_text)

        response = llm.invoke([HumanMessage(content=prompt)])
        new_summary = response.content

        container.conversations.update_summary(conversation_id, new_summary)
        updates["conversation_summary"] = new_summary

        if message_count >= 10 and message_count % 5 == 0 and session_id:
            try:
                existing_profile = container.sessions.get_memory_profile(session_id)

                profile_prompt = MEMORY_PROFILE_PROMPT.format(
                    summary=new_summary,
                    current_profile=existing_profile or "No existing profile",
                )

                profile_response = llm.invoke([HumanMessage(content=profile_prompt)])
                profile_json = profile_response.content.strip()

                if profile_json.startswith("```"):
                    profile_json = profile_json.split("```")[1]
                    if profile_json.startswith("json"):
                        profile_json = profile_json[4:]
                    profile_json = profile_json.strip()

                parsed_profile = json.loads(profile_json)

                if existing_profile:
                    try:
                        existing_data = json.loads(existing_profile)
                        for key, value in parsed_profile.items():
                            if isinstance(value, list) and key in existing_data:
                                existing_list = existing_data.get(key, [])
                                merged = list(set(existing_list + value))
                                existing_data[key] = merged[-5:]
                            elif value:
                                existing_data[key] = value
                        profile_json = json.dumps(existing_data, ensure_ascii=False)
                    except json.JSONDecodeError:
                        pass

                container.sessions.update_memory_profile(session_id, profile_json)
                updates["memory_profile_json"] = profile_json

            except Exception as e:
                log.error("agent", "Error updating memory_profile", error=str(e))

        return updates

    except Exception as e:
        log.error("agent", "Error generating summary", error=str(e))
        return {}


def should_continue(state) -> Literal["tools", END]:
    """Determines if graph should continue to tools or end."""
    messages = get_state_value(state, "messages", [])
    last_message = messages[-1] if messages else None

    if not last_message:
        return END

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"

    return END


def build_graph():
    """Builds the LangGraph state graph for the agent.

    Returns:
        StateGraph: Configured graph ready to compile.
    """
    builder = StateGraph(AgentState, input=InputState)

    builder.add_node("load_context", load_context)
    builder.add_node("assistant", assistant)
    builder.add_node("tools", ToolNode(tools))
    builder.add_node("save_final_response", save_final_response)
    builder.add_node("summarize_if_needed", summarize_if_needed)

    builder.add_edge(START, "load_context")
    builder.add_edge("load_context", "assistant")
    builder.add_conditional_edges(
        "assistant", should_continue, {"tools": "tools", END: "save_final_response"}
    )
    builder.add_edge("tools", "assistant")
    builder.add_edge("save_final_response", "summarize_if_needed")
    builder.add_edge("summarize_if_needed", END)

    return builder


graph = build_graph().compile()


def create_thread_config(
    client_id: str,
    user_phone: str,
    thread_id: str = None,
    branch_id: str = None,
) -> dict:
    """Creates configuration dict for graph invocation.

    Loads system settings and includes them in the config so they're
    available throughout the graph execution.

    Args:
        client_id: The client identifier.
        user_phone: User's phone number.
        thread_id: Optional thread ID. Generated if not provided.
        branch_id: Optional branch identifier.

    Returns:
        dict: Configuration for graph invocation with loaded settings.
    """
    import uuid

    settings = AgentSettings.load()

    config = {
        "configurable": {
            "client_id": client_id,
            "user_phone": user_phone,
            "thread_id": thread_id or str(uuid.uuid4()),
            "settings": settings,
        }
    }

    if branch_id:
        config["configurable"]["branch_id"] = branch_id

    return config


async def chat_async(
    message: str,
    client_id: str,
    user_phone: str,
    thread_id: str = None,
) -> tuple[str, str]:
    """Async convenience function to chat with the agent.

    Args:
        message: User message to process.
        client_id: The client identifier.
        user_phone: User's phone number.
        thread_id: Optional thread ID. Generated if not provided.

    Returns:
        tuple: Response message and thread ID.
    """
    import uuid

    if not thread_id:
        thread_id = str(uuid.uuid4())

    config = create_thread_config(
        client_id=client_id,
        user_phone=user_phone,
        thread_id=thread_id,
    )

    result = await graph.ainvoke({"messages": [HumanMessage(content=message)]}, config)

    response = ""
    for msg in reversed(result["messages"]):
        if (
            isinstance(msg, AIMessage)
            and msg.content
            and not getattr(msg, "tool_calls", None)
        ):
            response = msg.content
            break

    return response, thread_id


def chat_sync(
    message: str,
    client_id: str,
    user_phone: str,
    thread_id: str = None,
) -> tuple[str, str]:
    """Sync version of chat_async.

    Args:
        message: User message to process.
        client_id: The client identifier.
        user_phone: User's phone number.
        thread_id: Optional thread ID. Generated if not provided.

    Returns:
        tuple: Response message and thread ID.
    """
    import uuid

    if not thread_id:
        thread_id = str(uuid.uuid4())

    config = create_thread_config(
        client_id=client_id,
        user_phone=user_phone,
        thread_id=thread_id,
    )

    result = graph.invoke({"messages": [HumanMessage(content=message)]}, config)

    response = ""
    for msg in reversed(result["messages"]):
        if (
            isinstance(msg, AIMessage)
            and msg.content
            and not getattr(msg, "tool_calls", None)
        ):
            response = msg.content
            break

    return response, thread_id
