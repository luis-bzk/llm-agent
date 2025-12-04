# mock_ai Agent - Demo de Agendación de Citas

Agente conversacional de LangGraph para agendación de citas médicas por WhatsApp.

## Tabla de Contenidos

1. [Requisitos Previos](#requisitos-previos)
2. [Instalación](#instalación)
3. [Configuración de Google Calendar](#configuración-de-google-calendar)
4. [Configuración de Calendarios para el Demo](#configuración-de-calendarios-para-el-demo)
5. [Variables de Entorno](#variables-de-entorno)
6. [Ejecución](#ejecución)
7. [Estructura del Proyecto](#estructura-del-proyecto)
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

### Verificar SQLite (Mac)

SQLite viene preinstalado en macOS. Verifica con:

```bash
sqlite3 --version
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

#### Paso 5: Primera autenticación

La primera vez que ejecutes el agente, se abrirá un navegador para autorizar el acceso. Esto genera un `token.json` que se reutiliza después.

---

### Opción B: Service Account (Para producción)

Si prefieres usar una Service Account (sin intervención manual):

1. En Google Cloud Console, ve a **IAM & Admin** → **Service Accounts**
2. Crea una nueva Service Account
3. Descarga la clave JSON
4. Renómbrala a `google_credentials.json` y colócala en `config/`
5. **Importante**: Comparte cada calendario de Google con el email de la Service Account

---

## Configuración de Calendarios para el Demo

El sistema usa **eventos llamados "mock_ai"** para determinar la disponibilidad de cada empleado. Un evento "mock_ai" indica las horas en que el empleado puede recibir citas.

### Crear Calendarios en Google Calendar

Necesitas crear **11 calendarios secundarios** en tu cuenta de Google Calendar (o usar una cuenta de prueba).

#### Paso 1: Crear los calendarios

En Google Calendar (calendar.google.com):

1. En el panel izquierdo, click en **+** junto a "Other calendars"
2. Selecciona **Create new calendar**
3. Crea cada uno de los siguientes calendarios:

| # | Nombre del Calendario | Google Calendar ID (usar este nombre) |
|---|----------------------|---------------------------------------|
| 1 | Dr. Mario Gómez | `cal-mario-gomez@demo.com` |
| 2 | Dra. Laura Rodríguez | `cal-laura-rodriguez@demo.com` |
| 3 | Dra. Susana Torres | `cal-susana-torres@demo.com` |
| 4 | Dr. Pedro Morales | `cal-pedro-morales@demo.com` |
| 5 | Dr. Roberto Vega | `cal-roberto-vega@demo.com` |
| 6 | Dra. Carmen Díaz | `cal-carmen-diaz@demo.com` |
| 7 | Dra. María López | `cal-maria-lopez@demo.com` |
| 8 | Dr. Carlos Andrade | `cal-carlos-andrade@demo.com` |
| 9 | Dr. Felipe Herrera | `cal-felipe-herrera@demo.com` |
| 10 | Dra. Ana Martínez | `cal-ana-martinez@demo.com` |
| 11 | Dr. Javier Paredes | `cal-javier-paredes@demo.com` |

#### Paso 2: Obtener el Calendar ID real

Después de crear cada calendario:

1. Click en los **⋮** (tres puntos) junto al calendario
2. Selecciona **Settings and sharing**
3. Baja hasta **Integrate calendar**
4. Copia el **Calendar ID** (algo como `abc123xyz@group.calendar.google.com`)

#### Paso 3: Actualizar el seed con los Calendar IDs reales

Edita `src/db/seed.py` - todos los Calendar IDs están centralizados en el diccionario `CALENDARIOS` al inicio del archivo:

```python
CALENDARIOS = {
    "mario_gomez": {
        "nombre": "Dr. Mario Gómez",
        "google_calendar_id": "TU_CALENDAR_ID_AQUI",  # ← CAMBIA ESTO
        "email": "mario.gomez@clinicassaludtotal.com",
        "horario_inicio": time(8, 0),
        "horario_fin": time(16, 0),
    },
    # ... resto de calendarios
}
```

Solo necesitas editar el campo `google_calendar_id` de cada entrada con el ID real que copiaste de Google Calendar.

---

### Configurar Eventos "mock_ai" de Disponibilidad

El agente determina cuándo un empleado está disponible buscando eventos llamados **"mock_ai"** en su calendario.

#### Crear eventos "mock_ai" para cada calendario

Para cada calendario, crea eventos recurrentes llamados **"mock_ai"** según los horarios del seed:

---

#### 📅 SUCURSAL 1: CLÍNICA CENTRO

| Calendario | Días | Horario | Evento "mock_ai" a crear |
|------------|------|---------|------------------------|
| **Dr. Mario Gómez** | Lun-Sáb | 8:00-16:00 | Crear evento recurrente "mock_ai" de 8:00 a 16:00, repite Lun-Sáb |
| **Dra. Laura Rodríguez** | Lun-Sáb | 10:00-18:00 | Crear evento recurrente "mock_ai" de 10:00 a 18:00, repite Lun-Sáb |
| **Dra. Susana Torres** | Lun-Sáb | 8:00-14:00 | Crear evento recurrente "mock_ai" de 8:00 a 14:00, repite Lun-Sáb |
| **Dr. Pedro Morales** | Lun-Sáb | 14:00-19:00 | Crear evento recurrente "mock_ai" de 14:00 a 19:00, repite Lun-Sáb |
| **Dr. Roberto Vega** | Lun-Sáb | 9:00-17:00 | Crear evento recurrente "mock_ai" de 9:00 a 17:00, repite Lun-Sáb |
| **Dra. Carmen Díaz** | Lun-Sáb | 11:00-18:00 | Crear evento recurrente "mock_ai" de 11:00 a 18:00, repite Lun-Sáb |

---

#### 📅 SUCURSAL 2: CLÍNICA NORTE

| Calendario | Días | Horario | Evento "mock_ai" a crear |
|------------|------|---------|------------------------|
| **Dra. María López** | Lun-Vie | 9:00-17:00 | Crear evento recurrente "mock_ai" de 9:00 a 17:00, repite Lun-Vie |
| **Dr. Carlos Andrade** | Lun-Vie | 12:00-18:00 | Crear evento recurrente "mock_ai" de 12:00 a 18:00, repite Lun-Vie |
| **Dr. Felipe Herrera** | Lun-Vie | 9:00-14:00 | Crear evento recurrente "mock_ai" de 9:00 a 14:00, repite Lun-Vie |
| **Dra. Ana Martínez** | Lun-Vie | 9:00-16:00 | Crear evento recurrente "mock_ai" de 9:00 a 16:00, repite Lun-Vie |
| **Dr. Javier Paredes** | Lun-Vie | 13:00-18:00 | Crear evento recurrente "mock_ai" de 13:00 a 18:00, repite Lun-Vie |

---

#### Cómo crear un evento recurrente "mock_ai"

1. En Google Calendar, selecciona el calendario del empleado (ej: "Dr. Mario Gómez")
2. Click en una fecha/hora para crear evento
3. **Título**: `mock_ai` (exactamente así, en minúsculas)
4. **Hora inicio**: Según tabla (ej: 8:00)
5. **Hora fin**: Según tabla (ej: 16:00)
6. Click en **More options**
7. En **Does not repeat**, cambia a:
   - **Custom...**
   - Repeat every: 1 week
   - Selecciona los días: Lun, Mar, Mié, Jue, Vie (y Sáb si aplica)
   - Ends: Never (o una fecha lejana)
8. Asegúrate que el evento esté en el calendario correcto (no el principal)
9. **Save**

#### Ejemplo Visual

```
Calendario: Dr. Mario Gómez
┌────────────────────────────────────────────────────────────┐
│  Lunes 2 Dic    │  Martes 3 Dic   │  Miércoles 4 Dic      │
├────────────────────────────────────────────────────────────┤
│  ┌──────────┐   │  ┌──────────┐   │  ┌──────────┐         │
│  │  mock_ai   │   │  │  mock_ai   │   │  │  mock_ai   │         │
│  │ 8:00 AM  │   │  │ 8:00 AM  │   │  │ 8:00 AM  │         │
│  │    -     │   │  │    -     │   │  │    -     │         │
│  │ 4:00 PM  │   │  │ 4:00 PM  │   │  │ 4:00 PM  │         │
│  └──────────┘   │  └──────────┘   │  └──────────┘         │
└────────────────────────────────────────────────────────────┘
```

---

### Agregar bloques de almuerzo (Opcional)

Si quieres simular horarios de almuerzo, crea eventos adicionales:

```
Calendario: Dr. Mario Gómez
Evento: "Almuerzo" (cualquier nombre que NO sea "mock_ai")
Hora: 12:00 - 13:00
Recurrencia: Lun-Vie

El agente verá este bloque como "ocupado" y no agendará citas ahí.
```

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

### 1. Inicializar la base de datos y cargar datos de prueba

```bash
# Desde el directorio mock_ai-agent
python -m src.db.seed
```

Esto creará:
- Base de datos SQLite en `data/mock_ai.db`
- 1 Cliente (Clínicas Salud Total)
- 2 Sucursales
- 5 Categorías
- 12 Servicios
- 11 Calendarios

### 2. Ejecutar el CLI de prueba (Recomendado para testing)

```bash
python test_chat.py
```

Este CLI interactivo te permite:
- Chatear con el agente en tiempo real
- Ver logs detallados de cada nodo del grafo
- Ver las llamadas a tools y sus resultados
- Inspeccionar el estado interno

**Comandos especiales en el CLI:**
| Comando | Descripción |
|---------|-------------|
| `/quit`, `/exit`, `/q` | Salir del CLI |
| `/clear` | Iniciar nueva conversación (simula timeout) |
| `/db` | Ver mensajes guardados en BD |
| `/state` | Ver estado actual del agente |

### 3. Ejecutar con LangGraph Studio

```bash
# Iniciar el servidor de desarrollo
langgraph dev
```

Esto abrirá:
- **API**: http://127.0.0.1:2024
- **Studio UI**: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
- **API Docs**: http://127.0.0.1:2024/docs

En Studio podrás:
- Visualizar el grafo del agente
- Enviar mensajes de prueba
- Ver los estados y transiciones
- Inspeccionar las llamadas a tools

### 4. Resetear la base de datos

Si necesitas empezar de cero:

```bash
# Eliminar BD existente
rm -f data/mock_ai.db

# Recrear con datos de prueba
python -m src.db.seed
```

---

## Estructura del Proyecto

```
mock_ai-agent/
├── config/                      # Credenciales
│   ├── google_credentials.json  # Credenciales de Google (tú lo creas)
│   └── token.json               # Token OAuth (auto-generado)
│
├── data/                        # Base de datos
│   └── mock_ai.db                 # SQLite (auto-generado)
│
├── src/
│   ├── agent.py                 # Grafo principal de LangGraph
│   ├── state.py                 # Definición del estado
│   ├── prompts.py               # System prompts
│   │
│   ├── db/
│   │   ├── database.py          # Wrapper SQLite
│   │   └── seed.py              # Datos de ejemplo
│   │
│   ├── models/                  # Modelos Pydantic
│   │   ├── client.py
│   │   ├── branch.py
│   │   ├── service.py
│   │   └── ...
│   │
│   ├── memory/                  # Sistema de memoria 3 niveles
│   │   ├── short_term.py        # Últimos 6 mensajes
│   │   ├── long_term.py         # Resumen de conversación
│   │   └── total.py             # Perfil persistente
│   │
│   └── tools/                   # Herramientas del agente
│       ├── services.py          # Consulta de servicios
│       ├── availability.py      # Consulta de disponibilidad
│       ├── appointments.py      # Crear/cancelar citas
│       ├── user.py              # Gestión de usuarios
│       └── calendar_integration.py  # Google Calendar API
│
├── scripts/
│   ├── demo.py                  # Demo interactiva
│   └── seed_data.py             # Script de seed
│
├── .env                         # Variables de entorno
├── .env.example                 # Template de variables
├── langgraph.json               # Configuración LangGraph
├── requirements.txt             # Dependencias Python
└── README.md                    # Este archivo
```

---

## Datos de Prueba

### Cliente: Clínicas Salud Total

- **WhatsApp**: +593912345678
- **Ventana de agendación**: 30 días

### Sucursal 1: Clínica Centro

- **Dirección**: Av. 10 de Agosto N25-45 y Colón, Quito
- **Horario**: Lun-Sáb 8:00-19:00

| Categoría | Servicios | Precio | Duración |
|-----------|-----------|--------|----------|
| **Consultas Generales** | Consulta General | $20 | 30 min |
| | Control Médico | $15 | 20 min |
| | Chequeo Preventivo | $35 | 45 min |
| **Pediatría** | Consulta Pediátrica | $25 | 30 min |
| | Control de Niño Sano | $18 | 25 min |
| **Cardiología** | Consulta Cardiológica | $40 | 40 min |
| | Electrocardiograma | $30 | 20 min |

| Empleado | Especialidad | Horario |
|----------|--------------|---------|
| Dr. Mario Gómez | Medicina General | 8:00-16:00 |
| Dra. Laura Rodríguez | Medicina General | 10:00-18:00 |
| Dra. Susana Torres | Pediatría | 8:00-14:00 |
| Dr. Pedro Morales | Pediatría | 14:00-19:00 |
| Dr. Roberto Vega | Cardiología | 9:00-17:00 |
| Dra. Carmen Díaz | Cardiología | 11:00-18:00 |

### Sucursal 2: Clínica Norte

- **Dirección**: Av. de la Prensa N58-120 y Río Coca, Quito
- **Horario**: Lun-Vie 9:00-18:00

| Categoría | Servicios | Precio | Duración |
|-----------|-----------|--------|----------|
| **Servicios Dentales** | Limpieza Dental | $30 | 30 min |
| | Curación Dental | $25 | 25 min |
| | Revisión Dental | $15 | 20 min |
| **Dermatología** | Consulta Dermatológica | $35 | 30 min |
| | Tratamiento de Acné | $45 | 40 min |

| Empleado | Especialidad | Horario |
|----------|--------------|---------|
| Dra. María López | Odontología | 9:00-17:00 |
| Dr. Carlos Andrade | Odontología | 12:00-18:00 |
| Dr. Felipe Herrera | Odontología | 9:00-14:00 |
| Dra. Ana Martínez | Dermatología | 9:00-16:00 |
| Dr. Javier Paredes | Dermatología | 13:00-18:00 |

---

## Ejemplos de Conversación

### Ejemplo 1: Agendar cita simple

```
Usuario: Hola
mock_ai: ¡Hola! Soy mock_ai, el asistente virtual de Clínicas Salud Total.
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

### Ejemplo 2: Buscar por especialista

```
Usuario: Necesito cita con la Dra. Susana Torres
mock_ai: La Dra. Susana Torres trabaja en Clínica Centro y atiende:
       - Consulta Pediátrica ($25, 30 min)
       - Control de Niño Sano ($18, 25 min)
       Su horario es de 8:00 a 14:00, Lunes a Sábado.
       ¿Qué servicio necesitas?
```

---

## Troubleshooting

### Error: "No se encontró archivo de credenciales"

```
FileNotFoundError: No se encontró archivo de credenciales en ./config/google_credentials.json
```

**Solución**: Descarga las credenciales de Google Cloud Console y colócalas en `config/google_credentials.json`

### Error: "Access blocked: This app's request is invalid"

**Solución**:
1. Verifica que agregaste tu email como "Test user" en OAuth consent screen
2. Elimina `config/token.json` y vuelve a autenticar

### Error: "Calendar not found"

**Solución**: Verifica que:
1. Creaste los calendarios en Google Calendar
2. Actualizaste los Calendar IDs en `seed.py` con los IDs reales
3. Si usas Service Account, compartiste los calendarios con el email de la Service Account

### La base de datos no se crea

```bash
# Eliminar y recrear
rm -rf data/
mkdir data
python -m src.db.seed
```

---

## Licencia

Proyecto de demostración. Uso interno.
