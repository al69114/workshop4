"""
Mock HVAC business logic for the voice agent workshop.

In a real deployment, replace these functions with calls to your actual backend:
  - verify_account      → your CRM / customer database
  - get_appointments    → your scheduling system (e.g. Google Calendar, ServiceTitan)
  - reschedule_appointment → your scheduling system
  - get_order_status    → your field service / ERP system
  - get_available_slots → your scheduling system

Each function returns a plain dict — the agent reads it and speaks the result.
"""

import json
import random
import string
from datetime import datetime
from services import csv_service

# ── Mock data ──────────────────────────────────────────────────────────────────

ACCOUNTS = {
    "ACC-1001": {"last_name": "Garcia",   "full_name": "Maria Garcia",   "address": "12 Elm Street",   "phone": "555-0191"},
    "ACC-1002": {"last_name": "Thompson", "full_name": "James Thompson",  "address": "34 Oak Avenue",   "phone": "555-0192"},
    "ACC-1003": {"last_name": "Patel",    "full_name": "Priya Patel",     "address": "56 Maple Drive",  "phone": "555-0193"},
    "ACC-1004": {"last_name": "Kim",      "full_name": "David Kim",       "address": "78 Pine Road",    "phone": "555-0194"},
}

APPOINTMENTS = {
    "APT-4001": {"account": "ACC-1001", "date": "2026-04-18", "time": "9:00 AM",  "service": "AC Tune-Up",            "tech": "Carlos"},
    "APT-4002": {"account": "ACC-1001", "date": "2026-04-25", "time": "2:00 PM",  "service": "Filter Replacement",    "tech": "Maria"},
    "APT-4003": {"account": "ACC-1002", "date": "2026-04-19", "time": "11:00 AM", "service": "Heating System Repair", "tech": "Jake"},
    "APT-4004": {"account": "ACC-1003", "date": "2026-04-22", "time": "10:00 AM", "service": "New Unit Installation", "tech": "Sophie"},
}

ORDERS = {
    "ORD-8001": {"account": "ACC-1001", "status": "In Progress",  "service": "AC Compressor Replacement", "tech": "Carlos",  "eta": "2026-04-14"},
    "ORD-8002": {"account": "ACC-1002", "status": "Parts Ordered","service": "Heat Exchanger Repair",     "tech": "Jake",    "eta": "2026-04-17"},
    "ORD-8003": {"account": "ACC-1003", "status": "Completed",    "service": "Duct Sealing",               "tech": "Sophie",  "completed": "2026-04-10"},
    "ORD-8004": {"account": "ACC-1004", "status": "Scheduled",    "service": "Annual Maintenance",         "tech": "Maria",   "eta": "2026-04-15"},
}

AVAILABLE_SLOTS = [
    {"date": "2026-04-14", "times": ["9:00 AM", "11:00 AM", "2:00 PM"]},
    {"date": "2026-04-15", "times": ["10:00 AM", "3:00 PM"]},
    {"date": "2026-04-16", "times": ["8:00 AM", "1:00 PM", "4:00 PM"]},
    {"date": "2026-04-17", "times": ["9:00 AM", "11:00 AM"]},
    {"date": "2026-04-21", "times": ["10:00 AM", "2:00 PM", "4:00 PM"]},
    {"date": "2026-04-22", "times": ["9:00 AM", "1:00 PM"]},
]

TECHNICIANS = ["Carlos", "Maria", "Jake", "Sophie"]


def _format_spoken_date(value: str) -> str:
    """Convert YYYY-MM-DD into a short spoken date."""
    parsed = datetime.strptime(value, "%Y-%m-%d")
    return parsed.strftime("%A, %B").replace(" 0", " ") + _ordinal_suffix(parsed.day)


def _ordinal_suffix(day: int) -> str:
    """Return ordinal suffix for spoken dates."""
    if 10 <= day % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return f" {day}{suffix}"


def _join_names(names: list[str]) -> str:
    """Join technician names in a natural spoken way."""
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} or {names[1]}"
    return f"{', '.join(names[:-1])}, or {names[-1]}"


