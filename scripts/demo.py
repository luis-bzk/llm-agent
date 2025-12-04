#!/usr/bin/env python3
"""
Demo Interactiva - Agente mock_ai

Este script permite probar el agente de forma interactiva por consola.

Uso:
    python scripts/demo.py

Comandos especiales:
    - 'salir' o 'exit': Terminar
    - 'debug': Ver estado interno
    - 'reset': Reiniciar conversación
    - 'cliente:juan' o 'cliente:alberto': Cambiar de cliente
"""
import sys
import os

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from src.agent import chat_sync, graph
from src.db import get_db
from src.db.seed import seed_all


def get_client_info():
    """Obtiene información de los clientes disponibles"""
    db = get_db()

    # Buscar clientes
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, business_name, whatsapp_number FROM clients WHERE is_active = 1"
        )
        clients = [dict(row) for row in cursor.fetchall()]

    return clients


def print_header():
    print("=" * 70)
    print("  MOCK_AI AGENT - Demo Interactiva")
    print("=" * 70)
    print()


def print_help():
    print(
        """
Comandos disponibles:
  salir, exit    - Terminar la demo
  debug          - Ver estado interno (citas, usuarios)
  reset          - Reiniciar conversación (nuevo thread)
  seed           - Regenerar datos de ejemplo
  clientes       - Ver clientes disponibles
  cliente:N      - Cambiar al cliente N (ej: cliente:1)
  help           - Mostrar esta ayuda
"""
    )


def run_demo():
    """Ejecuta la demo interactiva"""
    print_header()

    # Verificar si hay datos
    clients = get_client_info()

    if not clients:
        print("No hay clientes en la base de datos.")
        print("Ejecutando seed para crear datos de ejemplo...")
        seed_all()
        clients = get_client_info()

    # Mostrar clientes disponibles
    print("Clientes disponibles:")
    for i, client in enumerate(clients, 1):
        print(
            f"  {i}. {client['business_name']} (WhatsApp: {client['whatsapp_number']})"
        )

    # Seleccionar cliente inicial
    current_client = clients[0]
    current_phone = "+593999888777"  # Número de prueba del usuario
    thread_id = None

    print(f"\nCliente activo: {current_client['business_name']}")
    print(f"Simulando usuario con teléfono: {current_phone}")
    print("\nEscribe 'help' para ver comandos disponibles.")
    print("-" * 70)

    while True:
        try:
            user_input = input("\n👤 Tú: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n¡Hasta luego! 👋")
            break

        if not user_input:
            continue

        # Comandos especiales
        lower_input = user_input.lower()

        if lower_input in ["salir", "exit", "quit"]:
            print("\n¡Hasta luego! 👋")
            break

        if lower_input == "help":
            print_help()
            continue

        if lower_input == "debug":
            db = get_db()
            print("\n[DEBUG] Estado interno:")
            print(f"  Cliente: {current_client['business_name']}")
            print(f"  Thread ID: {thread_id}")

            # Mostrar citas
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) as count FROM appointments WHERE status = 'scheduled'"
                )
                apt_count = cursor.fetchone()["count"]
                cursor.execute("SELECT COUNT(*) as count FROM users")
                user_count = cursor.fetchone()["count"]
                print(f"  Citas activas: {apt_count}")
                print(f"  Usuarios registrados: {user_count}")
            continue

        if lower_input == "reset":
            thread_id = None
            print("\n✅ Conversación reiniciada (nuevo thread)")
            continue

        if lower_input == "seed":
            print("\nRegenerando datos de ejemplo...")
            seed_all()
            clients = get_client_info()
            current_client = clients[0]
            print("✅ Datos regenerados")
            continue

        if lower_input == "clientes":
            print("\nClientes disponibles:")
            for i, client in enumerate(clients, 1):
                marker = "→" if client["id"] == current_client["id"] else " "
                print(f"  {marker} {i}. {client['business_name']}")
            continue

        if lower_input.startswith("cliente:"):
            try:
                idx = int(lower_input.split(":")[1]) - 1
                if 0 <= idx < len(clients):
                    current_client = clients[idx]
                    thread_id = None  # Reiniciar conversación
                    print(f"\n✅ Cambiado a: {current_client['business_name']}")
                else:
                    print(f"\n❌ Índice inválido. Usa 1-{len(clients)}")
            except ValueError:
                print("\n❌ Formato inválido. Usa: cliente:1")
            continue

        # Mensaje normal - enviar al agente
        try:
            response, thread_id = chat_sync(
                message=user_input,
                client_id=current_client["id"],
                user_phone=current_phone,
                thread_id=thread_id,
                model_name="gpt-4o-mini",
            )

            print(f"\n🤖 mock_ai: {response}")

        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback

            traceback.print_exc()


def main():
    """Entry point"""
    # Verificar variables de entorno
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY no está configurada")
        print("   Copia .env.example a .env y configura tus API keys")
        sys.exit(1)

    run_demo()


if __name__ == "__main__":
    main()
