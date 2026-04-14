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
        "Technician": "Ryan Majd",
        "Status": "Scheduled",
    },
    {
        "Appointment ID": "APT-4102",
        "Account": "ACC-1002",
        "Customer": "James Thompson",
        "Service": "Blower Motor Repair",
        "Date": "2026-04-12",
        "Time": "11:00 AM",
        "Technician": "Shishir Lohar",
        "Status": "Scheduled",
    },
    {
        "Appointment ID": "APT-4103",
        "Account": "ACC-1003",
        "Customer": "Priya Patel",
        "Service": "Thermostat Replacement",
        "Date": "2026-04-13",
        "Time": "09:00 AM",
        "Technician": "Yash Verma",
        "Status": "Scheduled",
    },
    {
        "Appointment ID": "APT-4104",
        "Account": "ACC-1004",
        "Customer": "David Kim",
        "Service": "Duct Inspection",
        "Date": "2026-04-13",
        "Time": "02:00 PM",
        "Technician": "Lamarca Salvatore",
        "Status": "Scheduled",
    },
    {
        "Appointment ID": "APT-4105",
        "Account": "ACC-1002",
        "Customer": "James Thompson",
        "Service": "Emergency No-Cool Diagnostic",
        "Date": "2026-04-14",
        "Time": "08:00 AM",
        "Technician": "Ryan Majd",
        "Status": "Scheduled",
    },
    {
        "Appointment ID": "APT-4106",
        "Account": "ACC-1001",
        "Customer": "Maria Garcia",
        "Service": "Filter Delivery and Install",
        "Date": "2026-04-14",
        "Time": "01:30 PM",
        "Technician": "Lamarca Salvatore",
        "Status": "Rescheduled",
    },
    {
        "Appointment ID": "APT-4107",
        "Account": "ACC-1005",
        "Customer": "Eleanor Price",
        "Service": "Mini-Split Maintenance",
        "Date": "2026-04-15",
        "Time": "10:00 AM",
        "Technician": "Shishir Lohar",
        "Status": "Scheduled",
    },
    {
        "Appointment ID": "APT-4108",
        "Account": "ACC-1006",
        "Customer": "Noah Bennett",
        "Service": "Coil Cleaning",
        "Date": "2026-04-15",
        "Time": "03:30 PM",
        "Technician": "Yash Verma",
        "Status": "Scheduled",
    },
    {
        "Appointment ID": "APT-4109",
        "Account": "ACC-1007",
        "Customer": "Ava Ramirez",
        "Service": "System Replacement Estimate",
        "Date": "2026-04-16",
        "Time": "09:30 AM",
        "Technician": "Lamarca Salvatore",
        "Status": "Scheduled",
    },
    {
        "Appointment ID": "APT-4110",
        "Account": "ACC-1008",
        "Customer": "Liam Foster",
        "Service": "Drain Line Flush",
        "Date": "2026-04-16",
        "Time": "12:30 PM",
        "Technician": "Ryan Majd",
        "Status": "Cancelled",
    },
    {
        "Appointment ID": "APT-4111",
        "Account": "ACC-1009",
        "Customer": "Grace Chen",
        "Service": "Heat Pump Inspection",
        "Date": "2026-04-18",
        "Time": "10:30 AM",
        "Technician": "Yash Verma",
        "Status": "Scheduled",
    },
    {
        "Appointment ID": "APT-4112",
        "Account": "ACC-1010",
        "Customer": "Mason Reed",
        "Service": "Condenser Fan Replacement",
        "Date": "2026-04-18",
        "Time": "02:30 PM",
        "Technician": "Shishir Lohar",
        "Status": "Scheduled",
    },
    {
        "Appointment ID": "APT-4113",
        "Account": "ACC-1011",
        "Customer": "Olivia Carter",
        "Service": "Spring Maintenance",
        "Date": "2026-04-26",
        "Time": "09:00 AM",
        "Technician": "Ryan Majd",
        "Status": "Scheduled",
    },
    {
        "Appointment ID": "APT-4114",
        "Account": "ACC-1012",
        "Customer": "Ethan Brooks",
        "Service": "Duct Inspection",
        "Date": "2026-04-27",
        "Time": "01:00 PM",
        "Technician": "Lamarca Salvatore",
        "Status": "Scheduled",
    },
    {
        "Appointment ID": "APT-4115",
        "Account": "ACC-1013",
        "Customer": "Sophia Nguyen",
        "Service": "AC Tune-Up",
        "Date": "2026-04-28",
        "Time": "12:00 PM",
        "Technician": "Yash Verma",
        "Status": "Scheduled",
    },
    {
        "Appointment ID": "APT-4116",
        "Account": "ACC-1014",
        "Customer": "Lucas Bennett",
        "Service": "Thermostat Repair",
        "Date": "2026-04-29",
        "Time": "10:00 AM",
        "Technician": "Shishir Lohar",
        "Status": "Scheduled",
    },
    {
        "Appointment ID": "APT-4117",
        "Account": "ACC-1015",
        "Customer": "Mia Sanchez",
        "Service": "Coil Cleaning",
        "Date": "2026-04-30",
        "Time": "02:30 PM",
        "Technician": "Ryan Majd",
        "Status": "Scheduled",
    },
    {
        "Appointment ID": "APT-4118",
        "Account": "ACC-1016",
        "Customer": "Noah Rivera",
        "Service": "System Check",
        "Date": "2026-05-01",
        "Time": "09:30 AM",
        "Technician": "Lamarca Salvatore",
        "Status": "Scheduled",
    },
    {
        "Appointment ID": "APT-4119",
        "Account": "ACC-1017",
        "Customer": "Avery Collins",
        "Service": "Filter Replacement",
        "Date": "2026-05-02",
        "Time": "10:00 AM",
        "Technician": "Yash Verma",
        "Status": "Scheduled",
    },
    {
        "Appointment ID": "APT-4120",
        "Account": "ACC-1018",
        "Customer": "Henry Foster",
        "Service": "Emergency Cooling Check",
        "Date": "2026-05-03",
        "Time": "11:30 AM",
        "Technician": "Shishir Lohar",
        "Status": "Scheduled",
    },
    {
        "Appointment ID": "APT-4121",
        "Account": "ACC-1019",
        "Customer": "Ella Parker",
        "Service": "Heat Pump Maintenance",
        "Date": "2026-05-04",
        "Time": "08:30 AM",
        "Technician": "Ryan Majd",
        "Status": "Scheduled",
    },
    {
        "Appointment ID": "APT-4122",
        "Account": "ACC-1020",
        "Customer": "Jackson Gray",
        "Service": "Airflow Diagnostic",
        "Date": "2026-05-05",
        "Time": "01:00 PM",
        "Technician": "Lamarca Salvatore",
        "Status": "Scheduled",
    },
    {
        "Appointment ID": "APT-4123",
        "Account": "ACC-1021",
        "Customer": "Amelia Ross",
        "Service": "Drain Line Service",
        "Date": "2026-05-06",
        "Time": "02:30 PM",
        "Technician": "Yash Verma",
        "Status": "Scheduled",
    },
    {
        "Appointment ID": "APT-4124",
        "Account": "ACC-1022",
        "Customer": "Benjamin Ward",
        "Service": "Vent Cleaning",
        "Date": "2026-05-07",
        "Time": "11:00 AM",
        "Technician": "Shishir Lohar",
        "Status": "Scheduled",
    },
    {
        "Appointment ID": "APT-4125",
        "Account": "ACC-1023",
        "Customer": "Harper James",
        "Service": "Annual Maintenance",
        "Date": "2026-05-08",
        "Time": "12:00 PM",
        "Technician": "Ryan Majd",
        "Status": "Scheduled",
    },
    {
        "Appointment ID": "APT-4126",
        "Account": "ACC-1024",
        "Customer": "Leo Murphy",
        "Service": "Compressor Inspection",
        "Date": "2026-05-09",
        "Time": "10:00 AM",
        "Technician": "Lamarca Salvatore",
        "Status": "Scheduled",
    },
    {
        "Appointment ID": "APT-4127",
        "Account": "ACC-1025",
        "Customer": "Nora Bell",
        "Service": "Routine AC Service",
        "Date": "2026-05-10",
        "Time": "11:30 AM",
        "Technician": "Lamarca Salvatore",
        "Status": "Scheduled",
    },
    {
        "Appointment ID": "APT-4128",
        "Account": "ACC-1026",
        "Customer": "Caleb Stone",
        "Service": "Thermostat Calibration",
        "Date": "2026-05-11",
        "Time": "12:00 PM",
        "Technician": "Ryan Majd",
        "Status": "Scheduled",
    },
    {
        "Appointment ID": "APT-4129",
        "Account": "ACC-1027",
        "Customer": "Lila Brooks",
        "Service": "Vent Inspection",
        "Date": "2026-05-12",
        "Time": "01:00 PM",
        "Technician": "Yash Verma",
        "Status": "Scheduled",
    },
    {
        "Appointment ID": "APT-4130",
        "Account": "ACC-1028",
        "Customer": "Owen Price",
        "Service": "Cooling Check",
        "Date": "2026-05-13",
        "Time": "12:30 PM",
        "Technician": "Shishir Lohar",
        "Status": "Scheduled",
    },
    {
        "Appointment ID": "APT-4131",
        "Account": "ACC-1029",
        "Customer": "Maya Ellis",
        "Service": "Filter Replacement",
        "Date": "2026-05-14",
        "Time": "11:00 AM",
        "Technician": "Lamarca Salvatore",
        "Status": "Scheduled",
    },
    {
        "Appointment ID": "APT-4132",
        "Account": "ACC-1030",
        "Customer": "Jade Foster",
        "Service": "Spring Checkup",
        "Date": "2026-05-15",
        "Time": "12:30 PM",
        "Technician": "Ryan Majd",
        "Status": "Scheduled",
    },
    {
        "Appointment ID": "APT-4133",
        "Account": "ACC-1031",
        "Customer": "Eli Turner",
        "Service": "Vent Balance Check",
        "Date": "2026-05-16",
        "Time": "01:00 PM",
        "Technician": "Yash Verma",
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


def update_appointment_customer_row(appointment_id: str, customer_name: str) -> dict:
    """Find the appointment by ID and update the customer name."""
    try:
        rows = _read_all()
        found = False
        for row in rows:
            if row["Appointment ID"] == appointment_id:
                row["Customer"] = customer_name
                found = True
                break
        if not found:
            return {"error": f"Appointment {appointment_id} not found in CSV."}
        _write_all(rows)
        return {"success": True, "file": str(_csv_path())}
    except Exception as e:
        return {"error": str(e)}
