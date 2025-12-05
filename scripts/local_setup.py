#!/usr/bin/env python3
"""Local Testing Setup - Seeds database and creates Google Calendars.

This script is for LOCAL TESTING ONLY. It:
1. Seeds the SQLite database with demo data (client, branches, services, calendars)
2. Seeds system configuration (AI model settings, etc.)
3. Optionally creates Google Calendars and updates the database with their IDs

Usage:
    python scripts/local_setup.py              # Seed only
    python scripts/local_setup.py --calendars  # Seed + create Google Calendars
"""

import argparse
import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime, time, timedelta
from pathlib import Path

from dotenv import load_dotenv

# Load .env file from project root
SCRIPT_DIR = Path(__file__).parent.parent
load_dotenv(SCRIPT_DIR / ".env")

# Validate AGENT_NAME at startup
AGENT_NAME = os.getenv("AGENT_NAME")
if not AGENT_NAME:
    print("=" * 70)
    print("ERROR: AGENT_NAME environment variable is required")
    print("=" * 70)
    print("\nPlease set the AGENT_NAME environment variable before running setup.")
    print("Example:")
    print("  export AGENT_NAME=Virsi")
    print("  python scripts/local_setup.py --calendars")
    print()
    sys.exit(1)

# Paths (SCRIPT_DIR already defined above for loading .env)
DB_PATH = SCRIPT_DIR / "data" / "agent.db"
CREDENTIALS_PATH = SCRIPT_DIR / "config" / "google_credentials.json"
TOKEN_PATH = SCRIPT_DIR / "config" / "token.json"

SCOPES = ["https://www.googleapis.com/auth/calendar"]


# =============================================================================
# EMPLOYEE CONFIGURATION
# =============================================================================
# Working days: MO,TU,WE,TH,FR,SA (RFC 5545 format for RRULE)
WORKING_DAYS_CENTRO = "MO,TU,WE,TH,FR,SA"  # Lun-Sáb
WORKING_DAYS_NORTE = "MO,TU,WE,TH,FR"  # Lun-Vie

EMPLOYEES = {
    # Branch 1: Clínica Centro (Lun-Sáb)
    "mario_gomez": {
        "name": "Dr. Mario Gómez",
        "email": "mario.gomez@clinicassaludtotal.com",
        "start_time": time(8, 0),
        "end_time": time(16, 0),
        "working_days": WORKING_DAYS_CENTRO,
    },
    "laura_rodriguez": {
        "name": "Dra. Laura Rodríguez",
        "email": "laura.rodriguez@clinicassaludtotal.com",
        "start_time": time(10, 0),
        "end_time": time(18, 0),
        "working_days": WORKING_DAYS_CENTRO,
    },
    "susana_torres": {
        "name": "Dra. Susana Torres",
        "email": "susana.torres@clinicassaludtotal.com",
        "start_time": time(8, 0),
        "end_time": time(14, 0),
        "working_days": WORKING_DAYS_CENTRO,
    },
    "pedro_morales": {
        "name": "Dr. Pedro Morales",
        "email": "pedro.morales@clinicassaludtotal.com",
        "start_time": time(14, 0),
        "end_time": time(19, 0),
        "working_days": WORKING_DAYS_CENTRO,
    },
    "roberto_vega": {
        "name": "Dr. Roberto Vega",
        "email": "roberto.vega@clinicassaludtotal.com",
        "start_time": time(9, 0),
        "end_time": time(17, 0),
        "working_days": WORKING_DAYS_CENTRO,
    },
    "carmen_diaz": {
        "name": "Dra. Carmen Díaz",
        "email": "carmen.diaz@clinicassaludtotal.com",
        "start_time": time(11, 0),
        "end_time": time(18, 0),
        "working_days": WORKING_DAYS_CENTRO,
    },
    # Branch 2: Clínica Norte (Lun-Vie)
    "maria_lopez": {
        "name": "Dra. María López",
        "email": "maria.lopez@clinicassaludtotal.com",
        "start_time": time(9, 0),
        "end_time": time(17, 0),
        "working_days": WORKING_DAYS_NORTE,
    },
    "carlos_andrade": {
        "name": "Dr. Carlos Andrade",
        "email": "carlos.andrade@clinicassaludtotal.com",
        "start_time": time(12, 0),
        "end_time": time(18, 0),
        "working_days": WORKING_DAYS_NORTE,
    },
    "felipe_herrera": {
        "name": "Dr. Felipe Herrera",
        "email": "felipe.herrera@clinicassaludtotal.com",
        "start_time": time(9, 0),
        "end_time": time(14, 0),
        "working_days": WORKING_DAYS_NORTE,
    },
    "ana_martinez": {
        "name": "Dra. Ana Martínez",
        "email": "ana.martinez@clinicassaludtotal.com",
        "start_time": time(9, 0),
        "end_time": time(16, 0),
        "working_days": WORKING_DAYS_NORTE,
    },
    "javier_paredes": {
        "name": "Dr. Javier Paredes",
        "email": "javier.paredes@clinicassaludtotal.com",
        "start_time": time(13, 0),
        "end_time": time(18, 0),
        "working_days": WORKING_DAYS_NORTE,
    },
}

