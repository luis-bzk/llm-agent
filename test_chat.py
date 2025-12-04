#!/usr/bin/env python3
"""Test CLI for the mock_ai agent with detailed logging."""

import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

from src.container import set_container, get_container
from src.repositories.sqlite.factory import create_sqlite_container

set_container(create_sqlite_container())

from src.agent import build_graph, get_state_value, create_thread_config

console = Console()

BUSINESS_WHATSAPP = "+593912345678"
USER_PHONE = "+1234567890"

COLORS = {
    "node": "cyan",
    "tool": "yellow",
    "llm": "green",
    "db": "magenta",
    "error": "red",
    "info": "blue",
}


def log(category: str, message: str, data: any = None):
    """Prints formatted log message."""
    color = COLORS.get(category, "white")
    timestamp = datetime.now().strftime("%H:%M:%S")
    console.print(f"[dim]{timestamp}[/dim] [{color}][{category.upper()}][/{color}] {message}")

    if data:
        if isinstance(data, dict):
            console.print(Syntax(json.dumps(data, indent=2, default=str, ensure_ascii=False), "json", theme="monokai"))
        elif isinstance(data, list):
            for item in data:
                console.print(f"  • {item}")
        else:
            console.print(f"  {data}")


def show_db_messages(conversation_id: str):
    """Displays messages stored in database."""
    container = get_container()
    messages = container.conversations.get_messages(conversation_id)

    table = Table(title=f"Messages in DB (conversation_id: {conversation_id[:8]}...)")
    table.add_column("#", style="dim")
    table.add_column("Role", style="cyan")
    table.add_column("Content", max_width=60)
    table.add_column("Tool", style="yellow")

    for i, msg in enumerate(messages, 1):
        content = msg.content[:57] + "..." if len(msg.content) > 60 else msg.content
        table.add_row(str(i), msg.role, content, msg.tool_name or "")

    console.print(table)
    console.print(f"\n[dim]Total: {len(messages)} messages[/dim]")


def show_state(state: dict):
    """Displays current state."""
    table = Table(title="Current State")
    table.add_column("Field", style="cyan")
    table.add_column("Value")

    for key, value in state.items():
        if key == "messages":
            value = f"{len(value)} messages"
        elif isinstance(value, str) and len(value) > 50:
            value = value[:47] + "..."
        table.add_row(key, str(value))

    console.print(table)


def format_messages_for_display(messages: list) -> str:
    """Formats messages for log display."""
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
    """Graph wrapper with detailed logging."""

    def __init__(self):
        self.graph = build_graph().compile()
        self.last_state = {}

    def invoke(self, input_state: dict, config: dict) -> dict:
        """Invokes graph with step-by-step logging.

        Args:
            input_state: Initial state with messages.
            config: Graph configuration.

        Returns:
            dict: Final state after graph execution.
        """
        console.print("\n" + "=" * 60)
        log("info", "Starting graph invocation")
        log("info", "Input:", {
            "messages": len(input_state.get("messages", [])),
            "from_number": input_state.get("from_number"),
            "to_number": input_state.get("to_number"),
        })

        events = []
        for event in self.graph.stream(input_state, config, stream_mode="updates"):
            events.append(event)

            for node_name, node_output in event.items():
                log("node", f"Node: {node_name}")

                if node_output is None:
                    continue

                if node_name == "load_context":
                    if "conversation_id" in node_output:
                        log("db", f"Conversation ID: {node_output['conversation_id'][:8]}...")
                    if "messages" in node_output:
                        log("info", f"Messages loaded: {len(node_output['messages'])}")
                        msgs = [m for m in node_output["messages"]
                                if not (isinstance(m, SystemMessage) and m.content == "__REPLACE_MESSAGES__")]
                        if msgs:
                            console.print(Panel(format_messages_for_display(msgs), title="Messages for LLM"))

                elif node_name == "assistant":
                    if "messages" in node_output:
                        for msg in node_output["messages"]:
                            if isinstance(msg, AIMessage):
                                if msg.tool_calls:
                                    log("tool", "LLM decided to call tools:")
                                    for tc in msg.tool_calls:
                                        log("tool", f"  → {tc['name']}({json.dumps(tc['args'], ensure_ascii=False)[:100]})")
                                else:
                                    log("llm", f"LLM response: {msg.content[:200]}...")

                elif node_name == "tools":
                    if "messages" in node_output:
                        for msg in node_output["messages"]:
                            if isinstance(msg, ToolMessage):
                                result = msg.content[:200] + "..." if len(msg.content) > 200 else msg.content
                                log("tool", f"Result from {msg.name}: {result}")

                elif node_name == "save_final_response":
                    log("db", "Saving final response to DB")

                elif node_name == "summarize_if_needed":
                    if "conversation_summary" in node_output:
                        log("db", "Summary generated/updated")

        final_state = {}
        for event in events:
            for node_output in event.values():
                if node_output is not None:
                    final_state.update(node_output)

        self.last_state = final_state
        console.print("=" * 60 + "\n")

        return final_state


def main():
    """Main chat loop."""
    console.print(Panel.fit(
        "[bold blue]mock_ai Agent - Test CLI[/bold blue]\n"
        "[dim]Stateless agent with detailed logging[/dim]\n\n"
        "Commands: /quit, /clear, /db, /state",
        title="🤖 mock_ai",
    ))

    container = get_container()
    client = container.clients.get_by_whatsapp(BUSINESS_WHATSAPP)

    if not client:
        console.print(f"[red]ERROR: No client with WhatsApp {BUSINESS_WHATSAPP}[/red]")
        return

    console.print(f"[green]Business: {client.business_name}[/green]")
    console.print(f"[green]Business WhatsApp (to_number): {BUSINESS_WHATSAPP}[/green]")
    console.print(f"[green]User phone (from_number): {USER_PHONE}[/green]")
    console.print("[green]Model: (from system config)[/green]\n")

    graph = LoggingGraph()
    config = create_thread_config(client_id=client.id, user_phone=USER_PHONE)
    conversation_id = None

    while True:
        try:
            user_input = console.input("\n[bold green]You:[/bold green] ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["/quit", "/exit", "/q"]:
                console.print("[yellow]Goodbye![/yellow]")
                break

            if user_input.lower() == "/clear":
                conversation_id = None
                console.print("[yellow]New conversation started[/yellow]")
                continue

            if user_input.lower() == "/db":
                if conversation_id:
                    show_db_messages(conversation_id)
                else:
                    console.print("[yellow]No active conversation[/yellow]")
                continue

            if user_input.lower() == "/state":
                if graph.last_state:
                    show_state(graph.last_state)
                else:
                    console.print("[yellow]No saved state[/yellow]")
                continue

            input_state = {
                "messages": [HumanMessage(content=user_input)],
                "from_number": USER_PHONE,
                "to_number": BUSINESS_WHATSAPP,
            }

            result = graph.invoke(input_state, config)

            if "conversation_id" in result:
                conversation_id = result["conversation_id"]

            response = ""
            messages = result.get("messages", [])
            for msg in reversed(messages):
                if isinstance(msg, AIMessage) and msg.content and not getattr(msg, "tool_calls", None):
                    response = msg.content
                    break

            if response:
                console.print(Panel(response, title="[bold blue]🤖 mock_ai[/bold blue]", border_style="blue"))
            else:
                console.print("[red]No response received[/red]")

        except KeyboardInterrupt:
            console.print("\n[yellow]Goodbye![/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
