#!/usr/bin/env python3
"""
Test de Double Texting - Agente mock_ai

Este script demuestra cómo manejar el escenario donde el usuario
envía múltiples mensajes rápidamente ("hola", "como estas", "necesito cita").

Estrategias disponibles (configurables en el SDK de LangGraph):
- reject: Rechaza mensajes nuevos hasta que termine el actual
- enqueue: Encola mensajes para procesar en orden
- interrupt: Interrumpe el actual, guarda progreso, procesa nuevo
- rollback: Interrumpe, elimina el anterior, procesa nuevo

Uso:
    python scripts/test_double_texting.py
"""
import sys
import os
import asyncio
import uuid

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from langchain_core.messages import HumanMessage, AIMessage
from src.agent import graph, create_thread_config
from src.db import get_db
from src.db.seed import seed_all


async def test_enqueue_strategy():
    """
    Prueba la estrategia 'enqueue' para double-texting.

    Los mensajes se encolan y procesan en orden.
    """
    print("=" * 70)
    print("TEST: Estrategia ENQUEUE")
    print("=" * 70)
    print()

    # Obtener cliente de prueba
    db = get_db()
    clients = []
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, business_name FROM clients LIMIT 1")
        row = cursor.fetchone()
        if row:
            clients.append(dict(row))

    if not clients:
        print("No hay clientes. Ejecutando seed...")
        seed_all()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, business_name FROM clients LIMIT 1")
            clients.append(dict(cursor.fetchone()))

    client_id = clients[0]["id"]
    user_phone = "+593999111222"
    thread_id = str(uuid.uuid4())

    config = create_thread_config(
        client_id=client_id, user_phone=user_phone, thread_id=thread_id
    )

    print(f"Cliente: {clients[0]['business_name']}")
    print(f"Thread ID: {thread_id}")
    print()

    # Simular mensajes rápidos del usuario
    messages = ["hola", "como estas", "necesito una cita"]

    print("Enviando mensajes en secuencia rápida:")
    for msg in messages:
        print(f"  → {msg}")

    print()
    print("Procesando (enqueue - cada mensaje espera al anterior)...")
    print()

    # Con enqueue, procesamos secuencialmente
    for i, msg in enumerate(messages, 1):
        print(f"[Mensaje {i}] Usuario: {msg}")

        result = await graph.ainvoke({"messages": [HumanMessage(content=msg)]}, config)

        # Obtener respuesta
        for m in reversed(result["messages"]):
            if (
                isinstance(m, AIMessage)
                and m.content
                and not getattr(m, "tool_calls", None)
            ):
                print(f"[Mensaje {i}] mock_ai: {m.content}")
                break

        print()

    print("=" * 70)
    print("TEST COMPLETADO")
    print("=" * 70)


async def test_interrupt_strategy():
    """
    Prueba la estrategia 'interrupt' para double-texting.

    Cada nuevo mensaje interrumpe el anterior pero guarda el progreso.
    """
    print()
    print("=" * 70)
    print("TEST: Estrategia INTERRUPT")
    print("=" * 70)
    print()

    # Este test es más complejo porque requiere el SDK de LangGraph Server
    # Por ahora, mostramos cómo se configuraría

    print(
        """
Para usar la estrategia 'interrupt' en producción:

1. Deploy del agente en LangGraph Platform:
   $ cd mock_ai-agent
   $ langgraph build -t mock_ai-agent
   $ docker compose up

2. Usar el SDK de LangGraph:

   from langgraph_sdk import get_client

   client = get_client(url="http://localhost:8123")
   thread = await client.threads.create()

   # Primer mensaje
   run1 = await client.runs.create(
       thread["thread_id"],
       "mock_ai",
       input={"messages": [{"role": "human", "content": "hola"}]},
       config=config
   )

   # Segundo mensaje con interrupt - interrumpe run1
   run2 = await client.runs.create(
       thread["thread_id"],
       "mock_ai",
       input={"messages": [{"role": "human", "content": "necesito una cita"}]},
       config=config,
       multitask_strategy="interrupt"  # <-- Clave
   )

   # run1 tendrá status='interrupted'
   # run2 continuará desde donde quedó run1

Estrategias disponibles:
- reject: Error 409 si hay run activo
- enqueue: Espera a que termine el anterior
- interrupt: Interrumpe anterior, guarda progreso
- rollback: Interrumpe anterior, elimina su estado
"""
    )


async def main():
    """Ejecutar tests"""
    print()
    print("MOCK_AI AGENT - Test de Double Texting")
    print()

    await test_enqueue_strategy()
    await test_interrupt_strategy()


if __name__ == "__main__":
    asyncio.run(main())
