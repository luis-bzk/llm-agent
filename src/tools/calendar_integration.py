"""Google Calendar Integration.

This integration looks for "mock_ai" events in the calendar to determine availability.
"mock_ai" events mark time blocks where the employee is available.

Example:
- "mock_ai" event from 9:00 to 17:00 = employee available from 9 to 17
- Any other event in that range = booked time
"""

import os
from datetime import datetime, date, time, timedelta
from typing import Optional
from pathlib import Path

from ..constants.config_keys import ConfigDefaults

from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/calendar"]

CREDENTIALS_PATH = Path(
    os.getenv(
        "GOOGLE_CALENDAR_CREDENTIALS_PATH",
        Path(__file__).parent.parent.parent / "config" / "google_credentials.json",
    )
)
TOKEN_PATH = Path(__file__).parent.parent.parent / "config" / "token.json"


class GoogleCalendarClient:
    """Client for interacting with Google Calendar API."""

    def __init__(self):
        self.service = None
        self._authenticate()

    def _authenticate(self):
        """Authenticates with Google Calendar API."""
        creds = None

        if TOKEN_PATH.exists():
            creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            elif CREDENTIALS_PATH.exists():
                import json

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
                raise FileNotFoundError(
                    f"No se encontró archivo de credenciales en {CREDENTIALS_PATH}. "
                    "Por favor configura GOOGLE_CALENDAR_CREDENTIALS_PATH o coloca el archivo."
                )

        self.service = build("calendar", "v3", credentials=creds)

    def get_mock_ai_availability(
        self, calendar_id: str, target_date: date
    ) -> list[tuple[time, time]]:
        """Gets availability blocks based on "mock_ai" events.

        Args:
            calendar_id: Google Calendar ID.
            target_date: Date to search availability.

        Returns:
            List of (start_time, end_time) tuples where availability exists.
        """
        try:
            start_datetime = datetime.combine(target_date, time(0, 0))
            end_datetime = datetime.combine(target_date, time(23, 59, 59))

            print(f"[GCAL DEBUG] Searching calendar: {calendar_id}")
            print(f"[GCAL DEBUG] Date range: {start_datetime} to {end_datetime}")

            events_result = (
                self.service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=start_datetime.isoformat() + "Z",
                    timeMax=end_datetime.isoformat() + "Z",
                    singleEvents=True,
                    orderBy="startTime",
                    q="mock_ai",
                )
                .execute()
            )

            mock_ai_events = events_result.get("items", [])
            print(
                f"[GCAL DEBUG] Found {len(mock_ai_events)} events with 'mock_ai' query"
            )

            for event in mock_ai_events:
                print(
                    f"[GCAL DEBUG] Event: '{event.get('summary')}' - Start: {event['start']} - End: {event['end']}"
                )

            availability_blocks = []
            for event in mock_ai_events:
                summary = event.get("summary", "").lower()
                if "mock_ai" in summary:
                    start = event["start"].get("dateTime", event["start"].get("date"))
                    end = event["end"].get("dateTime", event["end"].get("date"))

                    start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                    end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))

                    availability_blocks.append((start_dt.time(), end_dt.time()))
                    print(
                        f"[GCAL DEBUG] Added availability block: {start_dt.time()} - {end_dt.time()}"
                    )

            return availability_blocks

        except HttpError as e:
            print(f"[GCAL ERROR] Error accessing Google Calendar: {e}")
            return []

    def get_booked_slots(
        self, calendar_id: str, target_date: date, exclude_mock_ai: bool = True
    ) -> list[tuple[time, time]]:
        """Gets already booked slots (events that are NOT "mock_ai").

        Args:
            calendar_id: Calendar ID.
            target_date: Date to check.
            exclude_mock_ai: Whether to exclude "mock_ai" events (default True).

        Returns:
            List of (start_time, end_time) tuples for booked slots.
        """
        try:
            start_datetime = datetime.combine(target_date, time(0, 0))
            end_datetime = datetime.combine(target_date, time(23, 59, 59))

            events_result = (
                self.service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=start_datetime.isoformat() + "Z",
                    timeMax=end_datetime.isoformat() + "Z",
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            all_events = events_result.get("items", [])

            booked_slots = []
            for event in all_events:
                summary = event.get("summary", "").lower()

                if exclude_mock_ai and "mock_ai" in summary:
                    continue

                start = event["start"].get("dateTime", event["start"].get("date"))
                end = event["end"].get("dateTime", event["end"].get("date"))

                if "T" in start:
                    start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                    end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))

                    booked_slots.append((start_dt.time(), end_dt.time()))

            return booked_slots

        except HttpError as e:
            print(f"Error accessing Google Calendar: {e}")
            return []

    def create_appointment_event(
        self,
        calendar_id: str,
        summary: str,
        start_datetime: datetime,
        end_datetime: datetime,
        description: str = None,
    ) -> Optional[str]:
        """Creates an appointment event in Google Calendar.

        Args:
            calendar_id: Google Calendar ID.
            summary: Event title.
            start_datetime: Event start.
            end_datetime: Event end.
            description: Event description.

        Returns:
            Created event ID or None if failed.
        """
        try:
            event = {
                "summary": summary,
                "description": description or "",
                "start": {
                    "dateTime": start_datetime.isoformat(),
                    "timeZone": "America/Guayaquil",
                },
                "end": {
                    "dateTime": end_datetime.isoformat(),
                    "timeZone": "America/Guayaquil",
                },
            }

            created_event = (
                self.service.events()
                .insert(calendarId=calendar_id, body=event)
                .execute()
            )

            return created_event.get("id")

        except HttpError as e:
            print(f"Error creating event: {e}")
            return None

    def delete_event(self, calendar_id: str, event_id: str) -> bool:
        """Deletes an event from the calendar."""
        try:
            self.service.events().delete(
                calendarId=calendar_id, eventId=event_id
            ).execute()
            return True
        except HttpError as e:
            print(f"Error deleting event: {e}")
            return False


