#!/usr/bin/env python3
"""
Script de prueba para el agente mock_ai (STATELESS, sin checkpointer).

Este script simula una conversación real por terminal con logs detallados
para debugging. NO usa LangGraph Studio ni checkpointer.

Uso:
    python test_chat.py

Comandos especiales:
    /quit, /exit, /q  - Salir
    /clear            - Nueva conversación (simula timeout)
    /db               - Ver mensajes en BD
    /state            - Ver estado actual
"""
import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

# Agregar el directorio src al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich import print as rprint

from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

# Importar el agente
from src.agent import build_graph, get_state_value
from src.db import get_db

console = Console()

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

# Configura estos valores según tu BD de prueba
DEFAULT_CLIENT_ID = ""  # Se llenará automáticamente si hay un cliente en BD
DEFAULT_USER_PHONE = "+1234567890"
DEFAULT_MODEL = "gpt-4o-mini"

# Colores para logs
COLORS = {
    "node": "cyan",
    "tool": "yellow",
    "llm": "green",
    "db": "magenta",
    "error": "red",
    "info": "blue",
}


def log(category: str, message: str, data: any = None):
    """Log con formato bonito."""
    color = COLORS.get(category, "white")
    timestamp = datetime.now().strftime("%H:%M:%S")

    console.print(
        f"[dim]{timestamp}[/dim] [{color}][{category.upper()}][/{color}] {message}"
    )

    if data:
        if isinstance(data, dict):
            console.print(
                Syntax(
                    json.dumps(data, indent=2, default=str, ensure_ascii=False),
                    "json",
                    theme="monokai",
                )
            )
        elif isinstance(data, list):
            for item in data:
                console.print(f"  • {item}")
        else:
            console.print(f"  {data}")


def get_default_client():
    """Obtiene el primer cliente de la BD para pruebas."""
    db = get_db()
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, business_name FROM clients LIMIT 1")
        row = cursor.fetchone()
        if row:
            return dict(row)
    return None


def show_db_messages(conversation_id: str):
    """Muestra los mensajes guardados en BD."""
    db = get_db()
    messages = db.get_conversation_messages(conversation_id)

    table = Table(title=f"Mensajes en BD (conversation_id: {conversation_id[:8]}...)")
    table.add_column("#", style="dim")
    table.add_column("Role", style="cyan")
    table.add_column("Content", max_width=60)
    table.add_column("Tool", style="yellow")

    for i, msg in enumerate(messages, 1):
        content = (
            msg["content"][:57] + "..." if len(msg["content"]) > 60 else msg["content"]
        )
        table.add_row(str(i), msg["role"], content, msg.get("tool_name", ""))

    console.print(table)
    console.print(f"\n[dim]Total: {len(messages)} mensajes[/dim]")


def show_state(state: dict):
    """Muestra el estado actual."""
    table = Table(title="Estado Actual")
    table.add_column("Campo", style="cyan")
    table.add_column("Valor")

    for key, value in state.items():
        if key == "messages":
            value = f"{len(value)} mensajes"
        elif isinstance(value, str) and len(value) > 50:
            value = value[:47] + "..."
        table.add_row(key, str(value))

    console.print(table)


def format_messages_for_display(messages: list) -> str:
    """Formatea mensajes para mostrar en logs."""
    lines = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            lines.append(f"👤 Human: {msg.content[:100]}...")
        elif isinstance(msg, AIMessage):
            if msg.tool_calls:
                tools = [tc["name"] for tc in msg.tool_calls]
                lines.append(f"🤖 AI: [tool_calls: {', '.join(tools)}]")
            else:
                lines.append(f"🤖 AI: {msg.content[:100]}...")
        elif isinstance(msg, ToolMessage):
            lines.append(f"🔧 Tool({msg.name}): {msg.content[:50]}...")
        elif isinstance(msg, SystemMessage):
            if msg.content == "__REPLACE_MESSAGES__":
                lines.append("🔄 [REPLACE MARKER]")
            else:
                lines.append(f"⚙️ System: {msg.content[:50]}...")
    return "\n".join(lines)


