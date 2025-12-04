# Arquitectura Técnica - mock_ai Agent

Documentación técnica detallada del agente de agendación de citas basado en LangGraph.

## Tabla de Contenidos

1. [Principios de Diseño](#principios-de-diseño)
2. [Diagrama del Grafo](#diagrama-del-grafo)
3. [Componentes Principales](#componentes-principales)
4. [Sistema de Estado](#sistema-de-estado)
5. [Sistema de Memoria](#sistema-de-memoria)
6. [Persistencia de Mensajes](#persistencia-de-mensajes)
7. [Tools Disponibles](#tools-disponibles)
8. [Integración con Google Calendar](#integración-con-google-calendar)
9. [Flujo de Datos](#flujo-de-datos)
10. [Esquema de Base de Datos](#esquema-de-base-de-datos)

---

## Principios de Diseño

### Agente Stateless

El agente es **completamente stateless**. La base de datos SQLite es la **única fuente de verdad**.

Cada invocación del grafo:

1. Recibe **solo** el mensaje nuevo del usuario
2. Carga contexto e historial desde la BD
3. Procesa el mensaje y ejecuta tools si es necesario
4. Guarda resultados en BD
5. Retorna la respuesta

**No se usa checkpointer** para mantener estado entre invocaciones. Esto permite:

- Escalabilidad horizontal
- Recuperación ante fallos
- Compatibilidad con cualquier infraestructura

### Persistencia Simplificada

Solo se guardan en BD:

- **Mensajes del usuario** (HumanMessage)
- **Respuestas finales del AI** (AIMessage sin tool_calls)

**NO se guardan**:

- Tool calls (AIMessage con tool_calls)
- Tool messages (resultados de herramientas)

Los tool_calls y tool_messages son **efímeros** - solo existen durante la ejecución de una invocación.

---

## Diagrama del Grafo

```
                                    ┌─────────────────────────────────────┐
                                    │              START                  │
                                    └─────────────────┬───────────────────┘
                                                      │
                                                      ▼
                              ┌────────────────────────────────────────────┐
                              │              load_context                   │
                              │  ─────────────────────────────────────────  │
                              │  • Extrae HumanMessage del input            │
                              │  • Resuelve client_id y user_phone          │
                              │  • Carga/crea sesión y conversación         │
                              │  • Recupera historial de BD                 │
                              │  • Guarda mensaje del usuario en BD         │
                              │  • Construye state.messages con marcador    │
                              │    __REPLACE_MESSAGES__                     │
                              └────────────────────────┬───────────────────┘
                                                       │
                                                       ▼
                              ┌────────────────────────────────────────────┐
                              │               assistant                     │
                              │  ─────────────────────────────────────────  │
                              │  • Construye system prompt con contexto     │
                              │  • Incluye summary si existe                │
                              │  • Invoca LLM con tools                     │
                              │  • Retorna AIMessage (con o sin tool_calls) │
                              └────────────────────────┬───────────────────┘
                                                       │
                                                       ▼
                              ┌────────────────────────────────────────────┐
                              │            should_continue                  │
                              │  ─────────────────────────────────────────  │
                              │  ¿El último mensaje tiene tool_calls?       │
                              └───────────┬───────────────────┬────────────┘
                                          │                   │
                                   Sí     │                   │  No
                                          ▼                   ▼
                  ┌────────────────────────────┐    ┌────────────────────────────┐
                  │           tools            │    │     save_final_response    │
                  │  ────────────────────────  │    │  ────────────────────────  │
                  │  • Ejecuta herramientas    │    │  • Guarda respuesta final  │
                  │  • ToolNode de LangGraph   │    │    del AI en BD            │
                  │  • Retorna ToolMessages    │    │  • Solo si tiene contenido │
                  └──────────────┬─────────────┘    └──────────────┬─────────────┘
                                 │                                  │
                                 │                                  ▼
                                 │                  ┌────────────────────────────┐
                                 │                  │    summarize_if_needed     │
                                 │                  │  ────────────────────────  │
                                 │                  │  • Si >6 mensajes en BD    │
                                 │                  │  • Crea/actualiza summary  │
                                 └─────────────────►│  • Guarda en BD            │
                                         │          └──────────────┬─────────────┘
                                   (loop)                          │
                                         │                         ▼
                                         │          ┌────────────────────────────┐
                                         │          │            END             │
                                         │          └────────────────────────────┘
                                         │
                              ┌──────────┴─────────┐
                              │     assistant      │
                              │  (procesa tools)   │
                              └────────────────────┘
```

### Flujo Resumido

```
START → load_context → assistant ──┬─→ [tools → assistant]* ──┬─→ save_final_response → summarize_if_needed → END
                                   │                          │
                                   └──────────────────────────┘
                                        (loop si hay tool_calls)
```

---

## Componentes Principales

### Estructura de Archivos

```
src/
├── agent.py              # Grafo principal de LangGraph
├── state.py              # Definiciones de estado (InputState, MockAiState)
├── prompts.py            # System prompts del agente
│
├── db/
│   ├── database.py       # Wrapper SQLite con todas las queries
│   └── seed.py           # Datos de ejemplo para demo
│
├── tools/
│   ├── __init__.py       # Exporta todas las tools
│   ├── services.py       # get_services, get_categories, get_service_details
│   ├── availability.py   # get_available_slots
│   ├── appointments.py   # create_appointment, cancel_appointment, etc.
│   ├── user.py           # find_or_create_user, get_user_info
│   └── calendar_integration.py  # Cliente de Google Calendar API
│
└── memory/               # Sistema de memoria (referencia)
    ├── short_term.py     # Últimos mensajes
    ├── long_term.py      # Resumen de conversación
    └── total.py          # Perfil persistente del usuario
```

### Archivos Clave

| Archivo       | Responsabilidad                                      |
| ------------- | ---------------------------------------------------- |
| `agent.py`    | Definición del grafo, nodos, y lógica de routing     |
| `state.py`    | Estados tipados con Pydantic y reducer personalizado |
| `prompts.py`  | System prompt dinámico con contexto del negocio      |
| `database.py` | Todas las operaciones de BD (singleton)              |

---

## Sistema de Estado

### InputState

Estado mínimo de entrada al grafo:

```python
class InputState(BaseModel):
    messages: Annotated[Sequence[AnyMessage], replace_or_add_messages]
    from_number: str = ""   # Teléfono del usuario (WhatsApp)
    to_number: str = ""     # Teléfono del negocio (WhatsApp)
```

### MockAiState

Estado completo que fluye por el grafo:

```python
class MockAiState(BaseModel):
    # Mensajes
    messages: Annotated[Sequence[AnyMessage], replace_or_add_messages]

    # Identificación
    from_number: str
    to_number: str
    client_id: str
    branch_id: Optional[str]

    # Usuario
    user_phone: str
    user_id: Optional[str]
    user_name: Optional[str]
    user_cedula: Optional[str]

    # Sesión
    session_id: Optional[str]
    conversation_id: Optional[str]

    # Memoria
    conversation_summary: Optional[str]
    user_profile_json: Optional[str]

    # Flujo
    selected_service_id: Optional[str]
    selected_calendar_id: Optional[str]
    pending_appointment: Optional[dict]

    # Control
    needs_escalation: bool = False
    escalation_reason: Optional[str]
    saved_messages_count: int = 0
```

### Reducer Personalizado

El reducer `replace_or_add_messages` permite que `load_context` **reemplace** los mensajes (reconstruyendo desde BD) mientras otros nodos **agregan** normalmente:

```python
def replace_or_add_messages(left, right):
    """
    Si el primer mensaje tiene content "__REPLACE_MESSAGES__": reemplaza todo
    De lo contrario: usa add_messages normal (append)
    """
    if right and len(right) > 0:
        first_msg = right[0]
        if hasattr(first_msg, "content") and first_msg.content == "__REPLACE_MESSAGES__":
            return list(right[1:])  # Descarta el marcador, retorna el resto

    return add_messages(left, right)  # Comportamiento normal
```

---

## Sistema de Memoria

El sistema tiene 3 niveles de memoria, pero actualmente solo se usa el nivel 2 (Long-Term):

### Nivel 1: Short-Term (Implícito)

- **Qué es**: Los mensajes actuales en `state.messages`
- **Límite**: Últimos 20 mensajes (configurable en `MAX_MESSAGES`)
- **Implementación**: Automático por el reducer

### Nivel 2: Long-Term (Activo)

- **Qué es**: Resumen automático de la conversación
- **Trigger**: Cuando hay más de 6 mensajes en BD
- **Almacenamiento**: Campo `summary` en tabla `conversations`
- **Uso**: Se incluye en el system prompt

```python
# En summarize_if_needed
if message_count > MAX_MESSAGES_BEFORE_SUMMARY:  # 6
    # Genera resumen con LLM
    new_summary = llm.invoke(SUMMARY_PROMPT)
    db.update_conversation_summary(conversation_id, new_summary)
```

### Nivel 3: Total Memory (Preparado, no implementado)

- **Qué es**: Perfil persistente del usuario
- **Almacenamiento**: Campo `memory_profile_key` en tabla `sessions`
- **Uso futuro**: Recordar preferencias entre conversaciones

---

## Persistencia de Mensajes

### Qué se guarda en BD

| Tipo                   | ¿Se guarda? | Cuándo                   | Campo `role` |
| ---------------------- | ----------- | ------------------------ | ------------ |
| HumanMessage           | ✅ Sí       | En `load_context`        | `"human"`    |
| AIMessage (final)      | ✅ Sí       | En `save_final_response` | `"ai"`       |
| AIMessage (tool_calls) | ❌ No       | -                        | -            |
| ToolMessage            | ❌ No       | -                        | -            |
| SystemMessage          | ❌ No       | -                        | -            |

### Por qué no guardamos tool_calls/tool_messages

1. **Evita errores de pairing**: Los LLMs requieren que cada `tool_call` tenga un `ToolMessage` correspondiente. Reconstruir esto desde BD es propenso a errores.

2. **Son efímeros**: Los tool_calls son decisiones internas del LLM para una invocación específica. El resultado final es lo que importa.

3. **Simplifica la BD**: Menos datos, queries más simples.

4. **El usuario no los ve**: El usuario solo ve mensajes de texto, no la ejecución interna de tools.

### Reconstrucción de Mensajes

```python
def db_messages_to_langchain(db_messages: list[dict]) -> list[BaseMessage]:
    """Solo convierte human y ai messages"""
    result = []
    for msg in db_messages:
        if msg["role"] == "human":
            result.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "ai":
            result.append(AIMessage(content=msg["content"]))
    return result
```

---

## Tools Disponibles

### Servicios

| Tool                  | Descripción                        | Parámetros                  |
| --------------------- | ---------------------------------- | --------------------------- |
| `get_services`        | Lista servicios de una sucursal    | `branch_id`                 |
| `get_categories`      | Lista categorías con sus servicios | `branch_id`                 |
| `get_service_details` | Detalles de un servicio específico | `branch_id`, `service_name` |

### Disponibilidad

| Tool                  | Descripción                           | Parámetros                                            |
| --------------------- | ------------------------------------- | ----------------------------------------------------- |
| `get_available_slots` | Horarios disponibles para un servicio | `branch_id`, `service_name`, `date`, `calendar_name?` |

### Citas

| Tool                     | Descripción             | Parámetros                                                    |
| ------------------------ | ----------------------- | ------------------------------------------------------------- |
| `create_appointment`     | Crea una cita           | `user_id`, `branch_id`, `service`, `calendar`, `date`, `time` |
| `get_user_appointments`  | Lista citas del usuario | `user_id`                                                     |
| `cancel_appointment`     | Cancela una cita        | `appointment_id`, `reason`                                    |
| `reschedule_appointment` | Reagenda una cita       | `appointment_id`, `new_date`, `new_time`                      |

### Usuario

| Tool                  | Descripción              | Parámetros                                                        |
| --------------------- | ------------------------ | ----------------------------------------------------------------- |
| `find_or_create_user` | Busca o crea usuario     | `client_id`, `phone_number`, `identification_number`, `full_name` |
| `get_user_info`       | Obtiene info del usuario | `user_id`                                                         |

---

## Integración con Google Calendar

### Concepto de Disponibilidad

La disponibilidad de cada empleado se determina por **eventos llamados "mock_ai"** en su Google Calendar.

```
┌─────────────────────────────────────────────────────────────┐
│  Calendario: Dr. Mario Gómez                                │
├─────────────────────────────────────────────────────────────┤
│  8:00  ┌─────────────────┐                                  │
│        │     mock_ai       │  ← Empleado disponible           │
│        │   (disponible)  │                                  │
│  12:00 ├─────────────────┤                                  │
│        │   Almuerzo      │  ← Bloque ocupado                │
│  13:00 ├─────────────────┤                                  │
│        │     mock_ai       │  ← Empleado disponible           │
│        │   (disponible)  │                                  │
│  16:00 └─────────────────┘                                  │
└─────────────────────────────────────────────────────────────┘
```

### Flujo de Disponibilidad

```
get_available_slots(branch_id, service, date)
         │
         ▼
┌─────────────────────────────────┐
│  1. Buscar servicio en BD       │
│  2. Buscar calendarios que      │
│     ofrecen ese servicio        │
└─────────────────────────────────┘
         │
         ▼ (para cada calendario)
┌─────────────────────────────────┐
│  Google Calendar API            │
│  ─────────────────────────────  │
│  • Buscar eventos "mock_ai"       │
│  • Buscar eventos ocupados      │
└─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Calcular slots disponibles     │
│  ─────────────────────────────  │
│  bloques_mock_ai - ocupados       │
│  = slots libres                 │
└─────────────────────────────────┘
```

### Comportamiento sin eventos "mock_ai"

Si un calendario **no tiene eventos "mock_ai"** para una fecha:

- El empleado se considera **NO disponible** para ese día
- Se retorna lista vacía de slots
- **NO se usa fallback** a horarios por defecto

```python
# En availability.py
availability_blocks = client.get_mock_ai_availability(google_calendar_id, target_date)

if not availability_blocks:
    # Sin eventos mock_ai = no disponible
    return []
```

### Cliente de Google Calendar

```python
# calendar_integration.py
class GoogleCalendarClient:
    def get_mock_ai_availability(self, calendar_id: str, target_date: date) -> list[tuple]:
        """Retorna bloques de disponibilidad [(start, end), ...]"""
        events = service.events().list(
            calendarId=calendar_id,
            timeMin=start_datetime,
            timeMax=end_datetime,
            q="mock_ai",  # Busca eventos con "mock_ai" en el título
        ).execute()

        return [(event.start, event.end) for event in events]

    def get_booked_slots(self, calendar_id: str, target_date: date) -> list[tuple]:
        """Retorna bloques ocupados (citas existentes)"""
        # Similar, pero sin filtro de "mock_ai"
```

---

## Flujo de Datos

### Invocación Completa

```
┌──────────────────────────────────────────────────────────────────────────┐
│  1. ENTRADA (WhatsApp/API)                                               │
│  ────────────────────────────────────────────────────────────────────────│
│  input = {                                                               │
│      "messages": [HumanMessage("Hola, quiero una cita")],                │
│      "from_number": "+593912345678",                                     │
│      "to_number": "+593998765432"                                        │
│  }                                                                       │
│  config = {"configurable": {"client_id": "...", "user_phone": "..."}}    │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  2. LOAD_CONTEXT                                                         │
│  ────────────────────────────────────────────────────────────────────────│
│  • to_number → client_id (lookup en BD)                                  │
│  • Carga/crea session para (client_id, from_number)                      │
│  • Carga/crea conversation activa                                        │
│  • Recupera mensajes históricos de BD                                    │
│  • Guarda HumanMessage en BD                                             │
│  • Construye: [__REPLACE_MARKER__, ...históricos..., nuevo_mensaje]      │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  3. ASSISTANT                                                            │
│  ────────────────────────────────────────────────────────────────────────│
│  • Construye system prompt con:                                          │
│    - Info del negocio (business_name, bot_name)                          │
│    - Info de sucursales                                                  │
│    - Summary de conversación (si existe)                                 │
│    - Datos del usuario (si ya se identificó)                             │
│  • Invoca LLM: [SystemMessage, ...mensajes...]                           │
│  • Retorna AIMessage (puede tener tool_calls)                            │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼ (tiene tool_calls)            ▼ (no tiene)
┌────────────────────────────────┐    ┌────────────────────────────────────┐
│  4a. TOOLS                     │    │  4b. SAVE_FINAL_RESPONSE           │
│  ──────────────────────────────│    │  ──────────────────────────────────│
│  • Ejecuta cada tool_call      │    │  • Guarda AIMessage.content en BD  │
│  • Retorna ToolMessages        │    │    con role="ai"                   │
│  • Vuelve a ASSISTANT          │    │                                    │
└────────────────────────────────┘    └────────────────────────────────────┘
                                                        │
                                                        ▼
                                      ┌────────────────────────────────────┐
                                      │  5. SUMMARIZE_IF_NEEDED            │
                                      │  ──────────────────────────────────│
                                      │  • Cuenta mensajes en BD           │
                                      │  • Si >6: genera/actualiza summary │
                                      │  • Guarda summary en BD            │
                                      └────────────────────────────────────┘
                                                        │
                                                        ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  6. SALIDA                                                               │
│  ────────────────────────────────────────────────────────────────────────│
│  result = {                                                              │
│      "messages": [...todos los mensajes de la ejecución...],             │
│      "conversation_id": "uuid",                                          │
│      "user_id": "uuid" (si se identificó),                               │
│      ...otros campos del estado...                                       │
│  }                                                                       │
│                                                                          │
│  # Extraer respuesta para el usuario:                                    │
│  response = result["messages"][-1].content  # Último AIMessage           │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Esquema de Base de Datos

### Diagrama ER Simplificado

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   clients   │────<│  branches   │────<│ categories  │
└─────────────┘     └─────────────┘     └──────┬──────┘
       │                   │                    │
       │                   │                    ▼
       │                   │            ┌─────────────┐
       │                   └───────────<│  services   │
       │                   │            └─────────────┘
       │                   │                    │
       │                   ▼                    │
       │            ┌─────────────┐             │
       │            │  calendars  │<────────────┘
       │            └─────────────┘      (calendar_services)
       │                   │
       │                   │
       ▼                   ▼
┌─────────────┐     ┌──────────────┐
│   users     │────>│appointments  │
└─────────────┘     └──────────────┘
       │
       │
       ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  sessions   │────<│conversations │────<│  messages   │
└─────────────┘     └──────────────┘     └─────────────┘
```

### Tablas Principales

#### `clients`

Negocios/empresas que usan el sistema.

| Campo               | Tipo    | Descripción                             |
| ------------------- | ------- | --------------------------------------- |
| id                  | TEXT PK | UUID                                    |
| business_name       | TEXT    | Nombre del negocio                      |
| whatsapp_number     | TEXT    | Número de WhatsApp del negocio          |
| bot_name            | TEXT    | Nombre del asistente (default: "mock_ai") |
| booking_window_days | INT     | Días hacia adelante para agendar        |

#### `branches`

Sucursales de cada cliente.

| Campo        | Tipo    | Descripción           |
| ------------ | ------- | --------------------- |
| id           | TEXT PK | UUID                  |
| client_id    | TEXT FK | Referencia a clients  |
| name         | TEXT    | Nombre de la sucursal |
| address      | TEXT    | Dirección             |
| opening_time | TIME    | Hora de apertura      |
| closing_time | TIME    | Hora de cierre        |

#### `services`

Servicios que se pueden agendar.

| Campo            | Tipo    | Descripción             |
| ---------------- | ------- | ----------------------- |
| id               | TEXT PK | UUID                    |
| branch_id        | TEXT FK | Referencia a branches   |
| category_id      | TEXT FK | Referencia a categories |
| name             | TEXT    | Nombre del servicio     |
| price            | DECIMAL | Precio                  |
| duration_minutes | INT     | Duración en minutos     |

#### `calendars`

Empleados/recursos que atienden citas.

| Campo              | Tipo    | Descripción                 |
| ------------------ | ------- | --------------------------- |
| id                 | TEXT PK | UUID                        |
| branch_id          | TEXT FK | Referencia a branches       |
| name               | TEXT    | Nombre del empleado         |
| google_calendar_id | TEXT    | ID del calendario en Google |

#### `sessions`

Sesiones de WhatsApp (1 por usuario por cliente).

| Campo        | Tipo    | Descripción                   |
| ------------ | ------- | ----------------------------- |
| id           | TEXT PK | UUID                          |
| client_id    | TEXT FK | Referencia a clients          |
| user_id      | TEXT FK | Referencia a users (nullable) |
| phone_number | TEXT    | Teléfono del usuario          |

#### `conversations`

Conversaciones dentro de una sesión.

| Campo           | Tipo     | Descripción                  |
| --------------- | -------- | ---------------------------- |
| id              | TEXT PK  | UUID                         |
| session_id      | TEXT FK  | Referencia a sessions        |
| summary         | TEXT     | Resumen de la conversación   |
| message_count   | INT      | Contador de mensajes         |
| last_message_at | DATETIME | Timestamp del último mensaje |

#### `messages`

Mensajes individuales.

| Campo           | Tipo     | Descripción                |
| --------------- | -------- | -------------------------- |
| id              | TEXT PK  | UUID                       |
| conversation_id | TEXT FK  | Referencia a conversations |
| role            | TEXT     | "human" o "ai"             |
| content         | TEXT     | Contenido del mensaje      |
| created_at      | DATETIME | Timestamp                  |

---

## Configuración Multi-Modelo

El agente soporta múltiples proveedores de LLM:

```python
def get_llm(model_name: str = "gpt-4o-mini"):
    if model_name.startswith("gpt"):
        return ChatOpenAI(model=model_name, temperature=0.3)
    elif model_name.startswith("claude"):
        return ChatAnthropic(model=model_name, temperature=0.3)
    elif model_name.startswith("gemini"):
        return ChatGoogleGenerativeAI(model=model_name, temperature=0.3)
```

Configurar en la invocación:

```python
config = {
    "configurable": {
        "client_id": "...",
        "user_phone": "...",
        "model_name": "gpt-4o-mini"  # o "claude-3-sonnet", "gemini-pro"
    }
}
```

---

## Ejecución y Testing

### CLI de Prueba

```bash
python test_chat.py
```

Comandos disponibles:

- `/quit`, `/exit`, `/q` - Salir
- `/clear` - Nueva conversación
- `/db` - Ver mensajes en BD
- `/state` - Ver estado actual

### LangGraph Studio

```bash
langgraph dev
```

Abre el Studio UI para visualizar el grafo y enviar mensajes de prueba.

### Invocación Programática

```python
from src.agent import graph, create_thread_config
from langchain_core.messages import HumanMessage

config = create_thread_config(
    client_id="...",
    user_phone="+593912345678",
    model_name="gpt-4o-mini"
)

result = graph.invoke(
    {"messages": [HumanMessage(content="Hola")]},
    config
)

# Extraer respuesta
response = result["messages"][-1].content
```