# System configuration defaults
SYSTEM_CONFIG = [
    ("ai_model", "gpt-4o-mini", "AI model to use for responses"),
    ("ai_temperature", "0.7", "Temperature for AI model responses"),
    ("ai_max_tokens", "1024", "Maximum tokens for AI responses"),
    ("summary_message_threshold", "10", "Messages before creating summary"),
    ("conversation_timeout_hours", "2", "Hours before conversation expires"),
    ("max_messages_in_context", "20", "Maximum messages to send to LLM"),
    ("default_booking_window_days", "30", "Days ahead for booking"),
    ("default_slot_interval_minutes", "15", "Minutes between appointment slots"),
    ("max_tool_retries", "3", "Maximum retries for tool calls"),
]


def generate_id(name: str) -> str:
    """Generates a deterministic UUID based on name for idempotent inserts."""
    return hashlib.md5(name.encode()).hexdigest()


def time_to_str(t: time) -> str:
    """Converts time to string for SQLite."""
    return t.strftime("%H:%M:%S")


def get_connection() -> sqlite3.Connection:
    """Gets SQLite connection. Creates tables if needed."""
    import sys

    sys.path.insert(0, str(SCRIPT_DIR))

    # Use SQLiteConnection to ensure tables are created
    from src.repositories.sqlite.connection import SQLiteConnection

    SQLiteConnection(str(DB_PATH))  # This calls _init_tables()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def seed_system_config(cursor: sqlite3.Cursor):
    """Seeds system configuration."""
    print("\n📋 Seeding system configuration...")

    now = datetime.now().isoformat()
    for key, value, description in SYSTEM_CONFIG:
        cursor.execute(
            """INSERT OR REPLACE INTO system_config (key, value, description, updated_at)
               VALUES (?, ?, ?, ?)""",
            (key, value, description, now),
        )
        print(f"   ✓ {key} = {value}")