def calculate_available_slots(
    availability_blocks: list[tuple[time, time]],
    booked_slots: list[tuple[time, time]],
    duration_minutes: int,
    slot_interval_minutes: int = int(ConfigDefaults.DEFAULT_SLOT_INTERVAL_MINUTES),
) -> list[time]:
    """Calculates available slots based on availability blocks and booked slots.

    Args:
        availability_blocks: Blocks where availability exists (from "mock_ai" events).
        booked_slots: Already booked slots.
        duration_minutes: Service duration.
        slot_interval_minutes: Interval between slots (default 15 min).

    Returns:
        List of available start times.
    """
    available_slots = []

    for avail_start, avail_end in availability_blocks:
        avail_start_mins = avail_start.hour * 60 + avail_start.minute
        avail_end_mins = avail_end.hour * 60 + avail_end.minute

        current_mins = avail_start_mins
        while current_mins + duration_minutes <= avail_end_mins:
            slot_start = time(current_mins // 60, current_mins % 60)
            slot_end_mins = current_mins + duration_minutes
            slot_end = time(slot_end_mins // 60, slot_end_mins % 60)

            is_available = True
            for booked_start, booked_end in booked_slots:
                booked_start_mins = booked_start.hour * 60 + booked_start.minute
                booked_end_mins = booked_end.hour * 60 + booked_end.minute

                if not (
                    slot_end_mins <= booked_start_mins
                    or current_mins >= booked_end_mins
                ):
                    is_available = False
                    break

            if is_available:
                available_slots.append(slot_start)

            current_mins += slot_interval_minutes

    return available_slots


_calendar_client: Optional[GoogleCalendarClient] = None


def get_calendar_client() -> GoogleCalendarClient:
    """Gets the Google Calendar client (singleton)."""
    global _calendar_client
    if _calendar_client is None:
        _calendar_client = GoogleCalendarClient()
    return _calendar_client
