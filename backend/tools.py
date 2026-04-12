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
        {"id": appt_id, **appt}
        for appt_id, appt in APPOINTMENTS.items()
        if appt["account"] == account_number.upper()
    ]
    if not appts:
        return {"found": False, "message": "No upcoming appointments found for this account."}
    return {"found": True, "appointments": appts}


def reschedule_appointment(appointment_id: str, new_date: str, new_time: str) -> dict:
    """Reschedule an existing appointment to a new date and time."""
    existing = APPOINTMENTS.get(appointment_id.upper())
    if not existing:
        return {"success": False, "reason": "Appointment ID not found."}
    old_date, old_time = existing["date"], existing["time"]
    APPOINTMENTS[appointment_id.upper()]["date"] = new_date
    APPOINTMENTS[appointment_id.upper()]["time"] = new_time
    # Sync to Google Sheets
    csv_service.reschedule_appointment_row(appointment_id.upper(), new_date, new_time)
    return {
        "success": True,
        "appointment_id": appointment_id.upper(),
        "service": existing["service"],
        "old_date": old_date,
        "old_time": old_time,
        "new_date": new_date,
        "new_time": new_time,
        "technician": existing["tech"],
    }


def get_order_status(order_id: str) -> dict:
    """Check the status of a service or parts order."""
    order = ORDERS.get(order_id.upper())
    if not order:
        return {"found": False, "reason": "Order ID not found."}
    return {"found": True, **order}


def get_available_slots(start_date: str, end_date: str, service_type: str = "") -> dict:
    """Return available appointment slots in a date range."""
    return {
        "available_slots": AVAILABLE_SLOTS,
        "note": "Technician will call 30 minutes before arrival to confirm.",
    }


def book_appointment(account_number: str, date: str, time: str, service_type: str) -> dict:
    """Book a new service appointment for a customer."""
    acc = ACCOUNTS.get(account_number.upper())
    if not acc:
        return {"success": False, "reason": "Account number not found."}
    appointment_id = "APT-" + "".join(random.choices(string.digits, k=4))
    techs = ["Carlos", "Maria", "Jake", "Sophie"]
    assigned_tech = random.choice(techs)
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
        "sheet_sync": sheet_result,
        "note": "You will receive a confirmation and your technician will call 30 minutes before arrival.",
    }


def cancel_appointment(appointment_id: str) -> dict:
    """Cancel an existing service appointment."""
    existing = APPOINTMENTS.get(appointment_id.upper())
    if not existing:
        return {"success": False, "reason": "Appointment ID not found."}
    cancelled = APPOINTMENTS.pop(appointment_id.upper())
    # Sync to Google Sheets
    csv_service.cancel_appointment_row(appointment_id.upper())
    return {
        "success": True,
        "appointment_id": appointment_id.upper(),
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
