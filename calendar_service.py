"""
Google Calendar integration for AirPro HVAC Services.

Setup (one-time):
  1. Go to console.cloud.google.com and create a project
  2. Enable the Google Calendar API
  3. Create OAuth 2.0 credentials → Desktop app
  4. Download the file and save it as credentials.json in this directory
  5. Add GOOGLE_CALENDAR_ID to your .env (use "primary" or a dedicated HVAC calendar ID)

On first run, a browser window will open asking you to authorize access.
After that, a token.json file is saved and reused automatically.
"""

import os
import datetime as dt
from zoneinfo import ZoneInfo

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ── Config ─────────────────────────────────────────────────────────────────────

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"

# Set GOOGLE_CALENDAR_ID in .env — use "primary" or a shared HVAC team calendar
CALENDAR_ID = os.environ.get("GOOGLE_CALENDAR_ID", "primary")

# Timezone for your HVAC business (Georgia → Eastern)
TIMEZONE = os.environ.get("BUSINESS_TIMEZONE", "America/New_York")

# Default service appointment window in hours
APPOINTMENT_DURATION_HOURS = 2


# ── Auth ───────────────────────────────────────────────────────────────────────

def get_service():
    """Authenticate and return a Google Calendar API client."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    "credentials.json not found. "
                    "Download it from Google Cloud Console and place it in this directory."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
    return build("calendar", "v3", credentials=creds)


# ── Calendar operations ────────────────────────────────────────────────────────

def create_event(
    title: str,
    date: str,
    time: str,
    tech_name: str,
    customer_name: str = "",
    service_type: str = "",
) -> dict:
    """Create a Google Calendar event for a new HVAC appointment.

    Args:
        title:         Event title shown on the calendar
        date:          Date in YYYY-MM-DD format
        time:          Time in "H:MM AM/PM" format, e.g. "9:00 AM"
        tech_name:     Technician assigned to the job
        customer_name: Customer's full name
        service_type:  Type of service being performed

    Returns:
        dict with event_id and html_link, or error key on failure
    """
    try:
        service = get_service()
        tz = ZoneInfo(TIMEZONE)

        start = dt.datetime.strptime(f"{date} {time}", "%Y-%m-%d %I:%M %p").replace(tzinfo=tz)
        end = start + dt.timedelta(hours=APPOINTMENT_DURATION_HOURS)

        event_body = {
            "summary": title,
            "description": (
                f"Service: {service_type}\n"
                f"Customer: {customer_name}\n"
                f"Technician: {tech_name}\n"
                "— Booked via AirPro HVAC Voice Agent"
            ),
            "start": {"dateTime": start.isoformat(), "timeZone": TIMEZONE},
            "end":   {"dateTime": end.isoformat(),   "timeZone": TIMEZONE},
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email",  "minutes": 24 * 60},
                    {"method": "popup",  "minutes": 60},
                ],
            },
        }

        result = service.events().insert(calendarId=CALENDAR_ID, body=event_body).execute()
        return {"event_id": result["id"], "html_link": result.get("htmlLink", "")}

    except FileNotFoundError as e:
        return {"error": str(e)}
    except HttpError as e:
        return {"error": f"Google Calendar API error: {e}"}


def cancel_event(event_id: str) -> dict:
    """Delete a Google Calendar event.

    Args:
        event_id: The Google Calendar event ID stored at booking time

    Returns:
        dict with success flag or error key
    """
    try:
        service = get_service()
        service.events().delete(calendarId=CALENDAR_ID, eventId=event_id).execute()
        return {"success": True, "event_id": event_id}
    except HttpError as e:
        return {"error": f"Google Calendar API error: {e}"}


def update_event(event_id: str, new_date: str, new_time: str) -> dict:
    """Move an existing Google Calendar event to a new date and time.

    Args:
        event_id:  The Google Calendar event ID
        new_date:  New date in YYYY-MM-DD format
        new_time:  New time in "H:MM AM/PM" format

    Returns:
        dict with success flag or error key
    """
    try:
        service = get_service()
        tz = ZoneInfo(TIMEZONE)

        # Fetch the existing event to preserve its title, description, etc.
        event = service.events().get(calendarId=CALENDAR_ID, eventId=event_id).execute()

        start = dt.datetime.strptime(f"{new_date} {new_time}", "%Y-%m-%d %I:%M %p").replace(tzinfo=tz)
        end = start + dt.timedelta(hours=APPOINTMENT_DURATION_HOURS)

        event["start"] = {"dateTime": start.isoformat(), "timeZone": TIMEZONE}
        event["end"]   = {"dateTime": end.isoformat(),   "timeZone": TIMEZONE}

        updated = service.events().update(
            calendarId=CALENDAR_ID, eventId=event_id, body=event
        ).execute()

        return {
            "success": True,
            "event_id": updated["id"],
            "new_date": new_date,
            "new_time": new_time,
            "html_link": updated.get("htmlLink", ""),
        }
    except HttpError as e:
        return {"error": f"Google Calendar API error: {e}"}
