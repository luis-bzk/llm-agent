#!/usr/bin/env python3
"""Local Cleanup - Deletes Google Calendars and database.

This script is for LOCAL TESTING ONLY. It:
1. Deletes all Google Calendars created by local_setup.py
2. Deletes the SQLite database

Usage:
    python scripts/local_cleanup.py              # Delete calendars + DB
    python scripts/local_cleanup.py --db-only    # Only delete DB (keep calendars)
"""

import argparse
import sqlite3
from pathlib import Path

# Paths
SCRIPT_DIR = Path(__file__).parent.parent
DB_PATH = SCRIPT_DIR / "data" / "agent.db"
CREDENTIALS_PATH = SCRIPT_DIR / "config" / "google_credentials.json"
TOKEN_PATH = SCRIPT_DIR / "config" / "token.json"

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_google_service():
    """Authenticates and returns Google Calendar service."""
    import json
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


def delete_google_calendars():
    """Deletes all Google Calendars from the database."""
    from googleapiclient.errors import HttpError

    print("\n" + "=" * 70)
    print("DELETING GOOGLE CALENDARS")
    print("=" * 70)

    if not DB_PATH.exists():
        print("\n   ⚠️  Database not found, nothing to delete")
        return

    # Get calendar IDs from database
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT c.name, c.google_calendar_id, b.name as branch_name
        FROM calendars c
        JOIN branches b ON c.branch_id = b.id
        WHERE c.google_calendar_id != '' AND c.google_calendar_id IS NOT NULL
        ORDER BY b.name, c.name
    """
    )
    calendars = cursor.fetchall()
    conn.close()

    if not calendars:
        print("\n   ⚠️  No Google Calendar IDs found in database")
        return

    print(f"\n   Found {len(calendars)} calendars to delete")

    print("\n📡 Connecting to Google Calendar API...")
    try:
        service = get_google_service()
        print("   ✓ Connected")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        print("   Calendars will remain in Google, but DB will be deleted")
        return

    deleted = 0
    failed = 0
    current_branch = None

    for cal in calendars:
        if cal["branch_name"] != current_branch:
            current_branch = cal["branch_name"]
            print(f"\n🏢 {current_branch}")

        google_calendar_id = cal["google_calendar_id"]

        try:
            service.calendars().delete(calendarId=google_calendar_id).execute()
            print(f"   ✓ Deleted: {cal['name']}")
            deleted += 1
        except HttpError as e:
            if e.resp.status == 404:
                print(f"   ⏭️  {cal['name']} - not found (already deleted?)")
            else:
                print(f"   ✗ {cal['name']} - error: {e}")
                failed += 1

    print(f"\n   Deleted: {deleted}, Failed: {failed}")


def delete_database():
    """Deletes the SQLite database file."""
    print("\n" + "=" * 70)
    print("DELETING DATABASE")
    print("=" * 70)

    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"\n   ✓ Deleted: {DB_PATH}")
    else:
        print(f"\n   ⚠️  Database not found: {DB_PATH}")


def main():
    parser = argparse.ArgumentParser(
        description="Local cleanup - delete calendars and database"
    )
    parser.add_argument(
        "--db-only",
        action="store_true",
        help="Only delete database (keep Google Calendars)",
    )
    parser.add_argument(
        "--calendars-only",
        action="store_true",
        help="Only delete Google Calendars (keep database)",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("LOCAL CLEANUP - Scheduling Agent")
    print("=" * 70)

    if args.db_only:
        delete_database()
    elif args.calendars_only:
        delete_google_calendars()
    else:
        delete_google_calendars()
        delete_database()

    print("\n" + "=" * 70)
    print("CLEANUP COMPLETE")
    print("=" * 70)
    print("\nTo recreate: python scripts/local_setup.py --calendars")


if __name__ == "__main__":
    main()
