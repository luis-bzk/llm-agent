"""
Agente Principal mock_ai - LangGraph (STATELESS)

Este es el grafo principal del agente de agendación de citas.
El agente es COMPLETAMENTE STATELESS - toda la memoria viene de BD.

FLUJO:
1. Llega mensaje(s) del usuario (input_messages)
2. load_context:
   - Carga sesión y conversación de BD
   - Recupera summary O mensajes históricos de BD
   - Guarda los mensajes de entrada a BD inmediatamente
3. assistant:
   - Construye prompt con summary (si existe)
   - Usa mensajes históricos de BD + mensajes de entrada
   - Invoca LLM
4. save_response:
   - Guarda la respuesta del LLM a BD
5. summarize_if_needed:
   - Si hay >6 mensajes en BD, crea/actualiza summary
"""

import os
import json
from datetime import datetime
from typing import Literal

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    SystemMessage,
    ToolMessage,
    BaseMessage,
    RemoveMessage,
)
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition

from .state import MockAiState, InputState
from .prompts import get_system_prompt
from .db import get_db
from .tools import (
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
)

load_dotenv()

# =============================================================================
# CONFIGURACIÓN DE MODELOS
# =============================================================================


def get_llm(model_name: str = "gpt-4o-mini"):
    """Obtiene el LLM según el nombre del modelo"""
    if model_name.startswith("gpt"):
        return ChatOpenAI(model=model_name, temperature=0.3)
    elif model_name.startswith("claude"):
        return ChatAnthropic(model=model_name, temperature=0.3)
    elif model_name.startswith("gemini"):
        return ChatGoogleGenerativeAI(model=model_name, temperature=0.3)
    else:
        return ChatOpenAI(model="gpt-4o-mini", temperature=0.3)


# =============================================================================
# TOOLS
# =============================================================================

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


# =============================================================================
# HELPER PARA ACCEDER AL ESTADO
# =============================================================================


def get_state_value(state, key: str, default=None):
    """Obtiene un valor del estado, ya sea dict o objeto tipado."""
    if isinstance(state, dict):
        return state.get(key, default)
    return getattr(state, key, default)


def db_messages_to_langchain(db_messages: list[dict]) -> list[BaseMessage]:
    """
    Convierte mensajes de BD a objetos LangChain.

    NOTA: Solo guardamos mensajes de usuario (human) y respuestas finales del agente (ai).
    NO guardamos tool_calls ni tool messages - esos solo existen durante la ejecución.
    """
    result = []
    for msg in db_messages:
        role = msg["role"]
        content = msg["content"]

        if role == "human" or role == "user":
            result.append(HumanMessage(content=content))
        elif role == "ai" or role == "assistant":
            result.append(AIMessage(content=content))
    return result


# =============================================================================
# CONSTANTES
# =============================================================================

MAX_MESSAGES_BEFORE_SUMMARY = 6
SUMMARY_PROMPT = """Eres un asistente que resume conversaciones de manera concisa.
Resume la siguiente conversación manteniendo los puntos clave:
- Información del usuario (nombre, cédula si se mencionó)
- Servicios o citas discutidos
- Cualquier preferencia expresada
- Estado actual de la conversación

Conversación:
{conversation}

Resumen conciso:"""

UPDATE_SUMMARY_PROMPT = """Eres un asistente que actualiza resúmenes de conversaciones.

Resumen anterior:
{existing_summary}

Nuevos mensajes:
{new_messages}

Actualiza el resumen incorporando la nueva información de manera concisa:"""


# =============================================================================
# NODOS DEL GRAFO
# =============================================================================


