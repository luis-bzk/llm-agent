"""SQLite connection management."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, date, time
from decimal import Decimal
from pathlib import Path
from typing import Optional


DEFAULT_DB_PATH = Path(__file__).parent.parent.parent.parent / "data" / "mock_ai.db"


def adapt_date(val: date) -> str:
    return val.isoformat()


def adapt_time(val: time) -> str:
    return val.strftime("%H:%M:%S")


def adapt_datetime(val: datetime) -> str:
    return val.isoformat()


def adapt_decimal(val: Decimal) -> str:
    return str(val)


def convert_date(val: bytes) -> date:
    return date.fromisoformat(val.decode())


def convert_time(val: bytes) -> time:
    return time.fromisoformat(val.decode())


def convert_datetime(val: bytes) -> datetime:
    return datetime.fromisoformat(val.decode())


def convert_decimal(val: bytes) -> Decimal:
    return Decimal(val.decode())


sqlite3.register_adapter(date, adapt_date)
sqlite3.register_adapter(time, adapt_time)
sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_adapter(Decimal, adapt_decimal)
sqlite3.register_converter("DATE", convert_date)
sqlite3.register_converter("TIME", convert_time)
sqlite3.register_converter("DATETIME", convert_datetime)
sqlite3.register_converter("DECIMAL", convert_decimal)


class SQLiteConnection:
    """Manages SQLite connection with transaction context manager."""

    def __init__(self, db_path: Optional[str] = None):
        """Initializes connection.

        Args:
            db_path: Path to database file. Uses default if not specified.
        """
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = DEFAULT_DB_PATH

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()

    @contextmanager
    def get_connection(self):
        """Context manager for getting a connection with transaction."""
        conn = sqlite3.connect(
            self.db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        )
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_tables(self):
        """Initializes all database tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS system_config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    description TEXT,
                    created_at DATETIME,
                    updated_at DATETIME
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS clients (
                    id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    business_name TEXT NOT NULL,
                    owner_name TEXT NOT NULL,
                    phone TEXT,
                    plan_id TEXT,
                    max_branches INTEGER DEFAULT 1,
                    max_calendars INTEGER DEFAULT 1,
                    max_appointments_monthly INTEGER DEFAULT 50,
                    booking_window_days INTEGER DEFAULT 7,
                    bot_name TEXT DEFAULT 'Asistente',
                    greeting_message TEXT,
                    whatsapp_number TEXT,
                    created_at DATETIME,
                    updated_at DATETIME,
                    is_active INTEGER DEFAULT 1
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS branches (
                    id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    address TEXT NOT NULL,
                    city TEXT,
                    opening_time TIME,
                    closing_time TIME,
                    working_days TEXT DEFAULT '1,2,3,4,5',
                    phone TEXT,
                    created_at DATETIME,
                    updated_at DATETIME,
                    is_active INTEGER DEFAULT 1,
                    FOREIGN KEY (client_id) REFERENCES clients(id)
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS categories (
                    id TEXT PRIMARY KEY,
                    branch_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    display_order INTEGER DEFAULT 0,
                    created_at DATETIME,
                    is_active INTEGER DEFAULT 1,
                    FOREIGN KEY (branch_id) REFERENCES branches(id)
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS services (
                    id TEXT PRIMARY KEY,
                    category_id TEXT NOT NULL,
                    branch_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    price DECIMAL NOT NULL,
                    duration_minutes INTEGER NOT NULL,
                    created_at DATETIME,
                    is_active INTEGER DEFAULT 1,
                    FOREIGN KEY (category_id) REFERENCES categories(id),
                    FOREIGN KEY (branch_id) REFERENCES branches(id)
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS calendars (
                    id TEXT PRIMARY KEY,
                    branch_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    google_calendar_id TEXT NOT NULL,
                    google_account_email TEXT,
                    default_start_time TIME,
                    default_end_time TIME,
                    created_at DATETIME,
                    updated_at DATETIME,
                    is_active INTEGER DEFAULT 1,
                    FOREIGN KEY (branch_id) REFERENCES branches(id)
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS calendar_services (
                    id TEXT PRIMARY KEY,
                    calendar_id TEXT NOT NULL,
                    service_id TEXT NOT NULL,
                    created_at DATETIME,
                    FOREIGN KEY (calendar_id) REFERENCES calendars(id),
                    FOREIGN KEY (service_id) REFERENCES services(id),
                    UNIQUE(calendar_id, service_id)
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    phone_number TEXT NOT NULL,
                    identification_number TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    email TEXT,
                    created_at DATETIME,
                    updated_at DATETIME,
                    last_interaction_at DATETIME,
                    FOREIGN KEY (client_id) REFERENCES clients(id),
                    UNIQUE(client_id, identification_number)
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS appointments (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    calendar_id TEXT NOT NULL,
                    service_id TEXT NOT NULL,
                    branch_id TEXT NOT NULL,
                    service_name_snapshot TEXT NOT NULL,
                    service_price_snapshot DECIMAL NOT NULL,
                    service_duration_snapshot INTEGER NOT NULL,
                    calendar_name_snapshot TEXT NOT NULL,
                    appointment_date DATE NOT NULL,
                    start_time TIME NOT NULL,
                    end_time TIME NOT NULL,
                    google_event_id TEXT,
                    status TEXT DEFAULT 'scheduled',
                    cancellation_reason TEXT,
                    cancelled_at DATETIME,
                    cancelled_by TEXT,
                    notes TEXT,
                    reminder_sent INTEGER DEFAULT 0,
                    reminder_sent_at DATETIME,
                    created_at DATETIME,
                    updated_at DATETIME,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (calendar_id) REFERENCES calendars(id),
                    FOREIGN KEY (service_id) REFERENCES services(id),
                    FOREIGN KEY (branch_id) REFERENCES branches(id)
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    user_id TEXT,
                    phone_number TEXT NOT NULL,
                    memory_profile_key TEXT,
                    memory_profile TEXT,
                    memory_profile_updated_at DATETIME,
                    created_at DATETIME,
                    last_activity_at DATETIME,
                    FOREIGN KEY (client_id) REFERENCES clients(id),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    status TEXT DEFAULT 'active',
                    escalated_to_chatwoot INTEGER DEFAULT 0,
                    escalated_at DATETIME,
                    escalation_reason TEXT,
                    summary TEXT,
                    summary_updated_at DATETIME,
                    message_count INTEGER DEFAULT 0,
                    created_at DATETIME,
                    last_message_at DATETIME,
                    expired_at DATETIME,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                )
            """
            )

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tool_call_id TEXT,
                    tool_name TEXT,
                    created_at DATETIME,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                )
            """
            )

            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_branches_client ON branches(client_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_categories_branch ON categories(branch_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_services_branch ON services(branch_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_services_category ON services(category_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_calendars_branch ON calendars(branch_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_appointments_user ON appointments(user_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_appointments_calendar ON appointments(calendar_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments(appointment_date)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone_number)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_users_identification ON users(identification_number)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_sessions_phone ON sessions(phone_number)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id)"
            )
