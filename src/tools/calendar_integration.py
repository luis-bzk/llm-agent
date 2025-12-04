"""
Google Calendar Integration

Esta integración busca eventos "mock_ai" en el calendario para determinar disponibilidad.
Los eventos "mock_ai" marcan los bloques de tiempo donde el empleado está disponible.

Ejemplo:
- Evento "mock_ai" de 9:00 a 17:00 en un día = empleado disponible de 9 a 17
- Cualquier otro evento en ese rango = tiempo ocupado
"""

import os
from datetime import datetime, date, time, timedelta
from typing import Optional
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Scopes necesarios
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Path a credenciales
CREDENTIALS_PATH = Path(
    os.getenv(
        "GOOGLE_CALENDAR_CREDENTIALS_PATH",
        Path(__file__).parent.parent.parent / "config" / "google_credentials.json",
    )
)
TOKEN_PATH = Path(__file__).parent.parent.parent / "config" / "token.json"


class GoogleCalendarClient:
    """Cliente para interactuar con Google Calendar API"""

    def __init__(self):
        self.service = None
        self._authenticate()

    def _authenticate(self):
        """Autenticar con Google Calendar API"""
        creds = None

        # Intentar cargar token existente
        if TOKEN_PATH.exists():
            creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

        # Si no hay credenciales válidas, autenticar
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            elif CREDENTIALS_PATH.exists():
                # Verificar si es service account o OAuth
                import json

                with open(CREDENTIALS_PATH) as f:
                    creds_data = json.load(f)

                if creds_data.get("type") == "service_account":
                    # Service Account
                    creds = service_account.Credentials.from_service_account_file(
                        str(CREDENTIALS_PATH), scopes=SCOPES
                    )
                else:
                    # OAuth flow
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(CREDENTIALS_PATH), SCOPES
                    )
                    creds = flow.run_local_server(port=0)

                # Guardar token para futuro uso (solo OAuth)
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
        """
        Obtiene los bloques de disponibilidad basándose en eventos "mock_ai".

        Args:
            calendar_id: ID del calendario en Google
            target_date: Fecha para buscar disponibilidad

        Returns:
            Lista de tuplas (start_time, end_time) donde hay disponibilidad
        """
        try:
            # Rango de búsqueda: todo el día
            start_datetime = datetime.combine(target_date, time(0, 0))
            end_datetime = datetime.combine(target_date, time(23, 59, 59))

            print(f"[GCAL DEBUG] Searching calendar: {calendar_id}")
            print(f"[GCAL DEBUG] Date range: {start_datetime} to {end_datetime}")

            # Buscar eventos "mock_ai" (definen disponibilidad)
            events_result = (
                self.service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=start_datetime.isoformat() + "Z",
                    timeMax=end_datetime.isoformat() + "Z",
                    singleEvents=True,
                    orderBy="startTime",
                    q="mock_ai",  # Buscar eventos que contengan "mock_ai"
                )
                .execute()
            )

            mock_ai_events = events_result.get("items", [])
            print(f"[GCAL DEBUG] Found {len(mock_ai_events)} events with 'mock_ai' query")

            # Log todos los eventos encontrados
            for event in mock_ai_events:
                print(
                    f"[GCAL DEBUG] Event: '{event.get('summary')}' - Start: {event['start']} - End: {event['end']}"
                )

            availability_blocks = []
            for event in mock_ai_events:
                # Solo considerar eventos que se llamen exactamente "mock_ai" o contengan "mock_ai"
                summary = event.get("summary", "").lower()
                if "mock_ai" in summary:
                    start = event["start"].get("dateTime", event["start"].get("date"))
                    end = event["end"].get("dateTime", event["end"].get("date"))

                    # Parsear tiempos
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
        """
        Obtiene los slots ya ocupados (eventos que NO son "mock_ai").

        Args:
            calendar_id: ID del calendario
            target_date: Fecha a verificar
            exclude_mock_ai: Si excluir eventos "mock_ai" (default True)

        Returns:
            Lista de tuplas (start_time, end_time) de slots ocupados
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

                # Excluir eventos "mock_ai" si se solicita
                if exclude_mock_ai and "mock_ai" in summary:
                    continue

                start = event["start"].get("dateTime", event["start"].get("date"))
                end = event["end"].get("dateTime", event["end"].get("date"))

                # Solo eventos con hora específica (no todo el día)
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
        """
        Crea un evento de cita en Google Calendar.

        Returns:
            ID del evento creado o None si falla
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
        """Elimina un evento del calendario"""
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
    slot_interval_minutes: int = 15,
) -> list[time]:
    """
    Calcula los slots disponibles basándose en bloques de disponibilidad y slots ocupados.

    Args:
        availability_blocks: Bloques donde hay disponibilidad (de eventos "mock_ai")
        booked_slots: Slots ya ocupados por otras citas
        duration_minutes: Duración del servicio
        slot_interval_minutes: Intervalo entre slots (default 15 min)

    Returns:
        Lista de horas de inicio disponibles
    """
    available_slots = []

    for avail_start, avail_end in availability_blocks:
        # Convertir a minutos desde medianoche para facilitar cálculos
        avail_start_mins = avail_start.hour * 60 + avail_start.minute
        avail_end_mins = avail_end.hour * 60 + avail_end.minute

        # Iterar por cada posible slot
        current_mins = avail_start_mins
        while current_mins + duration_minutes <= avail_end_mins:
            slot_start = time(current_mins // 60, current_mins % 60)
            slot_end_mins = current_mins + duration_minutes
            slot_end = time(slot_end_mins // 60, slot_end_mins % 60)

            # Verificar que no colisione con ningún slot ocupado
            is_available = True
            for booked_start, booked_end in booked_slots:
                booked_start_mins = booked_start.hour * 60 + booked_start.minute
                booked_end_mins = booked_end.hour * 60 + booked_end.minute

                # Hay colisión si los rangos se superponen
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


# Cliente singleton
_calendar_client: Optional[GoogleCalendarClient] = None


def get_calendar_client() -> GoogleCalendarClient:
    """Obtiene el cliente de Google Calendar (singleton)"""
    global _calendar_client
    if _calendar_client is None:
        _calendar_client = GoogleCalendarClient()
    return _calendar_client