def _spoken_slot_line(slot: dict) -> str:
    """Create one clean spoken availability line."""
    spoken_date = _format_spoken_date(slot["date"])
    technicians = _join_names(slot["available_technicians"])
    return f"{spoken_date} at {slot['time']} with {technicians}"


def _date_in_range(value: str, start_date: str, end_date: str) -> bool:
    return start_date <= value <= end_date


def _scheduled_rows() -> list[dict]:
    return [
        row
        for row in csv_service.list_appointments()
        if row.get("Status") != "Cancelled"
    ]


def _slot_is_offered(date: str, time: str) -> bool:
    return any(
        slot["date"] == date and time in slot["times"]
        for slot in AVAILABLE_SLOTS
    )


def _available_technicians(date: str, time: str) -> list[str]:
    occupied = {
        row["Technician"]
        for row in _scheduled_rows()
        if row.get("Date") == date and row.get("Time") == time
    }
    return [tech for tech in TECHNICIANS if tech not in occupied]


def _find_csv_appointment(appointment_id: str) -> dict | None:
    normalized_id = appointment_id.upper()
    for row in csv_service.list_appointments():
        if row.get("Appointment ID") == normalized_id:
            return row
    return None


def _find_account_by_name(customer_name: str) -> tuple[str, dict] | None:
    normalized_name = customer_name.strip().lower()
    for account_number, account in ACCOUNTS.items():
        if account["full_name"].strip().lower() == normalized_name:
            return account_number, account
    return None


def _next_account_number() -> str:
    numeric_values = [
        int(account_number.split("-", 1)[1])
        for account_number in ACCOUNTS
        if account_number.startswith("ACC-") and account_number.split("-", 1)[1].isdigit()
    ]
    next_number = max(numeric_values, default=1000) + 1
    return f"ACC-{next_number}"


def _register_customer(customer_name: str) -> tuple[str, dict, bool]:
    existing = _find_account_by_name(customer_name)
    if existing:
        account_number, account = existing
        return account_number, account, False

    cleaned_name = " ".join(customer_name.strip().split())
    last_name = cleaned_name.split()[-1] if cleaned_name else "Customer"
    account_number = _next_account_number()
    account = {
        "last_name": last_name,
        "full_name": cleaned_name,
        "address": "Address not yet collected",
        "phone": "Phone not yet collected",
    }
    ACCOUNTS[account_number] = account
    return account_number, account, True

# ── Tool functions ─────────────────────────────────────────────────────────────

def verify_account(account_number: str, last_name: str) -> dict:
    """Verify a customer's identity before accessing their account."""
    acc = ACCOUNTS.get(account_number.upper())
    if not acc:
        return {"verified": False, "reason": "Account number not found."}
    if acc["last_name"].lower() != last_name.strip().lower():
        return {"verified": False, "reason": "Last name does not match our records."}
    return {
        "verified": True,
        "account_number": account_number.upper(),
        "full_name": acc["full_name"],
        "address": acc["address"],
    }


def get_appointments(account_number: str) -> dict:
    """Get upcoming service appointments for a customer account."""
    appts = [
        {
            "id": row["Appointment ID"],
            "account": row["Account"],
            "date": row["Date"],
            "time": row["Time"],
            "service": row["Service"],
            "tech": row["Technician"],
            "status": row["Status"],
        }
        for row in csv_service.list_appointments()
        if row["Account"] == account_number.upper() and row["Status"] != "Cancelled"
    ]
    if not appts:
        return {"found": False, "message": "No upcoming appointments found for this account."}
    return {"found": True, "appointments": appts}


