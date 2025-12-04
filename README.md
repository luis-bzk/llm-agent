# mock_ai Agent - Demo de Agendación de Citas

Agente conversacional de LangGraph para agendación de citas médicas por WhatsApp.

## Tabla de Contenidos

1. [Requisitos Previos](#requisitos-previos)
2. [Instalación](#instalación)
3. [Configuración de Google Calendar](#configuración-de-google-calendar)
4. [Setup Local](#setup-local)
5. [Variables de Entorno](#variables-de-entorno)
6. [Ejecución](#ejecución)
7. [Arquitectura](#arquitectura)
8. [Datos de Prueba](#datos-de-prueba)

> **Documentación Técnica**: Para detalles sobre la arquitectura interna, sistema de memoria, diagrama del grafo y esquema de BD, ver [ARCHITECTURE.md](ARCHITECTURE.md).

---

## Requisitos Previos

### Software Requerido

- **Python 3.11+**
- **SQLite3** (viene incluido con Python en Mac/Linux)
- **Cuenta de Google** con acceso a Google Calendar

### Verificar Python

```bash
python3 --version
# Debe mostrar Python 3.11.x o superior
```

---

## Instalación

### 1. Clonar/Navegar al proyecto

```bash
cd mock_ai-agent
```

### 2. Crear entorno virtual

```bash
python3 -m venv venv
source venv/bin/activate  # Mac/Linux
# o en Windows: venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Crear directorios necesarios

```bash
mkdir -p config data
```

---

## Configuración de Google Calendar

Para que el agente pueda leer y crear eventos en Google Calendar, necesitas configurar la autenticación.

### Opción A: OAuth 2.0 (Recomendado para desarrollo/demo)

#### Paso 1: Crear proyecto en Google Cloud Console

1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un nuevo proyecto (ej: "mock_ai Agent Demo")
3. Selecciona el proyecto

#### Paso 2: Habilitar Google Calendar API

1. Ve a **APIs & Services** → **Library**
2. Busca "Google Calendar API"
3. Click en **Enable**

#### Paso 3: Configurar pantalla de consentimiento OAuth

1. Ve a **APIs & Services** → **OAuth consent screen**
2. Selecciona **External** (o Internal si usas Google Workspace)
3. Completa los campos requeridos:
   - **App name**: mock_ai Agent Demo
   - **User support email**: tu email
   - **Developer contact**: tu email
4. Click **Save and Continue**
5. En **Scopes**, click **Add or Remove Scopes**
6. Busca y selecciona: `https://www.googleapis.com/auth/calendar`
7. Click **Update** y luego **Save and Continue**
8. En **Test users**, agrega tu email de Google
9. Click **Save and Continue**

#### Paso 4: Crear credenciales OAuth

1. Ve a **APIs & Services** → **Credentials**
2. Click **+ CREATE CREDENTIALS** → **OAuth client ID**
3. Selecciona **Desktop app**
4. Nombre: "mock_ai Agent Desktop"
5. Click **Create**
6. Descarga el JSON (botón de descarga)
7. Renombra el archivo a `google_credentials.json`
8. Muévelo a `mock_ai-agent/config/google_credentials.json`

---

### Opción B: Service Account (Para producción)

Si prefieres usar una Service Account (sin intervención manual):

1. En Google Cloud Console, ve a **IAM & Admin** → **Service Accounts**
2. Crea una nueva Service Account
3. Descarga la clave JSON
4. Renómbrala a `google_credentials.json` y colócala en `config/`
5. **Importante**: Comparte cada calendario de Google con el email de la Service Account

---

## Setup Local

El proyecto incluye un script unificado para configurar todo el entorno de desarrollo local.

### Script de Setup: `scripts/local_setup.py`

Este script hace todo lo necesario para tener el ambiente funcionando:

1. Crea las tablas en SQLite si no existen
2. Inserta la configuración del sistema (modelo AI, timeouts, etc.)
3. Crea datos demo (cliente, sucursales, servicios, calendarios)
4. Opcionalmente crea los Google Calendars automáticamente

### Uso Básico (Solo seed de datos)

```bash
python scripts/local_setup.py
```

Esto crea:

- Base de datos SQLite en `data/mock_ai.db`
- Configuración del sistema (modelo, temperatura, etc.)
- 1 Cliente (Clínicas Salud Total)
- 2 Sucursales
- 5 Categorías de servicios
- 12 Servicios
- 11 Calendarios (sin Google Calendar IDs)

### Uso Completo (Seed + Google Calendars)

```bash
python scripts/local_setup.py --calendars
```

Esto hace todo lo anterior más:

- Crea 11 calendarios secundarios en tu cuenta de Google
- Guarda los Google Calendar IDs en la base de datos
- Se abre el navegador para autorizar (primera vez)

### Resetear Todo

```bash
rm -f data/mock_ai.db
python scripts/local_setup.py --calendars
```

---

### Configurar Eventos "mock_ai" de Disponibilidad

El agente determina cuándo un empleado está disponible buscando eventos llamados **"mock_ai"** en su calendario.

#### Crear eventos "mock_ai" para cada calendario

Para cada calendario, crea eventos recurrentes llamados **"mock_ai"** según los horarios:

#### Sucursal 1: Clínica Centro

| Calendario           | Días    | Horario     |
| -------------------- | ------- | ----------- |
| Dr. Mario Gómez      | Lun-Sáb | 8:00-16:00  |
| Dra. Laura Rodríguez | Lun-Sáb | 10:00-18:00 |
| Dra. Susana Torres   | Lun-Sáb | 8:00-14:00  |
| Dr. Pedro Morales    | Lun-Sáb | 14:00-19:00 |
| Dr. Roberto Vega     | Lun-Sáb | 9:00-17:00  |
| Dra. Carmen Díaz     | Lun-Sáb | 11:00-18:00 |

#### Sucursal 2: Clínica Norte

| Calendario         | Días    | Horario     |
| ------------------ | ------- | ----------- |
| Dra. María López   | Lun-Vie | 9:00-17:00  |
| Dr. Carlos Andrade | Lun-Vie | 12:00-18:00 |
| Dr. Felipe Herrera | Lun-Vie | 9:00-14:00  |
| Dra. Ana Martínez  | Lun-Vie | 9:00-16:00  |
| Dr. Javier Paredes | Lun-Vie | 13:00-18:00 |

#### Cómo crear un evento recurrente "mock_ai"

1. En Google Calendar, selecciona el calendario del empleado
2. Click en una fecha/hora para crear evento
3. **Título**: `mock_ai` (exactamente así, en minúsculas)
4. **Hora inicio/fin**: Según tabla
5. Click en **More options** → **Does not repeat** → **Custom...**
6. Selecciona los días de la semana correspondientes
7. Ends: Never
8. **Save**

---

## Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto:

```bash
cp .env.example .env
```

Edita `.env` con tus valores:

```env
# OpenAI (requerido)
OPENAI_API_KEY=sk-tu-api-key-aqui

# Google Calendar
GOOGLE_CALENDAR_CREDENTIALS_PATH=./config/google_credentials.json

# LangSmith (opcional, para tracing)
LANGSMITH_API_KEY=lsv2_tu-api-key
LANGSMITH_TRACING_V2=true
LANGSMITH_PROJECT=mock_ai-agent

# Modelos alternativos (opcional)
ANTHROPIC_API_KEY=sk-ant-tu-api-key
GOOGLE_API_KEY=tu-api-key-gemini
```

---

## Ejecución

### 1. Ejecutar el CLI de prueba

```bash
python test_chat.py
```

Este CLI interactivo te permite:

- Chatear con el agente en tiempo real
- Ver logs detallados de cada nodo del grafo
- Ver las llamadas a tools y sus resultados
- Inspeccionar el estado interno

**Comandos especiales:**

| Comando                | Descripción                  |
| ---------------------- | ---------------------------- |
| `/quit`, `/exit`, `/q` | Salir del CLI                |
| `/clear`               | Iniciar nueva conversación   |
| `/db`                  | Ver mensajes guardados en BD |
| `/state`               | Ver estado actual del agente |

### 2. Ejecutar con LangGraph Studio

```bash
langgraph dev
```

Esto abrirá:

- **API**: http://127.0.0.1:2024
- **Studio UI**: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
- **API Docs**: http://127.0.0.1:2024/docs

---

## Arquitectura

El proyecto sigue el patrón **Repository Pattern** con **Dependency Injection**.

### Estructura del Proyecto

```
mock_ai-agent/
├── config/                      # Credenciales
│   ├── google_credentials.json  # Credenciales de Google (tú lo creas)
│   └── token.json               # Token OAuth (auto-generado)
│
├── data/                        # Base de datos
│   └── mock_ai.db               # SQLite (auto-generado)
│
├── scripts/                     # Scripts de desarrollo
│   └── local_setup.py           # Setup unificado (seed + calendars)
│
├── src/
│   ├── agent.py                 # Grafo principal de LangGraph
│   ├── state.py                 # Definición del estado
│   ├── prompts.py               # System prompts
│   ├── container.py             # Dependency Injection Container
│   │
│   ├── domain/                  # Entidades del dominio (dataclasses)
│   │   ├── client.py
│   │   ├── branch.py
│   │   ├── service.py
│   │   ├── calendar.py
│   │   ├── appointment.py
│   │   ├── user.py
│   │   ├── session.py
│   │   └── conversation.py
│   │
│   ├── repositories/            # Patrón Repository
│   │   ├── interfaces/          # Contratos abstractos (ABC)
│   │   │   ├── client_repository.py
│   │   │   ├── branch_repository.py
│   │   │   ├── service_repository.py
│   │   │   ├── calendar_repository.py
│   │   │   ├── appointment_repository.py
│   │   │   ├── user_repository.py
│   │   │   ├── session_repository.py
│   │   │   ├── conversation_repository.py
│   │   │   └── config_repository.py
│   │   │
│   │   └── sqlite/              # Implementación SQLite
│   │       ├── connection.py    # Conexión y creación de tablas
│   │       ├── factory.py       # Factory para crear container
│   │       └── [repositorios]   # Implementaciones concretas
│   │
│   └── tools/                   # Herramientas del agente
│       ├── services.py          # Consulta de servicios
│       ├── availability.py      # Consulta de disponibilidad
│       ├── appointments.py      # Crear/cancelar citas
│       ├── user.py              # Gestión de usuarios
│       └── calendar_integration.py  # Google Calendar API
│
├── test_chat.py                 # CLI de prueba interactivo
├── .env                         # Variables de entorno
├── langgraph.json               # Configuración LangGraph
├── requirements.txt             # Dependencias Python
└── README.md                    # Este archivo
```

### Configuración del Sistema

La tabla `system_config` almacena configuraciones del agente:

| Key                             | Default       | Descripción                         |
| ------------------------------- | ------------- | ----------------------------------- |
| `ai_model`                      | `gpt-4o-mini` | Modelo de AI a usar                 |
| `ai_temperature`                | `0.7`         | Temperatura del modelo              |
| `ai_max_tokens`                 | `1024`        | Tokens máximos por respuesta        |
| `summary_message_threshold`     | `10`          | Mensajes antes de crear resumen     |
| `conversation_timeout_hours`    | `2`           | Horas antes de expirar conversación |
| `max_messages_in_context`       | `20`          | Mensajes máximos en contexto LLM    |
| `default_booking_window_days`   | `30`          | Días hacia adelante para agendar    |
| `default_slot_interval_minutes` | `15`          | Intervalo entre slots               |

---

## Datos de Prueba

### Cliente: Clínicas Salud Total

- **WhatsApp**: +593912345678
- **Ventana de agendación**: 30 días

### Sucursal 1: Clínica Centro

- **Dirección**: Av. 10 de Agosto N25-45 y Colón, Quito
- **Horario**: Lun-Sáb 8:00-19:00

| Categoría               | Servicios             | Precio | Duración |
| ----------------------- | --------------------- | ------ | -------- |
| **Consultas Generales** | Consulta General      | $20    | 30 min   |
|                         | Control Médico        | $15    | 20 min   |
|                         | Chequeo Preventivo    | $35    | 45 min   |
| **Pediatría**           | Consulta Pediátrica   | $25    | 30 min   |
|                         | Control de Niño Sano  | $18    | 25 min   |
| **Cardiología**         | Consulta Cardiológica | $40    | 40 min   |
|                         | Electrocardiograma    | $30    | 20 min   |

| Empleado             | Especialidad     | Horario     |
| -------------------- | ---------------- | ----------- |
| Dr. Mario Gómez      | Medicina General | 8:00-16:00  |
| Dra. Laura Rodríguez | Medicina General | 10:00-18:00 |
| Dra. Susana Torres   | Pediatría        | 8:00-14:00  |
| Dr. Pedro Morales    | Pediatría        | 14:00-19:00 |
| Dr. Roberto Vega     | Cardiología      | 9:00-17:00  |
| Dra. Carmen Díaz     | Cardiología      | 11:00-18:00 |

### Sucursal 2: Clínica Norte

- **Dirección**: Av. de la Prensa N58-120 y Río Coca, Quito
- **Horario**: Lun-Vie 9:00-18:00

| Categoría              | Servicios              | Precio | Duración |
| ---------------------- | ---------------------- | ------ | -------- |
| **Servicios Dentales** | Limpieza Dental        | $30    | 30 min   |
|                        | Curación Dental        | $25    | 25 min   |
|                        | Revisión Dental        | $15    | 20 min   |
| **Dermatología**       | Consulta Dermatológica | $35    | 30 min   |
|                        | Tratamiento de Acné    | $45    | 40 min   |

| Empleado           | Especialidad | Horario     |
| ------------------ | ------------ | ----------- |
| Dra. María López   | Odontología  | 9:00-17:00  |
| Dr. Carlos Andrade | Odontología  | 12:00-18:00 |
| Dr. Felipe Herrera | Odontología  | 9:00-14:00  |
| Dra. Ana Martínez  | Dermatología | 9:00-16:00  |
| Dr. Javier Paredes | Dermatología | 13:00-18:00 |

---

## Troubleshooting

### Error: "No se encontró archivo de credenciales"

```
FileNotFoundError: No se encontró archivo de credenciales
```

**Solución**: Descarga las credenciales de Google Cloud Console y colócalas en `config/google_credentials.json`

### Error: "Access blocked: This app's request is invalid"

**Solución**:

1. Verifica que agregaste tu email como "Test user" en OAuth consent screen
2. Elimina `config/token.json` y vuelve a autenticar

### Error: "Calendar not found"

**Solución**: Ejecuta `python scripts/local_setup.py --calendars` para crear los calendarios automáticamente.

### La base de datos no se crea

```bash
rm -rf data/
python scripts/local_setup.py
```

### Error: "Container not initialized"

**Solución**: Asegúrate de llamar `set_container(create_sqlite_container())` antes de usar el agente.

---

## Licencia

Proyecto de demostración. Uso interno.