def load_context(state, config: RunnableConfig) -> dict:
    """
    Nodo inicial que carga el contexto necesario (STATELESS).

    Este agente es STATELESS - la BD es la única fuente de verdad.

    Flujo:
    1. Extrae el último HumanMessage (mensaje nuevo del usuario)
    2. Resuelve to_number → client_id, from_number → user_phone
    3. Carga/crea sesión y conversación en BD
    4. Recupera mensajes históricos de BD
    5. Guarda el mensaje nuevo a BD
    6. Construye state.messages = históricos + mensaje nuevo (usando marcador REPLACE)

    NOTA: El marcador __REPLACE_MESSAGES__ indica al reducer que reemplace
    los mensajes en lugar de hacer append. Esto es necesario para compatibilidad
    con LangGraph Studio (que usa checkpointer) y para el CLI sin checkpointer.
    """
    db = get_db()
    configurable = config.get("configurable", {})

    # El estado puede venir como dict o como MockAiState
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

    # =========================================================================
    # EXTRAER SOLO EL ÚLTIMO HUMANMESSAGE (mensaje nuevo del usuario)
    # El checkpointer acumula todos los mensajes, pero solo nos interesa el nuevo
    # =========================================================================
    new_user_message = None
    for msg in reversed(all_messages):
        if isinstance(msg, HumanMessage):
            new_user_message = msg
            break

    # Resolver to_number → client_id
    client_id = None
    if to_number:
        client = db.get_client_by_whatsapp(to_number)
        if client:
            client_id = client["id"]

    if not client_id:
        client_id = configurable.get("client_id", client_id_from_state)

    user_phone = from_number or configurable.get("user_phone", user_phone_from_state)

    if not client_id or not user_phone:
        # Usar marcador de reemplazo para limpiar mensajes duplicados
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

    # Cargar cliente
    client = db.get_client(client_id)
    if not client:
        # Usar marcador de reemplazo para limpiar mensajes duplicados
        replace_marker = SystemMessage(content="__REPLACE_MESSAGES__")
        msgs = [replace_marker]
        if new_user_message:
            msgs.append(new_user_message)
        updates["messages"] = msgs
        return updates

    # Cargar sucursales
    branches = db.get_branches_by_client(client_id)
    if len(branches) == 1:
        updates["branch_id"] = branches[0]["id"]

    # Buscar usuario existente por teléfono
    user = db.get_user_by_phone(client_id, user_phone)
    if user:
        updates["user_id"] = user["id"]
        updates["user_name"] = user["full_name"]
        updates["user_cedula"] = user["identification_number"]

    # Cargar/crear sesión
    session = db.get_or_create_session(client_id, user_phone)
    updates["session_id"] = session["id"]

    # Si el usuario existe y la sesión no tiene user_id, vincularla
    if user and not session.get("user_id"):
        db.link_session_to_user(session["id"], user["id"])

    # Cargar conversación activa o crear nueva
    timeout_hours = configurable.get("conversation_timeout_hours", 2)
    conversation = db.get_active_conversation(session["id"], timeout_hours)

    if not conversation:
        conversation = db.create_conversation(session["id"])

    conversation_id = conversation["id"]
    updates["conversation_id"] = conversation_id

    # =========================================================================
    # RECUPERAR MEMORIA DE BD (fuente de verdad)
    # =========================================================================
    conversation_summary = conversation.get("summary")

    if conversation_summary:
        updates["conversation_summary"] = conversation_summary
        # Con summary, solo necesitamos los últimos mensajes
        db_messages = db.get_conversation_messages(conversation_id, limit=6)
    else:
        # Sin summary, recuperamos todo
        db_messages = db.get_conversation_messages(conversation_id)

    # Convertir mensajes de BD a LangChain
    historical_messages = db_messages_to_langchain(db_messages) if db_messages else []

    # =========================================================================
    # GUARDAR EL MENSAJE NUEVO A BD
    # =========================================================================
    if new_user_message:
        # Verificar que no sea un duplicado (el último mensaje en BD)
        should_save = True
        if db_messages:
            last_db_msg = db_messages[-1]
            if (
                last_db_msg["role"] == "human"
                and last_db_msg["content"] == new_user_message.content
            ):
                # Es el mismo mensaje, no guardar de nuevo
                should_save = False

        if should_save:
            db.add_message(
                conversation_id=conversation_id,
                role="human",
                content=new_user_message.content,
            )

    # =========================================================================
    # CONSTRUIR LISTA DE MENSAJES LIMPIA (reemplaza completamente state.messages)
    # =========================================================================
    # Usamos un mensaje marcador especial para indicar al reducer que reemplace
    # en lugar de hacer append. Ver replace_or_add_messages en state.py
    replace_marker = SystemMessage(content="__REPLACE_MESSAGES__")

    # Solo usamos: históricos de BD + mensaje nuevo
    final_messages = [replace_marker] + historical_messages
    if new_user_message:
        final_messages.append(new_user_message)

    updates["messages"] = final_messages

    # Guardar el índice de mensajes ya guardados en BD
    # Históricos + el nuevo mensaje del usuario = todo lo que ya está en BD
    # (sin contar el marcador que se elimina en el reducer)
    updates["saved_messages_count"] = len(historical_messages) + (
        1 if new_user_message else 0
    )

    return updates


