# Arquitectura Técnica - mock_ai Agent

Documentación técnica detallada del agente de agendación de citas basado en LangGraph.

## Tabla de Contenidos

1. [Principios de Diseño](#principios-de-diseño)
2. [Arquitectura General](#arquitectura-general)
3. [Diagrama del Grafo](#diagrama-del-grafo)
4. [Repository Pattern](#repository-pattern)
5. [Sistema de Estado](#sistema-de-estado)
6. [Sistema de Memoria](#sistema-de-memoria)
7. [Configuración del Sistema](#configuración-del-sistema)
8. [Tools Disponibles](#tools-disponibles)
9. [Integración con Google Calendar](#integración-con-google-calendar)
10. [Flujo de Datos](#flujo-de-datos)
11. [Esquema de Base de Datos](#esquema-de-base-de-datos)

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

### Separation of Concerns

- **Domain**: Entidades puras sin lógica de persistencia
- **Repositories**: Contratos abstractos para acceso a datos
- **SQLite Implementation**: Implementación concreta intercambiable
- **Container**: Dependency Injection para desacoplar componentes

---

## Arquitectura General

### Estructura de Archivos

```
src/
├── agent.py              # Grafo principal de LangGraph
├── state.py              # Definiciones de estado (InputState, MockAiState)
├── prompts.py            # System prompts del agente
├── container.py          # Dependency Injection Container
│
├── domain/               # Entidades del dominio (dataclasses puros)
│   ├── client.py         # Client
│   ├── branch.py         # Branch
│   ├── service.py        # Service, Category
│   ├── calendar.py       # Calendar
│   ├── appointment.py    # Appointment
│   ├── user.py           # User
│   ├── session.py        # Session
│   ├── conversation.py   # Conversation, Message
│   └── config.py         # ConfigKeys, ConfigDefaults
│
├── repositories/
│   ├── interfaces/       # Contratos abstractos (ABC)
│   │   ├── client_repository.py
│   │   ├── branch_repository.py
│   │   ├── service_repository.py
│   │   ├── calendar_repository.py
│   │   ├── appointment_repository.py
│   │   ├── user_repository.py
│   │   ├── session_repository.py
│   │   ├── conversation_repository.py
│   │   └── config_repository.py
│   │
│   └── sqlite/           # Implementación SQLite
│       ├── connection.py # Conexión y creación de tablas
│       ├── factory.py    # Factory para crear container
│       ├── client_repository.py
│       ├── branch_repository.py
│       ├── service_repository.py
│       ├── calendar_repository.py
│       ├── appointment_repository.py
│       ├── user_repository.py
│       ├── session_repository.py
│       ├── conversation_repository.py
│       └── config_repository.py
│
└── tools/                # Herramientas del agente
    ├── __init__.py       # Exporta todas las tools
    ├── services.py       # get_services, get_categories, get_service_details
    ├── availability.py   # get_available_slots
    ├── appointments.py   # create_appointment, cancel_appointment, etc.
    ├── user.py           # find_or_create_user, get_user_info
    └── calendar_integration.py  # Cliente de Google Calendar API
```

### Archivos Clave

| Archivo        | Responsabilidad                                      |
| -------------- | ---------------------------------------------------- |
| `agent.py`     | Definición del grafo, nodos, y lógica de routing     |
| `state.py`     | Estados tipados con Pydantic y reducer personalizado |
| `prompts.py`   | System prompt dinámico con contexto del negocio      |
| `container.py` | Dependency Injection Container                       |

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
                                 │                  │  • Si >N mensajes en BD    │
                                 └─────────────────►│  • Crea/actualiza summary  │
                                         │          │  • Guarda en BD            │
                                   (loop)           └──────────────┬─────────────┘
                                         │                         │
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

## Repository Pattern

### Concepto

El proyecto implementa el **Repository Pattern** para desacoplar la lógica de negocio del acceso a datos.

```
┌─────────────────────────────────────────────────────────────────┐
│                         Agent / Tools                            │
│  (Lógica de negocio - no conoce SQLite)                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ usa
┌─────────────────────────────────────────────────────────────────┐
│                      Container (DI)                              │
│  container.clients, container.branches, container.services...   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ implementa
┌─────────────────────────────────────────────────────────────────┐
│                   Interfaces (ABC)                               │
│  IClientRepository, IBranchRepository, IServiceRepository...    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ implementado por
┌─────────────────────────────────────────────────────────────────┐
│               SQLite Implementation                              │
│  SQLiteClientRepository, SQLiteBranchRepository...              │
└─────────────────────────────────────────────────────────────────┘
```

### Beneficios

- **Testeable**: Se pueden inyectar mocks de repositorios
- **Intercambiable**: Cambiar a Postgres, MongoDB o API sin tocar la lógica
- **Single Responsibility**: Cada repositorio maneja una entidad
- **Tipado fuerte**: Las interfaces definen contratos claros

### Container

```python
# container.py
class Container:
    """Dependency Injection Container."""

    def __init__(
        self,
        clients: IClientRepository,
        branches: IBranchRepository,
        services: IServiceRepository,
        calendars: ICalendarRepository,
        appointments: IAppointmentRepository,
        users: IUserRepository,
        sessions: ISessionRepository,
        conversations: IConversationRepository,
        config: IConfigRepository,
    ):
        self.clients = clients
        self.branches = branches
        self.services = services
        self.calendars = calendars
        self.appointments = appointments
        self.users = users
        self.sessions = sessions
        self.conversations = conversations
        self.config = config


# Singleton global
_container: Optional[Container] = None

def set_container(container: Container):
    global _container
    _container = container

def get_container() -> Container:
    if _container is None:
        raise RuntimeError("Container not initialized. Call set_container() first.")
    return _container
```

### Factory

```python
# repositories/sqlite/factory.py
def create_sqlite_container(db_path: str = None) -> Container:
    """Creates Container with SQLite implementations."""
    connection = SQLiteConnection(db_path)

    return Container(
        clients=SQLiteClientRepository(connection),
        branches=SQLiteBranchRepository(connection),
        services=SQLiteServiceRepository(connection),
        calendars=SQLiteCalendarRepository(connection),
        appointments=SQLiteAppointmentRepository(connection),
        users=SQLiteUserRepository(connection),
        sessions=SQLiteSessionRepository(connection),
        conversations=SQLiteConversationRepository(connection),
        config=SQLiteConfigRepository(connection),
    )
```

### Uso en el Código

```python
# En cualquier parte del código
from src.container import get_container

container = get_container()
client = container.clients.get_by_whatsapp("+593912345678")
branches = container.branches.get_by_client(client.id)
```

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
    memory_profile_json: Optional[str]

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

El sistema tiene 3 niveles de memoria:

### Nivel 1: Short-Term (Implícito)

- **Qué es**: Los mensajes actuales en `state.messages`
- **Límite**: Configurable via `max_messages_in_context` (default: 20)
- **Implementación**: Automático por el reducer

### Nivel 2: Long-Term (Activo)

- **Qué es**: Resumen automático de la conversación
- **Trigger**: Cuando hay más de `summary_message_threshold` mensajes
- **Almacenamiento**: Campo `summary` en tabla `conversations`
- **Uso**: Se incluye en el system prompt

```python
# En summarize_if_needed
if message_count > settings.summary_threshold:
    new_summary = llm.invoke(SUMMARY_PROMPT)
    container.conversations.update_summary(conversation_id, new_summary)
```

### Nivel 3: Total Memory (Preparado)

- **Qué es**: Perfil persistente del usuario
- **Almacenamiento**: Campo `memory_profile` en tabla `sessions`
- **Uso**: Recordar preferencias entre conversaciones

---

## Configuración del Sistema

### AgentSettings

La configuración se carga UNA vez al inicio de cada request:

```python
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
            temperature=float(config.get_value(...)),
            max_messages_in_context=int(config.get_value(...)),
            summary_threshold=int(config.get_value(...)),
            conversation_timeout_hours=int(config.get_value(...)),
        )
```

### Tabla system_config

| Key                          | Default     | Descripción                        |
| ---------------------------- | ----------- | ---------------------------------- |
| `ai_model`                   | `gpt-4o-mini` | Modelo de AI a usar               |
| `ai_temperature`             | `0.7`       | Temperatura del modelo             |
| `ai_max_tokens`              | `1024`      | Tokens máximos por respuesta       |
| `summary_message_threshold`  | `10`        | Mensajes antes de crear resumen    |
| `conversation_timeout_hours` | `2`         | Horas antes de expirar conversación |
| `max_messages_in_context`    | `20`        | Mensajes máximos en contexto LLM   |
| `default_booking_window_days`| `30`        | Días hacia adelante para agendar   |
| `default_slot_interval_minutes` | `15`     | Intervalo entre slots              |

### ConfigKeys y ConfigDefaults

```python
# domain/config.py
class ConfigKeys:
    """Configuration key constants."""
    AI_MODEL = "ai_model"
    AI_TEMPERATURE = "ai_temperature"
    AI_MAX_TOKENS = "ai_max_tokens"
    SUMMARY_MESSAGE_THRESHOLD = "summary_message_threshold"
    CONVERSATION_TIMEOUT_HOURS = "conversation_timeout_hours"
    MAX_MESSAGES_IN_CONTEXT = "max_messages_in_context"
    DEFAULT_BOOKING_WINDOW_DAYS = "default_booking_window_days"
    DEFAULT_SLOT_INTERVAL_MINUTES = "default_slot_interval_minutes"
    MAX_TOOL_RETRIES = "max_tool_retries"


class ConfigDefaults:
    """Default values for configuration."""
    AI_MODEL = "gpt-4o-mini"
    AI_TEMPERATURE = "0.7"
    AI_MAX_TOKENS = "1024"
    SUMMARY_MESSAGE_THRESHOLD = "10"
    CONVERSATION_TIMEOUT_HOURS = "2"
    MAX_MESSAGES_IN_CONTEXT = "20"
    DEFAULT_BOOKING_WINDOW_DAYS = "30"
    DEFAULT_SLOT_INTERVAL_MINUTES = "15"
    MAX_TOOL_RETRIES = "3"
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
│        │     mock_ai     │  ← Empleado disponible           │
│        │   (disponible)  │                                  │
│  12:00 ├─────────────────┤                                  │
│        │   Almuerzo      │  ← Bloque ocupado                │
│  13:00 ├─────────────────┤                                  │
│        │     mock_ai     │  ← Empleado disponible           │
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
│  • Buscar eventos "mock_ai"     │
│  • Buscar eventos ocupados      │
└─────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Calcular slots disponibles     │
│  ─────────────────────────────  │
│  bloques_mock_ai - ocupados     │
│  = slots libres                 │
└─────────────────────────────────┘
```

### Comportamiento sin eventos "mock_ai"

Si un calendario **no tiene eventos "mock_ai"** para una fecha:

- El empleado se considera **NO disponible** para ese día
- Se retorna lista vacía de slots
- **NO se usa fallback** a horarios por defecto

```python
availability_blocks = client.get_mock_ai_availability(google_calendar_id, target_date)

if not availability_blocks:
    # Sin eventos mock_ai = no disponible
    return []
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
│  config = create_thread_config(client_id="...", user_phone="...")        │
└──────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  2. LOAD_CONTEXT                                                         │
│  ────────────────────────────────────────────────────────────────────────│
│  • to_number → client_id (lookup en BD via container.clients)            │
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
│  • Usa settings.model_name y settings.temperature                        │
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
                                      │  • Si >threshold: genera summary   │
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
┌───────────────┐
│ system_config │
└───────────────┘

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

#### `system_config`

Configuración global del sistema.

| Campo       | Tipo     | Descripción                      |
| ----------- | -------- | -------------------------------- |
| key         | TEXT PK  | Clave de configuración           |
| value       | TEXT     | Valor                            |
| description | TEXT     | Descripción (opcional)           |
| updated_at  | DATETIME | Última actualización             |

#### `clients`

Negocios/empresas que usan el sistema.

| Campo               | Tipo    | Descripción                    |
| ------------------- | ------- | ------------------------------ |
| id                  | TEXT PK | UUID                           |
| business_name       | TEXT    | Nombre del negocio             |
| whatsapp_number     | TEXT    | Número de WhatsApp del negocio |
| bot_name            | TEXT    | Nombre del asistente           |
| booking_window_days | INT     | Días hacia adelante para agendar |

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
| price            | REAL    | Precio                  |
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

| Campo          | Tipo    | Descripción                   |
| -------------- | ------- | ----------------------------- |
| id             | TEXT PK | UUID                          |
| client_id      | TEXT FK | Referencia a clients          |
| user_id        | TEXT FK | Referencia a users (nullable) |
| phone_number   | TEXT    | Teléfono del usuario          |
| memory_profile | TEXT    | JSON con perfil del usuario   |

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
from src.container import set_container, get_container
from src.repositories.sqlite.factory import create_sqlite_container
from src.agent import graph, create_thread_config
from langchain_core.messages import HumanMessage

# Inicializar container
set_container(create_sqlite_container())

# Crear config con settings
config = create_thread_config(
    client_id="...",
    user_phone="+593912345678",
)

# Invocar
result = graph.invoke(
    {"messages": [HumanMessage(content="Hola")]},
    config
)

# Extraer respuesta
response = result["messages"][-1].content
```

---

## Ejemplos de Conversación

### Agendar cita simple

```
Usuario: Hola
mock_ai: ¡Hola! Soy Virsi, el asistente virtual de Clínicas Salud Total.
       Para poder ayudarte, ¿podrías indicarme tu nombre completo y número de cédula?

Usuario: Luis Berrezueta, 0105392435
mock_ai: Gracias Luis. ¿En qué puedo ayudarte hoy?

Usuario: Necesito una cita
mock_ai: Contamos con 2 sucursales:
       1. Clínica Centro (Av. 10 de Agosto) - Medicina General, Pediatría, Cardiología
       2. Clínica Norte (Av. de la Prensa) - Servicios Dentales, Dermatología
       ¿En cuál te gustaría atenderte?

Usuario: Centro
mock_ai: En Clínica Centro tenemos:
       - Consultas Generales
       - Pediatría
       - Cardiología
       ¿Qué tipo de servicio necesitas?

Usuario: Consulta general
mock_ai: Para Consulta General ($20, 30 min) tenemos disponibles:
       - Dr. Mario Gómez (8:00-16:00)
       - Dra. Laura Rodríguez (10:00-18:00)
       ¿Tienes preferencia de doctor o te muestro disponibilidad?

Usuario: Disponibilidad para mañana
mock_ai: Disponibilidad para mañana:
       Dr. Mario Gómez: 8:00, 8:30, 9:00, 9:30, 10:00...
       Dra. Laura Rodríguez: 10:00, 10:30, 11:00...
       ¿Cuál prefieres?

Usuario: 10:00 con Mario
mock_ai: ¡Perfecto! Tu cita ha sido confirmada:
       📅 Consulta General
       👨‍⚕️ Dr. Mario Gómez
       📍 Clínica Centro
       🕐 Mañana a las 10:00
       💰 $20

       Te enviaremos un recordatorio. ¿Hay algo más en lo que pueda ayudarte?
```