def reschedule_appointment(appointment_id: str, new_date: str, new_time: str) -> dict:
    """Reschedule an existing appointment to a new date and time."""
    appointment_key = appointment_id.upper()
    existing = APPOINTMENTS.get(appointment_key)
    csv_row = _find_csv_appointment(appointment_key)
    if not existing and csv_row:
        existing = {
            "account": csv_row["Account"],
            "date": csv_row["Date"],
            "time": csv_row["Time"],
            "service": csv_row["Service"],
            "tech": csv_row["Technician"],
        }
        APPOINTMENTS[appointment_key] = existing
    if not existing:
        return {"success": False, "reason": "Appointment ID not found."}
    if not _slot_is_offered(new_date, new_time):
        return {
            "success": False,
            "reason": "That opening is not on the current availability list.",
            "repeat_prompt": "Please choose one of the listed openings, and I can repeat them if needed.",
        }
    available_techs = _available_technicians(new_date, new_time)
    if not available_techs:
        return {
            "success": False,
            "reason": "That time is no longer available.",
            "repeat_prompt": "Please choose another opening and I can repeat the available slots if needed.",
        }
    old_date, old_time = existing["date"], existing["time"]
    APPOINTMENTS[appointment_key]["date"] = new_date
    APPOINTMENTS[appointment_key]["time"] = new_time
    APPOINTMENTS[appointment_key]["tech"] = available_techs[0]
    # Sync to Google Sheets
    csv_service.reschedule_appointment_row(
        appointment_id.upper(),
        new_date,
        new_time,
        available_techs[0],
    )
    return {
        "success": True,
        "appointment_id": appointment_id.upper(),
        "service": existing["service"],
        "old_date": old_date,
        "old_time": old_time,
        "new_date": new_date,
        "new_time": new_time,
        "technician": available_techs[0],
    }


def get_order_status(order_id: str) -> dict:
    """Check the status of a service or parts order."""
    order = ORDERS.get(order_id.upper())
    if not order:
        return {"found": False, "reason": "Order ID not found."}
    return {"found": True, **order}


def get_available_slots(
    start_date: str = "",
    end_date: str = "",
    service_type: str = "",
) -> dict:
    """Return available appointment slots in a date range."""
    normalized_start = start_date or AVAILABLE_SLOTS[0]["date"]
    normalized_end = end_date or AVAILABLE_SLOTS[-1]["date"]
    slot_options = []
    unavailable_slots = []

    for slot in AVAILABLE_SLOTS:
        date = slot["date"]
        if not _date_in_range(date, normalized_start, normalized_end):
            continue

        for time in slot["times"]:
            available_techs = _available_technicians(date, time)
            option = {
                "date": date,
                "time": time,
                "available_technicians": available_techs,
                "remaining_capacity": len(available_techs),
            }
            if available_techs:
                slot_options.append(option)
            else:
                unavailable_slots.append(option)

    if not slot_options:
        return {
            "available_slots": [],
            "unavailable_slots": unavailable_slots,
            "message": "No appointment openings are available in that date range.",
            "repeat_prompt": "If you want, I can check a different date range for you.",
        }

    spoken_lines = [_spoken_slot_line(slot) for slot in slot_options[:3]]
    return {
        "available_slots": slot_options,
        "unavailable_slots": unavailable_slots,
        "service_type": service_type,
        "message": "Here are the next available appointment openings.",
        "spoken_summary": ". ".join(spoken_lines) + ".",
        "repeat_prompt": "If you would like, I can repeat those openings more slowly.",
        "note": "Technician will call 30 minutes before arrival to confirm.",
    }


def book_appointment(customer_name: str, date: str, time: str, service_type: str) -> dict:
    """Book a new service appointment for a customer."""
    cleaned_name = " ".join(customer_name.strip().split())
    if not cleaned_name:
        return {"success": False, "reason": "Customer name is required."}
    if not _slot_is_offered(date, time):
        return {
            "success": False,
            "reason": "That opening is not on the current availability list.",
            "repeat_prompt": "Please choose one of the listed openings, and I can repeat them if needed.",
        }
    available_techs = _available_technicians(date, time)
    if not available_techs:
        return {
            "success": False,
            "reason": "That time is no longer available.",
            "repeat_prompt": "Please choose another opening and I can repeat the available slots if needed.",
        }
    account_number, acc, created_new_account = _register_customer(cleaned_name)
    appointment_id = "APT-" + "".join(random.choices(string.digits, k=4))
    assigned_tech = available_techs[0]
    APPOINTMENTS[appointment_id] = {
        "account": account_number.upper(),
        "date": date,
        "time": time,
        "service": service_type,
        "tech": assigned_tech,
    }
    # Sync to Google Sheets
    sheet_result = csv_service.add_appointment(
        appointment_id=appointment_id,
        account=account_number.upper(),
        customer=acc["full_name"],
        service=service_type,
        date=date,
        time=time,
        tech=assigned_tech,
    )
    return {
        "success": True,
        "appointment_id": appointment_id,
        "account": account_number.upper(),
        "customer": acc["full_name"],
        "date": date,
        "time": time,
        "service": service_type,
        "technician": assigned_tech,
        "remaining_available_technicians": available_techs[1:],
        "customer_registered": created_new_account,
        "sheet_sync": sheet_result,
        "note": "You will receive a confirmation and your technician will call 30 minutes before arrival.",
    }


