"""
CSV-based appointment tracking for AirPro HVAC Services.

Appointments are written to a local CSV file so the HVAC team can open it
in Excel, Google Sheets, or any spreadsheet tool at any time.

The file is created automatically on first use.
Configure the file path in .env: APPOINTMENTS_CSV=appointments.csv
"""

import csv
import os
from pathlib import Path

CSV_PATH = Path(os.environ.get("APPOINTMENTS_CSV", "appointments.csv"))

HEADERS = [
    "Appointment ID", "Account", "Customer",
    "Service", "Date", "Time", "Technician", "Status",
]


def _ensure_file() -> None:
    """Create the CSV file with headers if it doesn't exist yet."""
    if not CSV_PATH.exists():
        with open(CSV_PATH, "w", newline="") as f:
            csv.DictWriter(f, fieldnames=HEADERS).writeheader()


def _read_all() -> list[dict]:
    """Return all rows as a list of dicts."""
    _ensure_file()
    with open(CSV_PATH, newline="") as f:
        return list(csv.DictReader(f))


def _write_all(rows: list[dict]) -> None:
    """Overwrite the CSV file with the given rows."""
    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)


# ── Public operations ──────────────────────────────────────────────────────────

def add_appointment(
    appointment_id: str,
    account: str,
    customer: str,
    service: str,
    date: str,
    time: str,
    tech: str,
) -> dict:
    """Append a new appointment row to the CSV."""
    try:
        _ensure_file()
        with open(CSV_PATH, "a", newline="") as f:
            csv.DictWriter(f, fieldnames=HEADERS).writerow({
                "Appointment ID": appointment_id,
                "Account":        account,
                "Customer":       customer,
                "Service":        service,
                "Date":           date,
                "Time":           time,
                "Technician":     tech,
                "Status":         "Scheduled",
            })
        return {"success": True, "file": str(CSV_PATH)}
    except Exception as e:
        return {"error": str(e)}


def cancel_appointment_row(appointment_id: str) -> dict:
    """Find the appointment by ID and mark it as Cancelled."""
    try:
        rows = _read_all()
        found = False
        for row in rows:
            if row["Appointment ID"] == appointment_id:
                row["Status"] = "Cancelled"
                found = True
                break
        if not found:
            return {"error": f"Appointment {appointment_id} not found in CSV."}
        _write_all(rows)
        return {"success": True, "file": str(CSV_PATH)}
    except Exception as e:
        return {"error": str(e)}


def reschedule_appointment_row(
    appointment_id: str, new_date: str, new_time: str
) -> dict:
    """Find the appointment by ID and update its date, time, and status."""
    try:
        rows = _read_all()
        found = False
        for row in rows:
            if row["Appointment ID"] == appointment_id:
                row["Date"]   = new_date
                row["Time"]   = new_time
                row["Status"] = "Rescheduled"
                found = True
                break
        if not found:
            return {"error": f"Appointment {appointment_id} not found in CSV."}
        _write_all(rows)
        return {"success": True, "file": str(CSV_PATH)}
    except Exception as e:
        return {"error": str(e)}
