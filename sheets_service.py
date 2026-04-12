"""
Google Sheets integration for AirPro HVAC Services.

Appointment data is written to a Google Sheet so the HVAC team always has
a live, up-to-date view of the schedule.

Setup (one-time):
  1. Go to console.cloud.google.com → create or reuse a project
  2. Enable the Google Sheets API
  3. Create OAuth 2.0 credentials → Desktop app
  4. Download and save as credentials.json in this directory
  5. Create a new Google Sheet — the header row will be added automatically
  6. Copy the Sheet ID from the URL:
       https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit
  7. Add to .env:
       GOOGLE_SHEET_ID=<your sheet id>
       GOOGLE_SHEET_TAB=Appointments   (optional, defaults to "Appointments")

On first run a browser window opens for OAuth consent.
After that, token.json is saved and reused automatically.
"""

import os
import gspread

# ── Config ─────────────────────────────────────────────────────────────────────

SPREADSHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "")
WORKSHEET_NAME = os.environ.get("GOOGLE_SHEET_TAB", "Appointments")

HEADERS = [
    "Appointment ID", "Account", "Customer",
    "Service", "Date", "Time", "Technician", "Status",
]

# Column indices (1-based) — must match HEADERS order
COL_APPT_ID   = 1
COL_ACCOUNT   = 2
COL_CUSTOMER  = 3
COL_SERVICE   = 4
COL_DATE      = 5
COL_TIME      = 6
COL_TECH      = 7
COL_STATUS    = 8


# ── Auth ───────────────────────────────────────────────────────────────────────

def get_worksheet() -> gspread.Worksheet:
    """Authenticate and return the Appointments worksheet, creating it if needed."""
    if not SPREADSHEET_ID:
        raise ValueError(
            "GOOGLE_SHEET_ID is not set in .env — add it and restart."
        )
    gc = gspread.oauth(
        credentials_filename="credentials.json",
        authorized_user_filename="token.json",
    )
    spreadsheet = gc.open_by_key(SPREADSHEET_ID)
    try:
        ws = spreadsheet.worksheet(WORKSHEET_NAME)
    except gspread.exceptions.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(
            title=WORKSHEET_NAME, rows=1000, cols=len(HEADERS)
        )
        ws.append_row(HEADERS)
    return ws


# ── Sheet operations ───────────────────────────────────────────────────────────

def add_appointment(
    appointment_id: str,
    account: str,
    customer: str,
    service: str,
    date: str,
    time: str,
    tech: str,
) -> dict:
    """Append a new row for a booked appointment."""
    try:
        ws = get_worksheet()
        ws.append_row(
            [appointment_id, account, customer, service, date, time, tech, "Scheduled"],
            value_input_option="USER_ENTERED",
        )
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


def cancel_appointment_row(appointment_id: str) -> dict:
    """Find the appointment row by ID and mark it as Cancelled."""
    try:
        ws = get_worksheet()
        cell = ws.find(appointment_id, in_column=COL_APPT_ID)
        if not cell:
            return {"error": f"Appointment {appointment_id} not found in sheet."}
        ws.update_cell(cell.row, COL_STATUS, "Cancelled")
        return {"success": True, "row": cell.row}
    except Exception as e:
        return {"error": str(e)}


def reschedule_appointment_row(appointment_id: str, new_date: str, new_time: str) -> dict:
    """Find the appointment row by ID and update its date, time, and status."""
    try:
        ws = get_worksheet()
        cell = ws.find(appointment_id, in_column=COL_APPT_ID)
        if not cell:
            return {"error": f"Appointment {appointment_id} not found in sheet."}
        ws.update_cell(cell.row, COL_DATE,   new_date)
        ws.update_cell(cell.row, COL_TIME,   new_time)
        ws.update_cell(cell.row, COL_STATUS, "Rescheduled")
        return {"success": True, "row": cell.row}
    except Exception as e:
        return {"error": str(e)}