def assistant(state, config: RunnableConfig) -> dict:
    """
    Nodo principal del asistente.

    - Construye el prompt con contexto (incluye summary si existe)
    - Invoca el LLM con tools
    """
    db = get_db()
    configurable = config.get("configurable", {})

    model_name = configurable.get("model_name", "gpt-4o-mini")
    llm = get_llm(model_name)
    llm_with_tools = llm.bind_tools(tools)

    messages = get_state_value(state, "messages", [])
    conversation_summary = get_state_value(state, "conversation_summary")
    client_id = get_state_value(state, "client_id", "")
    branch_id = get_state_value(state, "branch_id")
    user_phone = get_state_value(state, "user_phone", "")

    # Construir información del negocio
    business_name = "Negocio"
    bot_name = "mock_ai"
    greeting_message = None
    branch_info = None
    has_multiple_branches = False
    branches = []

    if client_id:
        client = db.get_client(client_id)
        if client:
            business_name = client["business_name"]
            bot_name = client.get("bot_name", "mock_ai")
            greeting_message = client.get("greeting_message")

        branches = db.get_branches_by_client(client_id)
        has_multiple_branches = len(branches) > 1

        if branch_id:
            branch_info = db.get_branch(branch_id)

    # Construir system prompt
    system_prompt = get_system_prompt(
        business_name=business_name,
        bot_name=bot_name,
        greeting_message=greeting_message,
        branch_info=branch_info,
        user_profile_context=None,
        conversation_summary=conversation_summary,
        has_multiple_branches=has_multiple_branches,
        branches=branches,
        user_phone=user_phone,
        client_id=client_id,
    )

    # Preparar mensajes para el LLM
    # Filtrar mensajes para evitar el error de tool messages sin tool_calls
    recent_messages = get_safe_messages_for_llm(messages)

    llm_messages = [SystemMessage(content=system_prompt)] + recent_messages

    # Invocar LLM
    response = llm_with_tools.invoke(llm_messages)

    return {"messages": [response]}


def get_safe_messages_for_llm(messages: list) -> list:
    """
    Prepara los mensajes para enviar al LLM.

    Los mensajes de BD solo contienen HumanMessage y AIMessage (sin tool_calls).
    Durante la ejecución, el state puede acumular tool_calls y ToolMessages,
    pero estos se manejan correctamente por LangGraph.

    Esta función solo limita la cantidad de mensajes para evitar contextos muy largos.
    """
    MAX_MESSAGES = 20

    if not messages:
        return []

    messages_list = list(messages)

    if len(messages_list) <= MAX_MESSAGES:
        return messages_list

    # Tomar los últimos MAX_MESSAGES
    return messages_list[-MAX_MESSAGES:]


def save_final_response(state, config: RunnableConfig) -> dict:
    """
    Guarda la respuesta final del LLM a la base de datos.

    Este nodo se ejecuta cuando el assistant termina (no va a tools).
    Solo guarda el último AIMessage si tiene contenido y no es tool_calls.
    """
    db = get_db()

    conversation_id = get_state_value(state, "conversation_id")
    if not conversation_id:
        return {}

    messages = get_state_value(state, "messages", [])
    if not messages:
        return {}

    # Obtener el último mensaje
    last_msg = messages[-1]

    # Solo guardar si es un AIMessage con contenido (no tool_calls)
    if isinstance(last_msg, AIMessage) and last_msg.content and not last_msg.tool_calls:
        db.add_message(
            conversation_id=conversation_id, role="ai", content=last_msg.content
        )

    return {}


def summarize_if_needed(state, config: RunnableConfig) -> dict:
    """
    Crea o actualiza el summary cuando hay más de 6 mensajes en BD.

    Lee los mensajes directamente de BD para determinar si necesita summarization.
    - Si no hay summary y hay >6 mensajes: crear summary
    - Si ya hay summary y hay nuevos mensajes: actualizarlo
    """
    db = get_db()
    configurable = config.get("configurable", {})

    conversation_id = get_state_value(state, "conversation_id")
    if not conversation_id:
        return {}

    # Leer mensajes de BD (fuente de verdad)
    db_messages = db.get_conversation_messages(conversation_id)
    message_count = len(db_messages)

    # Solo procesar si hay suficientes mensajes
    if message_count <= MAX_MESSAGES_BEFORE_SUMMARY:
        return {}

    # Verificar si ya hay summary
    conversation = db.get_active_conversation(
        get_state_value(state, "session_id"),
        configurable.get("conversation_timeout_hours", 2),
    )
    existing_summary = conversation.get("summary") if conversation else None

    model_name = configurable.get("model_name", "gpt-4o-mini")
    llm = get_llm(model_name)

    # Formatear mensajes de BD para el prompt
    def format_db_messages_for_summary(msgs):
        formatted = []
        for msg in msgs:
            role = msg["role"]
            content = msg["content"]
            if role == "human":
                formatted.append(f"Usuario: {content}")
            elif role == "ai" and not msg.get("tool_name"):
                formatted.append(f"Asistente: {content}")
            # No incluir tool messages ni tool_calls en el resumen
        return "\n".join(formatted)

    try:
        if existing_summary:
            # Actualizar summary existente con mensajes recientes de BD
            recent_msgs = db_messages[-4:]
            new_messages_text = format_db_messages_for_summary(recent_msgs)

            prompt = UPDATE_SUMMARY_PROMPT.format(
                existing_summary=existing_summary, new_messages=new_messages_text
            )
        else:
            # Crear summary nuevo con los primeros mensajes
            msgs_to_summarize = db_messages[:-2]
            conversation_text = format_db_messages_for_summary(msgs_to_summarize)

            prompt = SUMMARY_PROMPT.format(conversation=conversation_text)

        # Generar summary
        response = llm.invoke([HumanMessage(content=prompt)])
        new_summary = response.content

        # Guardar en BD
        db.update_conversation_summary(conversation_id, new_summary)

        return {"conversation_summary": new_summary}

    except Exception as e:
        print(f"Error generando summary: {e}")
        return {}


