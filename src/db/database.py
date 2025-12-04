"""
Database - SQLite connection and queries
"""
import sqlite3
from pathlib import Path
from typing import Optional, Any
from contextlib import contextmanager
from datetime import datetime, date, time
from decimal import Decimal

# Path to database file
DB_PATH = Path(__file__).parent.parent.parent / "data" / "mock_ai.db"


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


# Register adapters and converters
sqlite3.register_adapter(date, adapt_date)
sqlite3.register_adapter(time, adapt_time)
sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_adapter(Decimal, adapt_decimal)
sqlite3.register_converter("DATE", convert_date)
sqlite3.register_converter("TIME", convert_time)
sqlite3.register_converter("DATETIME", convert_datetime)
sqlite3.register_converter("DECIMAL", convert_decimal)


class Database:
    """SQLite database wrapper"""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()

    @contextmanager
    def get_connection(self):
        """Get a database connection with row factory"""
        conn = sqlite3.connect(
            self.db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
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
        """Initialize all database tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Clients table
            cursor.execute("""
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
                    bot_name TEXT DEFAULT 'mock_ai',
                    greeting_message TEXT,
                    whatsapp_number TEXT,
                    ai_model TEXT DEFAULT 'gpt-4o-mini',
                    created_at DATETIME,
                    updated_at DATETIME,
                    is_active INTEGER DEFAULT 1
                )
            """)

            # Branches table
            cursor.execute("""
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
            """)

            # Categories table
            cursor.execute("""
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
            """)

            # Services table
            cursor.execute("""
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
            """)

            # Calendars table
            cursor.execute("""
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
            """)

            # Calendar-Service relationship (many-to-many)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS calendar_services (
                    id TEXT PRIMARY KEY,
                    calendar_id TEXT NOT NULL,
                    service_id TEXT NOT NULL,
                    created_at DATETIME,
                    FOREIGN KEY (calendar_id) REFERENCES calendars(id),
                    FOREIGN KEY (service_id) REFERENCES services(id),
                    UNIQUE(calendar_id, service_id)
                )
            """)

            # Users table
            cursor.execute("""
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
            """)

            # Appointments table
            cursor.execute("""
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
            """)

            # Sessions table (WhatsApp sessions)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    client_id TEXT NOT NULL,
                    user_id TEXT,
                    phone_number TEXT NOT NULL,
                    memory_profile_key TEXT,
                    created_at DATETIME,
                    last_activity_at DATETIME,
                    FOREIGN KEY (client_id) REFERENCES clients(id),
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)

            # Conversations table
            cursor.execute("""
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
            """)

            # Messages table
            cursor.execute("""
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
            """)

            # Create indexes for common queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_branches_client ON branches(client_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_categories_branch ON categories(branch_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_services_branch ON services(branch_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_services_category ON services(category_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_calendars_branch ON calendars(branch_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_appointments_user ON appointments(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_appointments_calendar ON appointments(calendar_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments(appointment_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone_number)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_identification ON users(identification_number)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_phone ON sessions(phone_number)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id)")

    # =========================================================================
    # Client queries
    # =========================================================================

    def get_client(self, client_id: str) -> Optional[dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM clients WHERE id = ?", (client_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_client_by_whatsapp(self, whatsapp_number: str) -> Optional[dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM clients WHERE whatsapp_number = ?", (whatsapp_number,))
            row = cursor.fetchone()
            return dict(row) if row else None

    # =========================================================================
    # Branch queries
    # =========================================================================

    def get_branches_by_client(self, client_id: str) -> list[dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM branches WHERE client_id = ? AND is_active = 1",
                (client_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_branch(self, branch_id: str) -> Optional[dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM branches WHERE id = ?", (branch_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    # =========================================================================
    # Category queries
    # =========================================================================

    def get_categories_by_branch(self, branch_id: str) -> list[dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM categories WHERE branch_id = ? AND is_active = 1 ORDER BY display_order",
                (branch_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    # =========================================================================
    # Service queries
    # =========================================================================

    def get_services_by_branch(self, branch_id: str) -> list[dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT s.*, c.name as category_name
                   FROM services s
                   JOIN categories c ON s.category_id = c.id
                   WHERE s.branch_id = ? AND s.is_active = 1""",
                (branch_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_services_by_category(self, category_id: str) -> list[dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM services WHERE category_id = ? AND is_active = 1",
                (category_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_service(self, service_id: str) -> Optional[dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM services WHERE id = ?", (service_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def find_service_by_name(self, branch_id: str, name: str) -> Optional[dict]:
        """Find service by partial name match"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM services
                   WHERE branch_id = ? AND is_active = 1
                   AND LOWER(name) LIKE LOWER(?)""",
                (branch_id, f"%{name}%")
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    # =========================================================================
    # Calendar queries
    # =========================================================================

    def get_calendars_by_branch(self, branch_id: str) -> list[dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM calendars WHERE branch_id = ? AND is_active = 1",
                (branch_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_calendars_for_service(self, service_id: str) -> list[dict]:
        """Get all calendars that can provide a specific service"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT c.* FROM calendars c
                   JOIN calendar_services cs ON c.id = cs.calendar_id
                   WHERE cs.service_id = ? AND c.is_active = 1""",
                (service_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_calendar(self, calendar_id: str) -> Optional[dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM calendars WHERE id = ?", (calendar_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def find_calendar_by_name(self, branch_id: str, name: str) -> Optional[dict]:
        """Find calendar by partial name match"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM calendars
                   WHERE branch_id = ? AND is_active = 1
                   AND LOWER(name) LIKE LOWER(?)""",
                (branch_id, f"%{name}%")
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    # =========================================================================
    # User queries
    # =========================================================================

    def get_user(self, user_id: str) -> Optional[dict]:
        """Get user by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_user_by_phone(self, client_id: str, phone_number: str) -> Optional[dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM users WHERE client_id = ? AND phone_number = ?",
                (client_id, phone_number)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_user_by_identification(self, client_id: str, identification_number: str) -> Optional[dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM users WHERE client_id = ? AND identification_number = ?",
                (client_id, identification_number)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def create_user(self, user_data: dict) -> dict:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO users (id, client_id, phone_number, identification_number,
                   full_name, email, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    user_data["id"],
                    user_data["client_id"],
                    user_data["phone_number"],
                    user_data["identification_number"],
                    user_data["full_name"],
                    user_data.get("email"),
                    datetime.now(),
                    datetime.now()
                )
            )
            return user_data

    # =========================================================================
    # Appointment queries
    # =========================================================================

    def get_appointments_by_user(self, user_id: str) -> list[dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM appointments
                   WHERE user_id = ?
                   ORDER BY appointment_date DESC, start_time DESC""",
                (user_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_upcoming_appointments_by_user(self, user_id: str) -> list[dict]:
        """Get future appointments for a user"""
        today = date.today()
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM appointments
                   WHERE user_id = ? AND appointment_date >= ? AND status = 'scheduled'
                   ORDER BY appointment_date, start_time""",
                (user_id, today)
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_appointments_by_calendar_and_date(
        self, calendar_id: str, appointment_date: date
    ) -> list[dict]:
        """Get all appointments for a calendar on a specific date"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM appointments
                   WHERE calendar_id = ? AND appointment_date = ? AND status = 'scheduled'
                   ORDER BY start_time""",
                (calendar_id, appointment_date)
            )
            return [dict(row) for row in cursor.fetchall()]

    def create_appointment(self, appointment_data: dict) -> dict:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO appointments (
                    id, user_id, calendar_id, service_id, branch_id,
                    service_name_snapshot, service_price_snapshot, service_duration_snapshot,
                    calendar_name_snapshot, appointment_date, start_time, end_time,
                    google_event_id, status, notes, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    appointment_data["id"],
                    appointment_data["user_id"],
                    appointment_data["calendar_id"],
                    appointment_data["service_id"],
                    appointment_data["branch_id"],
                    appointment_data["service_name_snapshot"],
                    appointment_data["service_price_snapshot"],
                    appointment_data["service_duration_snapshot"],
                    appointment_data["calendar_name_snapshot"],
                    appointment_data["appointment_date"],
                    appointment_data["start_time"],
                    appointment_data["end_time"],
                    appointment_data.get("google_event_id"),
                    appointment_data.get("status", "scheduled"),
                    appointment_data.get("notes"),
                    datetime.now(),
                    datetime.now()
                )
            )
            return appointment_data

    def cancel_appointment(self, appointment_id: str, reason: str, cancelled_by: str) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE appointments
                   SET status = 'cancelled', cancellation_reason = ?,
                       cancelled_at = ?, cancelled_by = ?, updated_at = ?
                   WHERE id = ?""",
                (reason, datetime.now(), cancelled_by, datetime.now(), appointment_id)
            )
            return cursor.rowcount > 0

    def get_appointment(self, appointment_id: str) -> Optional[dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM appointments WHERE id = ?", (appointment_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    # =========================================================================
    # Session queries
    # =========================================================================

    def get_or_create_session(self, client_id: str, phone_number: str) -> dict:
        """Get existing session or create new one"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM sessions WHERE client_id = ? AND phone_number = ?",
                (client_id, phone_number)
            )
            row = cursor.fetchone()
            if row:
                # Update last activity
                cursor.execute(
                    "UPDATE sessions SET last_activity_at = ? WHERE id = ?",
                    (datetime.now(), row["id"])
                )
                return dict(row)

            # Create new session
            import uuid
            session_id = str(uuid.uuid4())
            cursor.execute(
                """INSERT INTO sessions (id, client_id, phone_number, created_at, last_activity_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (session_id, client_id, phone_number, datetime.now(), datetime.now())
            )
            return {
                "id": session_id,
                "client_id": client_id,
                "phone_number": phone_number,
                "user_id": None,
                "memory_profile_key": None,
                "created_at": datetime.now(),
                "last_activity_at": datetime.now()
            }

    def link_session_to_user(self, session_id: str, user_id: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE sessions SET user_id = ? WHERE id = ?",
                (user_id, session_id)
            )

    # =========================================================================
    # Conversation queries
    # =========================================================================

    def get_active_conversation(self, session_id: str, timeout_hours: int = 2) -> Optional[dict]:
        """Get active conversation within timeout window"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM conversations
                   WHERE session_id = ? AND status = 'active'
                   AND last_message_at > datetime('now', ?)
                   ORDER BY created_at DESC LIMIT 1""",
                (session_id, f"-{timeout_hours} hours")
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def create_conversation(self, session_id: str) -> dict:
        import uuid
        conversation_id = str(uuid.uuid4())
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO conversations (id, session_id, status, created_at, last_message_at)
                   VALUES (?, ?, 'active', ?, ?)""",
                (conversation_id, session_id, datetime.now(), datetime.now())
            )
            return {
                "id": conversation_id,
                "session_id": session_id,
                "status": "active",
                "escalated_to_chatwoot": False,
                "message_count": 0,
                "created_at": datetime.now(),
                "last_message_at": datetime.now()
            }

    def update_conversation_summary(self, conversation_id: str, summary: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE conversations
                   SET summary = ?, summary_updated_at = ?
                   WHERE id = ?""",
                (summary, datetime.now(), conversation_id)
            )

    def escalate_conversation(self, conversation_id: str, reason: str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """UPDATE conversations
                   SET escalated_to_chatwoot = 1, escalated_at = ?, escalation_reason = ?
                   WHERE id = ?""",
                (datetime.now(), reason, conversation_id)
            )

    # =========================================================================
    # Message queries
    # =========================================================================

    def add_message(self, conversation_id: str, role: str, content: str,
                    tool_call_id: str = None, tool_name: str = None) -> dict:
        import uuid
        message_id = str(uuid.uuid4())
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO messages (id, conversation_id, role, content, tool_call_id, tool_name, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (message_id, conversation_id, role, content, tool_call_id, tool_name, datetime.now())
            )
            # Update conversation
            cursor.execute(
                """UPDATE conversations
                   SET message_count = message_count + 1, last_message_at = ?
                   WHERE id = ?""",
                (datetime.now(), conversation_id)
            )
            return {
                "id": message_id,
                "conversation_id": conversation_id,
                "role": role,
                "content": content,
                "created_at": datetime.now()
            }

    def get_conversation_messages(self, conversation_id: str, limit: int = None) -> list[dict]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at"
            if limit:
                query += f" DESC LIMIT {limit}"
                cursor.execute(query, (conversation_id,))
                rows = cursor.fetchall()
                return [dict(row) for row in reversed(rows)]
            else:
                cursor.execute(query, (conversation_id,))
                return [dict(row) for row in cursor.fetchall()]


# Singleton instance
_db_instance: Optional[Database] = None


def get_db() -> Database:
    """Get database singleton instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