class LoggingGraph:
    """Wrapper del grafo con logging detallado."""

    def __init__(self):
        # Compilar SIN checkpointer = verdaderamente stateless
        self.graph = build_graph().compile()
        self.last_state = {}

    def invoke(self, input_state: dict, config: dict) -> dict:
        """Invoca el grafo con logging de cada paso."""

        console.print("\n" + "=" * 60)
        log("info", "Iniciando invocación del grafo")
        log(
            "info",
            "Input:",
            {
                "messages": len(input_state.get("messages", [])),
                "from_number": input_state.get("from_number"),
                "to_number": input_state.get("to_number"),
            },
        )

        # Usar stream para ver cada nodo
        events = []
        for event in self.graph.stream(input_state, config, stream_mode="updates"):
            events.append(event)

            for node_name, node_output in event.items():
                log("node", f"Nodo: {node_name}")

                # Skip si node_output es None
                if node_output is None:
                    continue

                # Log específico según el nodo
                if node_name == "load_context":
                    if "conversation_id" in node_output:
                        log(
                            "db",
                            f"Conversation ID: {node_output['conversation_id'][:8]}...",
                        )
                    if "messages" in node_output:
                        log(
                            "info", f"Mensajes cargados: {len(node_output['messages'])}"
                        )
                        # Mostrar mensajes (sin el marker)
                        msgs = [
                            m
                            for m in node_output["messages"]
                            if not (
                                isinstance(m, SystemMessage)
                                and m.content == "__REPLACE_MESSAGES__"
                            )
                        ]
                        if msgs:
                            console.print(
                                Panel(
                                    format_messages_for_display(msgs),
                                    title="Mensajes para LLM",
                                )
                            )

                elif node_name == "assistant":
                    if "messages" in node_output:
                        for msg in node_output["messages"]:
                            if isinstance(msg, AIMessage):
                                if msg.tool_calls:
                                    log("tool", "LLM decidió llamar tools:")
                                    for tc in msg.tool_calls:
                                        log(
                                            "tool",
                                            f"  → {tc['name']}({json.dumps(tc['args'], ensure_ascii=False)[:100]})",
                                        )
                                else:
                                    log(
                                        "llm",
                                        f"Respuesta del LLM: {msg.content[:200]}...",
                                    )

                elif node_name == "tools":
                    if "messages" in node_output:
                        for msg in node_output["messages"]:
                            if isinstance(msg, ToolMessage):
                                result = (
                                    msg.content[:200] + "..."
                                    if len(msg.content) > 200
                                    else msg.content
                                )
                                log("tool", f"Resultado de {msg.name}: {result}")

                elif node_name == "save_final_response":
                    log("db", "Guardando respuesta final en BD")

                elif node_name == "summarize_if_needed":
                    if "conversation_summary" in node_output:
                        log("db", "Summary generado/actualizado")

        # Obtener estado final
        final_state = {}
        for event in events:
            for node_output in event.values():
                if node_output is not None:
                    final_state.update(node_output)

        self.last_state = final_state

        console.print("=" * 60 + "\n")

        return final_state


def main():
    """Loop principal del chat."""
    console.print(
        Panel.fit(
            "[bold blue]mock_ai Agent - Test CLI[/bold blue]\n"
            "[dim]Agente stateless con logging detallado[/dim]\n\n"
            "Comandos: /quit, /clear, /db, /state",
            title="🤖 mock_ai",
        )
    )

    # Obtener cliente de prueba
    client = get_default_client()
    if not client:
        console.print(
            "[red]ERROR: No hay clientes en la BD. Ejecuta el seed primero.[/red]"
        )
        return

    client_id = client["id"]
    console.print(
        f"[green]Cliente: {client['business_name']} ({client_id[:8]}...)[/green]"
    )
    console.print(f"[green]Teléfono usuario: {DEFAULT_USER_PHONE}[/green]")
    console.print(f"[green]Modelo: {DEFAULT_MODEL}[/green]\n")

    # Crear grafo con logging
    graph = LoggingGraph()

    # Config para el grafo
    config = {
        "configurable": {
            "client_id": client_id,
            "user_phone": DEFAULT_USER_PHONE,
            "model_name": DEFAULT_MODEL,
        }
    }

    conversation_id = None

    while True:
        try:
            user_input = console.input("\n[bold green]Tú:[/bold green] ").strip()

            if not user_input:
                continue

            # Comandos especiales
            if user_input.lower() in ["/quit", "/exit", "/q"]:
                console.print("[yellow]¡Hasta luego![/yellow]")
                break

            if user_input.lower() == "/clear":
                conversation_id = None
                console.print("[yellow]Nueva conversación iniciada[/yellow]")
                continue

            if user_input.lower() == "/db":
                if conversation_id:
                    show_db_messages(conversation_id)
                else:
                    console.print("[yellow]No hay conversación activa[/yellow]")
                continue

            if user_input.lower() == "/state":
                if graph.last_state:
                    show_state(graph.last_state)
                else:
                    console.print("[yellow]No hay estado guardado[/yellow]")
                continue

            # Preparar input para el grafo
            input_state = {
                "messages": [HumanMessage(content=user_input)],
                "from_number": DEFAULT_USER_PHONE,
                "to_number": "",  # Se resuelve por client_id en config
            }

            # Invocar grafo
            result = graph.invoke(input_state, config)

            # Guardar conversation_id para comandos /db
            if "conversation_id" in result:
                conversation_id = result["conversation_id"]

            # Mostrar respuesta del bot
            response = ""
            messages = result.get("messages", [])
            for msg in reversed(messages):
                if (
                    isinstance(msg, AIMessage)
                    and msg.content
                    and not getattr(msg, "tool_calls", None)
                ):
                    response = msg.content
                    break

            if response:
                console.print(
                    Panel(
                        response,
                        title="[bold blue]🤖 mock_ai[/bold blue]",
                        border_style="blue",
                    )
                )
            else:
                console.print("[red]No se obtuvo respuesta[/red]")

        except KeyboardInterrupt:
            console.print("\n[yellow]¡Hasta luego![/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    main()