def should_continue(state) -> Literal["tools", END]:
    """
    Determina si el grafo debe continuar a tools o terminar.
    """
    messages = get_state_value(state, "messages", [])
    last_message = messages[-1] if messages else None

    if not last_message:
        return END

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"

    return END


# =============================================================================
# CONSTRUCCIÓN DEL GRAFO
# =============================================================================


def build_graph():
    """
    Construye el grafo de LangGraph para el agente mock_ai (STATELESS).

    Estructura:
    START -> load_context -> assistant -> [tools -> assistant]* -> save_final_response -> summarize_if_needed -> END

    Flujo:
    1. load_context: Guarda mensaje del usuario a BD, recupera histórico
    2. assistant: Genera respuesta (puede tener tool_calls)
    3. Si hay tool_calls:
       - tools: Ejecuta las herramientas
       - Vuelve a assistant
    4. Si no hay tool_calls:
       - save_final_response: Guarda respuesta final a BD
       - summarize_if_needed: Actualiza summary si hay >6 mensajes

    NOTA: Solo guardamos en BD mensajes de usuario y respuestas finales.
    Los tool_calls y tool_messages son efímeros (solo durante la ejecución).
    """
    builder = StateGraph(MockAiState, input=InputState)

    # Agregar nodos
    builder.add_node("load_context", load_context)
    builder.add_node("assistant", assistant)
    builder.add_node("tools", ToolNode(tools))
    builder.add_node("save_final_response", save_final_response)
    builder.add_node("summarize_if_needed", summarize_if_needed)

    # Definir flujo
    builder.add_edge(START, "load_context")
    builder.add_edge("load_context", "assistant")

    # Edge condicional después del assistant
    builder.add_conditional_edges(
        "assistant", should_continue, {"tools": "tools", END: "save_final_response"}
    )

    # Después de tools, volver al assistant
    builder.add_edge("tools", "assistant")

    # Después de guardar respuesta final, verificar si necesita summarization
    builder.add_edge("save_final_response", "summarize_if_needed")
    builder.add_edge("summarize_if_needed", END)

    return builder


# =============================================================================
# INSTANCIA GLOBAL PARA LANGGRAPH STUDIO
# =============================================================================

graph = build_graph().compile()


# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================


def create_thread_config(
    client_id: str,
    user_phone: str,
    thread_id: str = None,
    model_name: str = "gpt-4o-mini",
    branch_id: str = None,
) -> dict:
    """Crea la configuración para una invocación del grafo."""
    import uuid

    config = {
        "configurable": {
            "client_id": client_id,
            "user_phone": user_phone,
            "model_name": model_name,
            "thread_id": thread_id or str(uuid.uuid4()),
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
    model_name: str = "gpt-4o-mini",
) -> tuple[str, str]:
    """Función de conveniencia para chatear con el agente (async)."""
    import uuid

    if not thread_id:
        thread_id = str(uuid.uuid4())

    config = create_thread_config(
        client_id=client_id,
        user_phone=user_phone,
        thread_id=thread_id,
        model_name=model_name,
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
    model_name: str = "gpt-4o-mini",
) -> tuple[str, str]:
    """Versión síncrona de chat_async."""
    import uuid

    if not thread_id:
        thread_id = str(uuid.uuid4())

    config = create_thread_config(
        client_id=client_id,
        user_phone=user_phone,
        thread_id=thread_id,
        model_name=model_name,
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