def cancel_appointment(customer_name: str, appointment_id: str) -> dict:
    """Cancel an existing service appointment."""
    cleaned_name = " ".join(customer_name.strip().split())
    if not cleaned_name:
        return {"success": False, "reason": "Customer name is required."}
    appointment_key = appointment_id.upper()
    existing = APPOINTMENTS.get(appointment_key)
    csv_row = _find_csv_appointment(appointment_key)
    if not existing and csv_row:
        existing = {
            "account": csv_row["Account"],
            "date": csv_row["Date"],
            "time": csv_row["Time"],
            "service": csv_row["Service"],
            "tech": csv_row["Technician"],
        }
    if not existing:
        return {"success": False, "reason": "Appointment ID not found."}

    recorded_name = ""
    if csv_row and csv_row.get("Customer"):
        recorded_name = " ".join(csv_row["Customer"].strip().split())
    elif existing.get("account") and existing["account"] in ACCOUNTS:
        recorded_name = ACCOUNTS[existing["account"]]["full_name"]

    if recorded_name and recorded_name.lower() != cleaned_name.lower():
        return {
            "success": False,
            "reason": "The name does not match the appointment on file.",
        }

    cancelled = APPOINTMENTS.pop(appointment_key, existing)
    csv_service.cancel_appointment_row(appointment_key)
    return {
        "success": True,
        "appointment_id": appointment_key,
        "customer": recorded_name or cleaned_name,
        "service": cancelled["service"],
        "date": cancelled["date"],
        "time": cancelled["time"],
        "message": "Appointment successfully cancelled. You will receive a cancellation confirmation.",
    }


def estimate_arrival_time(service_type: str, urgency: str = "standard") -> dict:
    """Estimate how long until a technician can arrive, based on urgency."""
    schedules = {
        "emergency": {"eta_minutes": random.randint(30, 90),  "note": "Emergency dispatch — a technician is being routed to you now."},
        "urgent":    {"eta_minutes": random.randint(2, 4) * 60, "note": "Same-day service — we will call to confirm the window shortly."},
        "standard":  {"eta_minutes": random.randint(1, 3) * 24 * 60, "note": "Standard scheduling — see available slots to book a time."},
    }
    level = urgency.lower() if urgency.lower() in schedules else "standard"
    eta = schedules[level]
    minutes = eta["eta_minutes"]
    if minutes < 60:
        eta_readable = f"{minutes} minutes"
    elif minutes < 24 * 60:
        eta_readable = f"{minutes // 60} hour{'s' if minutes // 60 != 1 else ''}"
    else:
        eta_readable = f"{minutes // (24 * 60)} day{'s' if minutes // (24 * 60) != 1 else ''}"
    return {
        "urgency": level,
        "service_type": service_type,
        "estimated_arrival": eta_readable,
        "note": eta["note"],
    }


# ── Dispatcher ─────────────────────────────────────────────────────────────────

_REGISTRY = {
    "verify_account":         verify_account,
    "get_appointments":       get_appointments,
    "reschedule_appointment": reschedule_appointment,
    "get_order_status":       get_order_status,
    "get_available_slots":    get_available_slots,
    "book_appointment":       book_appointment,
    "cancel_appointment":     cancel_appointment,
    "estimate_arrival_time":  estimate_arrival_time,
}


def dispatch(name: str, args: dict) -> dict:
    """Call the named tool function and return the result as a dict."""
    func = _REGISTRY.get(name)
    if not func:
        return {"error": f"Unknown tool: {name}"}
    try:
        return func(**args)
    except Exception as e:
        return {"error": str(e)}