def seed_demo_data(cursor: sqlite3.Cursor) -> str:
    """Seeds demo data for Clínicas Salud Total. Returns client_id."""
    print("\n" + "=" * 70)
    print("SEED DATA - Clínicas Salud Total")
    print("=" * 70)

    now = datetime.now().isoformat()

    # Client
    client_id = generate_id("client:clinicas_salud_total")
    cursor.execute(
        """INSERT OR REPLACE INTO clients (
            id, email, business_name, owner_name, phone,
            max_branches, max_calendars, max_appointments_monthly, booking_window_days,
            bot_name, greeting_message, whatsapp_number, appointment_type,
            created_at, updated_at, is_active
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            client_id,
            "alberto.mendoza@clinicassaludtotal.com",
            "Clínicas Salud Total",
            "Alberto Mendoza",
            "+593999000001",
            5,
            15,
            500,
            30,
            "Virsi",
            "¡Hola! Soy Virsi, el asistente virtual de Clínicas Salud Total. ¿En qué puedo ayudarte hoy?",
            "+593912345678",
            "virtual",  # appointment_type: presencial or virtual
            now,
            now,
            1,
        ),
    )
    print(f"\n✓ Client: Clínicas Salud Total")
    print(f"   WhatsApp: +593912345678")

    # Branch 1: Clínica Centro
    branch1_id = generate_id("branch:clinica_centro")
    cursor.execute(
        """INSERT OR REPLACE INTO branches (
            id, client_id, name, address, city,
            opening_time, closing_time, working_days, phone,
            created_at, updated_at, is_active
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            branch1_id,
            client_id,
            "Clínica Centro",
            "Av. 10 de Agosto N25-45 y Colón",
            "Quito",
            time_to_str(time(8, 0)),
            time_to_str(time(19, 0)),
            "1,2,3,4,5,6",
            "+593999100001",
            now,
            now,
            1,
        ),
    )
    print(f"\n✓ Branch 1: Clínica Centro")

    # Categories and Services for Branch 1
    cat_general = generate_id("category:consultas_generales")
    cursor.execute(
        """INSERT OR REPLACE INTO categories (id, branch_id, name, description, display_order, created_at, is_active)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            cat_general,
            branch1_id,
            "Consultas Generales",
            "Atención médica general",
            1,
            now,
            1,
        ),
    )

    svc_consulta = generate_id("service:consulta_general")
    svc_control = generate_id("service:control_medico")
    svc_chequeo = generate_id("service:chequeo_preventivo")
    for svc_id, name, desc, price, duration in [
        (svc_consulta, "Consulta General", "Consulta médica general", 20.00, 30),
        (svc_control, "Control Médico", "Seguimiento de tratamientos", 15.00, 20),
        (svc_chequeo, "Chequeo Preventivo", "Examen médico preventivo", 35.00, 45),
    ]:
        cursor.execute(
            """INSERT OR REPLACE INTO services (id, category_id, branch_id, name, description, price, duration_minutes, created_at, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (svc_id, cat_general, branch1_id, name, desc, price, duration, now, 1),
        )

    cat_pediatria = generate_id("category:pediatria")
    cursor.execute(
        """INSERT OR REPLACE INTO categories (id, branch_id, name, description, display_order, created_at, is_active)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (cat_pediatria, branch1_id, "Pediatría", "Atención para niños", 2, now, 1),
    )

    svc_pediatrica = generate_id("service:consulta_pediatrica")
    svc_nino_sano = generate_id("service:control_nino_sano")
    for svc_id, name, desc, price, duration in [
        (svc_pediatrica, "Consulta Pediátrica", "Consulta para niños", 25.00, 30),
        (svc_nino_sano, "Control de Niño Sano", "Seguimiento infantil", 18.00, 25),
    ]:
        cursor.execute(
            """INSERT OR REPLACE INTO services (id, category_id, branch_id, name, description, price, duration_minutes, created_at, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (svc_id, cat_pediatria, branch1_id, name, desc, price, duration, now, 1),
        )

    cat_cardio = generate_id("category:cardiologia")
    cursor.execute(
        """INSERT OR REPLACE INTO categories (id, branch_id, name, description, display_order, created_at, is_active)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (cat_cardio, branch1_id, "Cardiología", "Atención cardiovascular", 3, now, 1),
    )

    svc_cardio = generate_id("service:consulta_cardiologica")
    svc_electro = generate_id("service:electrocardiograma")
    for svc_id, name, desc, price, duration in [
        (svc_cardio, "Consulta Cardiológica", "Evaluación cardiovascular", 40.00, 40),
        (svc_electro, "Electrocardiograma", "Estudio del corazón", 30.00, 20),
    ]:
        cursor.execute(
            """INSERT OR REPLACE INTO services (id, category_id, branch_id, name, description, price, duration_minutes, created_at, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (svc_id, cat_cardio, branch1_id, name, desc, price, duration, now, 1),
        )

    # Calendars for Branch 1
    def create_calendar(key: str, branch_id: str) -> str:
        emp = EMPLOYEES[key]
        cal_id = generate_id(f"calendar:{key}")
        cursor.execute(
            """INSERT OR REPLACE INTO calendars (
                id, branch_id, name, google_calendar_id, google_account_email,
                default_start_time, default_end_time, created_at, updated_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                cal_id,
                branch_id,
                emp["name"],
                "",
                emp["email"],
                time_to_str(emp["start_time"]),
                time_to_str(emp["end_time"]),
                now,
                now,
                1,
            ),
        )
        return cal_id

    def link_services(calendar_id: str, service_ids: list):
        for svc_id in service_ids:
            cursor.execute(
                "INSERT OR REPLACE INTO calendar_services (id, calendar_id, service_id, created_at) VALUES (?, ?, ?, ?)",
                (
                    generate_id(f"cal_svc:{calendar_id}:{svc_id}"),
                    calendar_id,
                    svc_id,
                    now,
                ),
            )

    cal_mario = create_calendar("mario_gomez", branch1_id)
    link_services(cal_mario, [svc_consulta, svc_control, svc_chequeo])

    cal_laura = create_calendar("laura_rodriguez", branch1_id)
    link_services(cal_laura, [svc_consulta, svc_control])

    cal_susana = create_calendar("susana_torres", branch1_id)
    link_services(cal_susana, [svc_pediatrica, svc_nino_sano])

    cal_pedro = create_calendar("pedro_morales", branch1_id)
    link_services(cal_pedro, [svc_pediatrica, svc_nino_sano])

    cal_roberto = create_calendar("roberto_vega", branch1_id)
    link_services(cal_roberto, [svc_cardio, svc_electro])

    cal_carmen = create_calendar("carmen_diaz", branch1_id)
    link_services(cal_carmen, [svc_cardio, svc_electro])

    print(f"   6 calendars created")

    # Branch 2: Clínica Norte
    branch2_id = generate_id("branch:clinica_norte")
    cursor.execute(
        """INSERT OR REPLACE INTO branches (
            id, client_id, name, address, city,
            opening_time, closing_time, working_days, phone,
            created_at, updated_at, is_active
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            branch2_id,
            client_id,
            "Clínica Norte",
            "Av. de la Prensa N58-120 y Río Coca",
            "Quito",
            time_to_str(time(9, 0)),
            time_to_str(time(18, 0)),
            "1,2,3,4,5",
            "+593999100002",
            now,
            now,
            1,
        ),
    )
    print(f"\n✓ Branch 2: Clínica Norte")

    # Categories and Services for Branch 2
    cat_dental = generate_id("category:servicios_dentales")
    cursor.execute(
        """INSERT OR REPLACE INTO categories (id, branch_id, name, description, display_order, created_at, is_active)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            cat_dental,
            branch2_id,
            "Servicios Dentales",
            "Atención odontológica",
            1,
            now,
            1,
        ),
    )

    svc_limpieza = generate_id("service:limpieza_dental")
    svc_curacion = generate_id("service:curacion_dental")
    svc_revision = generate_id("service:revision_dental")
    for svc_id, name, desc, price, duration in [
        (svc_limpieza, "Limpieza Dental", "Limpieza profesional", 30.00, 30),
        (svc_curacion, "Curación Dental", "Restauración de caries", 25.00, 25),
        (svc_revision, "Revisión Dental", "Examen dental", 15.00, 20),
    ]:
        cursor.execute(
            """INSERT OR REPLACE INTO services (id, category_id, branch_id, name, description, price, duration_minutes, created_at, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (svc_id, cat_dental, branch2_id, name, desc, price, duration, now, 1),
        )

    cat_dermato = generate_id("category:dermatologia")
    cursor.execute(
        """INSERT OR REPLACE INTO categories (id, branch_id, name, description, display_order, created_at, is_active)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (cat_dermato, branch2_id, "Dermatología", "Cuidado de la piel", 2, now, 1),
    )

    svc_dermato = generate_id("service:consulta_dermatologica")
    svc_acne = generate_id("service:tratamiento_acne")
    for svc_id, name, desc, price, duration in [
        (svc_dermato, "Consulta Dermatológica", "Evaluación de piel", 35.00, 30),
        (svc_acne, "Tratamiento de Acné", "Tratamiento especializado", 45.00, 40),
    ]:
        cursor.execute(
            """INSERT OR REPLACE INTO services (id, category_id, branch_id, name, description, price, duration_minutes, created_at, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (svc_id, cat_dermato, branch2_id, name, desc, price, duration, now, 1),
        )

    # Calendars for Branch 2
    cal_maria = create_calendar("maria_lopez", branch2_id)
    link_services(cal_maria, [svc_limpieza, svc_curacion, svc_revision])

    cal_carlos = create_calendar("carlos_andrade", branch2_id)
    link_services(cal_carlos, [svc_limpieza, svc_curacion])

    cal_felipe = create_calendar("felipe_herrera", branch2_id)
    link_services(cal_felipe, [svc_limpieza, svc_curacion, svc_revision])

    cal_ana = create_calendar("ana_martinez", branch2_id)
    link_services(cal_ana, [svc_dermato, svc_acne])

    cal_javier = create_calendar("javier_paredes", branch2_id)
    link_services(cal_javier, [svc_dermato, svc_acne])

    print(f"   5 calendars created")

    return client_id


def get_google_service():
    """Authenticates and returns Google Calendar service."""
    from google.oauth2.credentials import Credentials
    from google.oauth2 import service_account
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = None

    if TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif CREDENTIALS_PATH.exists():
            with open(CREDENTIALS_PATH) as f:
                creds_data = json.load(f)

            if creds_data.get("type") == "service_account":
                creds = service_account.Credentials.from_service_account_file(
                    str(CREDENTIALS_PATH), scopes=SCOPES
                )
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(CREDENTIALS_PATH), SCOPES
                )
                creds = flow.run_local_server(port=0)

            if hasattr(creds, "refresh_token"):
                TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
                with open(TOKEN_PATH, "w") as token:
                    token.write(creds.to_json())
        else:
            raise FileNotFoundError(f"No credentials at {CREDENTIALS_PATH}")

    return build("calendar", "v3", credentials=creds)


def setup_google_calendars(cursor: sqlite3.Cursor):
    """Creates Google Calendars for all employees."""
    from googleapiclient.errors import HttpError

    print("\n" + "=" * 70)
    print("GOOGLE CALENDAR SETUP")
    print("=" * 70)

    print("\n📡 Connecting to Google Calendar API...")
    try:
        service = get_google_service()
        print("   ✓ Connected")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        print(f"   Make sure credentials exist at {CREDENTIALS_PATH}")
        return

    # Get all calendars
    cursor.execute(
        """
        SELECT c.id, c.name, c.google_calendar_id, b.name as branch_name
        FROM calendars c
        JOIN branches b ON c.branch_id = b.id
        WHERE c.is_active = 1
        ORDER BY b.name, c.name
    """
    )
    calendars = cursor.fetchall()

    created = 0
    skipped = 0
    current_branch = None

    for cal in calendars:
        if cal["branch_name"] != current_branch:
            current_branch = cal["branch_name"]
            print(f"\n🏢 {current_branch}")

        # Skip if already configured
        if (
            cal["google_calendar_id"]
            and "@group.calendar.google.com" in cal["google_calendar_id"]
        ):
            try:
                service.calendars().get(calendarId=cal["google_calendar_id"]).execute()
                print(f"   ⏭️  {cal['name']} - exists")
                skipped += 1
                continue
            except HttpError:
                pass

        # Create calendar
        print(f"   📅 Creating: {cal['name']}...")
        try:
            calendar_body = {
                "summary": cal["name"],
                "description": f"Calendar for {cal['name']} - {cal['branch_name']}",
                "timeZone": "America/Guayaquil",
            }
            new_cal = service.calendars().insert(body=calendar_body).execute()
            google_id = new_cal["id"]

            cursor.execute(
                "UPDATE calendars SET google_calendar_id = ? WHERE id = ?",
                (google_id, cal["id"]),
            )

            print(f"      ✓ {google_id[:40]}...")
            created += 1

        except HttpError as e:
            print(f"      ✗ Error: {e}")

    print(f"\n   Created: {created}, Skipped: {skipped}")

    # After creating calendars, create availability marker events
    create_availability_events(cursor, service)


def create_availability_events(cursor: sqlite3.Cursor, service):
    """Creates recurring availability marker events for all calendars."""
    from googleapiclient.errors import HttpError

    marker_name = AGENT_NAME.lower()

    print("\n" + "=" * 70)
    print("CREATING AVAILABILITY MARKER EVENTS")
    print("=" * 70)

    # Get calendars with their schedule info
    cursor.execute(
        """
        SELECT c.id, c.name, c.google_calendar_id,
               c.default_start_time, c.default_end_time,
               b.name as branch_name
        FROM calendars c
        JOIN branches b ON c.branch_id = b.id
        WHERE c.is_active = 1 AND c.google_calendar_id != ''
        ORDER BY b.name, c.name
    """
    )
    calendars = cursor.fetchall()

    created = 0
    skipped = 0
    current_branch = None

    for cal in calendars:
        if cal["branch_name"] != current_branch:
            current_branch = cal["branch_name"]
            print(f"\n🏢 {current_branch}")

        google_calendar_id = cal["google_calendar_id"]
        if not google_calendar_id:
            print(f"   ⏭️  {cal['name']} - no Google Calendar ID")
            skipped += 1
            continue

        # Find employee config by matching name
        employee_config = None
        for key, emp in EMPLOYEES.items():
            if emp["name"] == cal["name"]:
                employee_config = emp
                break

        if not employee_config:
            print(f"   ⏭️  {cal['name']} - no employee config found")
            skipped += 1
            continue

        # Check if marker event already exists
        try:
            events = (
                service.events()
                .list(
                    calendarId=google_calendar_id,
                    q=marker_name,
                    maxResults=1,
                )
                .execute()
            )

            if events.get("items"):
                print(f"   ⏭️  {cal['name']} - marker event exists")
                skipped += 1
                continue
        except HttpError as e:
            print(f"   ✗ {cal['name']} - error checking: {e}")
            continue

        # Create recurring marker event
        start_time = employee_config["start_time"]
        end_time = employee_config["end_time"]
        working_days = employee_config["working_days"]

        # Start from next Monday
        today = datetime.now().date()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        next_monday = today + timedelta(days=days_until_monday)

        start_datetime = datetime.combine(next_monday, start_time)
        end_datetime = datetime.combine(next_monday, end_time)

        event_body = {
            "summary": marker_name,
            "description": f"Disponibilidad de {cal['name']} para citas",
            "start": {
                "dateTime": start_datetime.isoformat(),
                "timeZone": "America/Guayaquil",
            },
            "end": {
                "dateTime": end_datetime.isoformat(),
                "timeZone": "America/Guayaquil",
            },
            "recurrence": [f"RRULE:FREQ=WEEKLY;BYDAY={working_days}"],
        }

        try:
            service.events().insert(
                calendarId=google_calendar_id, body=event_body
            ).execute()

            days_display = working_days.replace(",", ", ")
            print(
                f"   ✓ {cal['name']} - {start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')} ({days_display})"
            )
            created += 1

        except HttpError as e:
            print(f"   ✗ {cal['name']} - error: {e}")

    print(f"\n   Created: {created}, Skipped: {skipped}")


def main():
    parser = argparse.ArgumentParser(description="Local testing setup")
    parser.add_argument(
        "--calendars",
        action="store_true",
        help="Also create Google Calendars",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("LOCAL SETUP - Scheduling Agent")
    print("=" * 70)

    conn = get_connection()
    cursor = conn.cursor()

    try:
        seed_system_config(cursor)
        client_id = seed_demo_data(cursor)
        conn.commit()

        if args.calendars:
            setup_google_calendars(cursor)
            conn.commit()

        print("\n" + "=" * 70)
        print("SETUP COMPLETE")
        print("=" * 70)
        print(f"\nClient ID: {client_id}")
        print(f"WhatsApp: +593912345678")
        print(f"\nTo test: python test_chat.py")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
