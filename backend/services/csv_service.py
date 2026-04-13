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

HEADERS = [
    "Appointment ID", "Account", "Customer",
    "Service", "Date", "Time", "Technician", "Status",
]

SEED_APPOINTMENTS = [
    {
        "Appointment ID": "APT-4101",
        "Account": "ACC-1001",
        "Customer": "Maria Garcia",
        "Service": "Spring AC Tune-Up",
        "Date": "2026-04-12",
        "Time": "08:30 AM",
        "Technician": "Carlos",
        "Status": "Scheduled",
    },
    {
        "Appointment ID": "APT-4102",
        "Account": "ACC-1002",
        "Customer": "James Thompson",
        "Service": "Blower Motor Repair",
        "Date": "2026-04-12",
        "Time": "11:00 AM",
        "Technician": "Sophie",
        "Status": "Scheduled",
    },
    {
        "Appointment ID": "APT-4103",
        "Account": "ACC-1003",
        "Customer": "Priya Patel",
        "Service": "Thermostat Replacement",
        "Date": "2026-04-13",
        "Time": "09:00 AM",
        "Technician": "Jake",
        "Status": "Scheduled",
    },
    {
        "Appointment ID": "APT-4104",
        "Account": "ACC-1004",
        "Customer": "David Kim",
        "Service": "Duct Inspection",
        "Date": "2026-04-13",
        "Time": "02:00 PM",
        "Technician": "Maria",
        "Status": "Scheduled",
    },
    {
        "Appointment ID": "APT-4105",
        "Account": "ACC-1002",
        "Customer": "James Thompson",
        "Service": "Emergency No-Cool Diagnostic",
        "Date": "2026-04-14",
        "Time": "08:00 AM",
        "Technician": "Carlos",
        "Status": "Scheduled",
    },
    {
        "Appointment ID": "APT-4106",
        "Account": "ACC-1001",
        "Customer": "Maria Garcia",
        "Service": "Filter Delivery and Install",
        "Date": "2026-04-14",
        "Time": "01:30 PM",
        "Technician": "Maria",
        "Status": "Rescheduled",
    },
    {
        "Appointment ID": "APT-4107",
        "Account": "ACC-1005",
        "Customer": "Eleanor Price",
        "Service": "Mini-Split Maintenance",
        "Date": "2026-04-15",
        "Time": "10:00 AM",
        "Technician": "Sophie",
        "Status": "Scheduled",
    },
    {
        "Appointment ID": "APT-4108",
        "Account": "ACC-1006",
        "Customer": "Noah Bennett",
        "Service": "Coil Cleaning",
        "Date": "2026-04-15",
        "Time": "03:30 PM",
        "Technician": "Jake",
        "Status": "Scheduled",
    },
    {
        "Appointment ID": "APT-4109",
        "Account": "ACC-1007",
        "Customer": "Ava Ramirez",
        "Service": "System Replacement Estimate",
        "Date": "2026-04-16",
        "Time": "09:30 AM",
        "Technician": "Maria",
        "Status": "Scheduled",
    },
    {
        "Appointment ID": "APT-4110",
        "Account": "ACC-1008",
        "Customer": "Liam Foster",
        "Service": "Drain Line Flush",
        "Date": "2026-04-16",
        "Time": "12:30 PM",
        "Technician": "Carlos",
        "Status": "Cancelled",
    },
    {
        "Appointment ID": "APT-4111",
        "Account": "ACC-1009",
        "Customer": "Grace Chen",
        "Service": "Heat Pump Inspection",
        "Date": "2026-04-18",
        "Time": "10:30 AM",
        "Technician": "Jake",
        "Status": "Scheduled",
    },
    {
        "Appointment ID": "APT-4112",
        "Account": "ACC-1010",
        "Customer": "Mason Reed",
        "Service": "Condenser Fan Replacement",
        "Date": "2026-04-18",
        "Time": "02:30 PM",
        "Technician": "Sophie",
        "Status": "Scheduled",
    },
]


def _csv_path() -> Path:
    """Resolve the appointment CSV from the current environment."""
    return Path(os.environ.get("APPOINTMENTS_CSV", "appointments.csv"))


def _ensure_file() -> None:
    """Create the CSV file with headers if it doesn't exist yet."""
    csv_path = _csv_path()
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    if not csv_path.exists():
        with open(csv_path, "w", newline="") as f:
            csv.DictWriter(f, fieldnames=HEADERS).writeheader()


def ensure_seed_data() -> None:
    """Populate the CSV with workshop demo data when it is empty."""
    _ensure_file()
    rows = _read_all()
    if rows:
        return
    _write_all(SEED_APPOINTMENTS)


def _read_all() -> list[dict]:
    """Return all rows as a list of dicts."""
    _ensure_file()
    with open(_csv_path(), newline="") as f:
        return list(csv.DictReader(f))


def _write_all(rows: list[dict]) -> None:
    """Overwrite the CSV file with the given rows."""
    with open(_csv_path(), "w", newline="") as f:
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
        csv_path = _csv_path()
        with open(csv_path, "a", newline="") as f:
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
        return {"success": True, "file": str(csv_path)}
    except Exception as e:
        return {"error": str(e)}


def list_appointments() -> list[dict]:
    """Return all appointments, seeding the CSV for demos if needed."""
    ensure_seed_data()
    return _read_all()


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
        return {"success": True, "file": str(_csv_path())}
    except Exception as e:
        return {"error": str(e)}


def reschedule_appointment_row(
    appointment_id: str, new_date: str, new_time: str, new_technician: str | None = None
) -> dict:
    """Find the appointment by ID and update its date, time, and status."""
    try:
        rows = _read_all()
        found = False
        for row in rows:
            if row["Appointment ID"] == appointment_id:
                row["Date"]   = new_date
                row["Time"]   = new_time
                if new_technician:
                    row["Technician"] = new_technician
                row["Status"] = "Rescheduled"
                found = True
                break
        if not found:
            return {"error": f"Appointment {appointment_id} not found in CSV."}
        _write_all(rows)
        return {"success": True, "file": str(_csv_path())}
    except Exception as e:
        return {"error": str(e)}
