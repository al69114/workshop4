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
from datetime import date, datetime, timedelta
from services import csv_service

# ── Mock data ──────────────────────────────────────────────────────────────────

ACCOUNTS = {
    "ACC-1001": {"last_name": "Garcia",   "full_name": "Maria Garcia",   "address": "12 Elm Street",   "phone": "555-0191"},
    "ACC-1002": {"last_name": "Thompson", "full_name": "James Thompson",  "address": "34 Oak Avenue",   "phone": "555-0192"},
    "ACC-1003": {"last_name": "Patel",    "full_name": "Priya Patel",     "address": "56 Maple Drive",  "phone": "555-0193"},
    "ACC-1004": {"last_name": "Kim",      "full_name": "David Kim",       "address": "78 Pine Road",    "phone": "555-0194"},
}

APPOINTMENTS = {
    "APT-4001": {"account": "ACC-1001", "date": "2026-04-18", "time": "9:00 AM",  "service": "AC Tune-Up",            "tech": "Ryan Majd"},
    "APT-4002": {"account": "ACC-1001", "date": "2026-04-25", "time": "2:00 PM",  "service": "Filter Replacement",    "tech": "Lamarca Salvatore"},
    "APT-4003": {"account": "ACC-1002", "date": "2026-04-19", "time": "11:00 AM", "service": "Heating System Repair", "tech": "Yash Verma"},
    "APT-4004": {"account": "ACC-1003", "date": "2026-04-22", "time": "10:00 AM", "service": "New Unit Installation", "tech": "Shishir Lohar"},
}

ORDERS = {
    "ORD-8001": {"account": "ACC-1001", "status": "In Progress",  "service": "AC Compressor Replacement", "tech": "Ryan Majd",     "eta": "2026-04-14"},
    "ORD-8002": {"account": "ACC-1002", "status": "Parts Ordered","service": "Heat Exchanger Repair",     "tech": "Yash Verma",    "eta": "2026-04-17"},
    "ORD-8003": {"account": "ACC-1003", "status": "Completed",    "service": "Duct Sealing",              "tech": "Shishir Lohar", "completed": "2026-04-10"},
    "ORD-8004": {"account": "ACC-1004", "status": "Scheduled",    "service": "Annual Maintenance",        "tech": "Lamarca Salvatore",   "eta": "2026-04-15"},
}

AVAILABLE_SLOTS = [
    {"date": "2026-04-14", "times": ["9:00 AM", "11:00 AM", "2:00 PM"]},
    {"date": "2026-04-15", "times": ["10:00 AM", "3:00 PM"]},
    {"date": "2026-04-16", "times": ["8:00 AM", "1:00 PM", "4:00 PM"]},
    {"date": "2026-04-17", "times": ["9:00 AM", "11:00 AM"]},
    {"date": "2026-04-21", "times": ["10:00 AM", "2:00 PM", "4:00 PM"]},
    {"date": "2026-04-22", "times": ["9:00 AM", "1:00 PM"]},
    {"date": "2026-04-26", "times": ["9:00 AM", "11:00 AM", "2:00 PM"]},
    {"date": "2026-04-27", "times": ["8:30 AM", "1:00 PM", "3:30 PM"]},
    {"date": "2026-04-28", "times": ["9:00 AM", "12:00 PM", "4:00 PM"]},
    {"date": "2026-04-29", "times": ["10:00 AM", "1:30 PM", "3:00 PM"]},
    {"date": "2026-04-30", "times": ["8:00 AM", "11:00 AM", "2:30 PM"]},
    {"date": "2026-05-01", "times": ["9:30 AM", "12:30 PM", "3:30 PM"]},
    {"date": "2026-05-02", "times": ["10:00 AM", "1:00 PM"]},
    {"date": "2026-05-03", "times": ["9:00 AM", "11:30 AM", "2:00 PM"]},
    {"date": "2026-05-04", "times": ["8:30 AM", "12:00 PM", "4:00 PM"]},
    {"date": "2026-05-05", "times": ["9:00 AM", "1:00 PM", "3:00 PM"]},
    {"date": "2026-05-06", "times": ["10:00 AM", "12:30 PM", "2:30 PM"]},
    {"date": "2026-05-07", "times": ["8:00 AM", "11:00 AM", "1:30 PM"]},
    {"date": "2026-05-08", "times": ["9:30 AM", "12:00 PM", "3:00 PM"]},
    {"date": "2026-05-09", "times": ["10:00 AM", "1:00 PM"]},
    {"date": "2026-05-10", "times": ["9:00 AM", "11:30 AM", "2:30 PM"]},
    {"date": "2026-05-11", "times": ["8:30 AM", "12:00 PM", "3:30 PM"]},
    {"date": "2026-05-12", "times": ["9:00 AM", "1:00 PM", "4:00 PM"]},
    {"date": "2026-05-13", "times": ["10:00 AM", "12:30 PM", "3:00 PM"]},
    {"date": "2026-05-14", "times": ["8:00 AM", "11:00 AM", "2:00 PM"]},
    {"date": "2026-05-15", "times": ["9:30 AM", "12:30 PM", "3:30 PM"]},
    {"date": "2026-05-16", "times": ["10:00 AM", "1:00 PM", "4:00 PM"]},
]

TECHNICIANS = ["Ryan Majd", "Lamarca Salvatore", "Yash Verma", "Shishir Lohar"]
TECHNICIAN_FEEDBACK = {
    "ryan majd": {
        "technician": "Ryan Majd",
        "rating": 9.0,
        "summary": "Brilliant critical thinker with a reputation for solving tough HVAC problems quickly and is about to retire.",
    },
    "lamarca salvatore": {
        "technician": "Lamarca Salvatore",
        "rating": 3.0,
        "summary": "High-energy technician who usually averages on the job and doesn't know systems and bullies customers ",
    },
    "yash verma": {
        "technician": "Yash Verma",
        "rating": 7.0,
        "summary": "Drank a gallon of milk puked all over the AC and is new to the job and hacked the hvac to hack into kronos",
    },
    "shishir lohar": {
        "technician": "Shishir Lohar",
        "rating": 2.5,
        "summary": "He is below average in installing units but a hundred percent genius when it comes to exploding units.",
    },
}


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


def _spoken_slot_line(slot: dict) -> str:
    """Create one clean spoken availability line."""
    spoken_date = _format_spoken_date(slot["date"])
    return f"{spoken_date} at {slot['time']}"


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


def _date_window(start_date: str = "", end_date: str = "") -> tuple[str, str]:
    """Resolve a date window for availability lookups."""
    normalized_start = start_date or AVAILABLE_SLOTS[0]["date"]
    normalized_end = end_date or AVAILABLE_SLOTS[-1]["date"]
    return normalized_start, normalized_end


def _emergency_date_window(
    start_date: str = "",
    end_date: str = "",
) -> tuple[str, str]:
    """Limit emergency scheduling to today through the next two days."""
    today = date.today()
    earliest = max(today, datetime.strptime(AVAILABLE_SLOTS[0]["date"], "%Y-%m-%d").date())
    latest = min(
        today + timedelta(days=2),
        datetime.strptime(AVAILABLE_SLOTS[-1]["date"], "%Y-%m-%d").date(),
    )

    start = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else earliest
    end = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else latest

    normalized_start = max(start, earliest)
    normalized_end = min(end, latest)
    if normalized_start > normalized_end:
        normalized_start = earliest
        normalized_end = latest

    return normalized_start.isoformat(), normalized_end.isoformat()


def _find_csv_appointment(appointment_id: str) -> dict | None:
    normalized_id = _normalize_appointment_id(appointment_id)
    for row in csv_service.list_appointments():
        if row.get("Appointment ID") == normalized_id:
            return row
    return None


def _normalize_appointment_id(appointment_id: str) -> str:
    """Accept bare numeric appointment numbers like 3487 as APT-3487."""
    cleaned = "".join(ch for ch in appointment_id.upper() if ch.isalnum() or ch == "-")
    digits = "".join(ch for ch in cleaned if ch.isdigit())
    if cleaned.startswith("APT-"):
        return cleaned
    if cleaned.startswith("APT") and digits:
        return f"APT-{digits}"
    if digits:
        return f"APT-{digits}"
    return cleaned


def _first_name(value: str) -> str:
    """Return the normalized first name from a full name string."""
    cleaned = " ".join(value.strip().split()).lower()
    return cleaned.split()[0] if cleaned else ""


def _resolve_technician_name(technician_name: str) -> str | None:
    """Resolve a technician from a full name, first name, or unique partial match."""
    cleaned = " ".join(technician_name.strip().split()).lower()
    if not cleaned:
        return None

    exact_match = next(
        (technician for technician in TECHNICIANS if technician.lower() == cleaned),
        None,
    )
    if exact_match:
        return exact_match

    first_name_matches = [
        technician
        for technician in TECHNICIANS
        if technician.split()[0].lower() == cleaned
    ]
    if len(first_name_matches) == 1:
        return first_name_matches[0]

    partial_matches = [
        technician
        for technician in TECHNICIANS
        if cleaned in technician.lower()
    ]
    if len(partial_matches) == 1:
        return partial_matches[0]

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


def _update_account_name(account_number: str, customer_name: str) -> None:
    """Update the stored account name when a caller corrects it."""
    cleaned_name = " ".join(customer_name.strip().split())
    if not cleaned_name:
        return
    account = ACCOUNTS.get(account_number.upper())
    if not account:
        return
    account["full_name"] = cleaned_name
    account["last_name"] = cleaned_name.split()[-1]

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


def reschedule_appointment(
    first_name: str,
    appointment_id: str,
    new_date: str,
    new_time: str,
) -> dict:
    """Reschedule an existing appointment to a new date and time."""
    cleaned_first_name = _first_name(first_name)
    if not cleaned_first_name:
        return {"success": False, "reason": "First name is required."}

    appointment_key = _normalize_appointment_id(appointment_id)
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

    recorded_name = ""
    if csv_row and csv_row.get("Customer"):
        recorded_name = " ".join(csv_row["Customer"].strip().split())
    elif existing.get("account") and existing["account"] in ACCOUNTS:
        recorded_name = ACCOUNTS[existing["account"]]["full_name"]

    if recorded_name and _first_name(recorded_name) != cleaned_first_name:
        return {
            "success": False,
            "reason": "The first name does not match the appointment on file.",
        }

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
        "appointment_id": appointment_key,
        "customer": recorded_name or cleaned_first_name.title(),
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


def get_technician_feedback(technician_name: str) -> dict:
    """Return a playful technician rating summary."""
    resolved_name = _resolve_technician_name(technician_name)
    if not resolved_name:
        return {
            "found": False,
            "message": "I do not have technician feedback for that name.",
        }
    feedback = TECHNICIAN_FEEDBACK.get(resolved_name.lower())
    return {
        "found": True,
        "rating_scale": 10,
        "rating_text": f"{feedback['rating']} out of 10",
        **feedback,
    }


def get_available_slots(
    start_date: str = "",
    end_date: str = "",
    service_type: str = "",
    urgency: str = "standard",
) -> dict:
    """Return available appointment slots in a date range."""
    normalized_urgency = urgency.strip().lower() or "standard"
    if normalized_urgency == "emergency":
        normalized_start, normalized_end = _emergency_date_window(start_date, end_date)
    else:
        normalized_start, normalized_end = _date_window(start_date, end_date)
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
            "message": (
                "No emergency openings are available today through the next two days."
                if normalized_urgency == "emergency"
                else "No appointment openings are available in that date range."
            ),
            "repeat_prompt": (
                "If you want, I can check the next available non-emergency openings for you."
                if normalized_urgency == "emergency"
                else "If you want, I can check a different date range for you."
            ),
            "urgency": normalized_urgency,
        }

    spoken_lines = [_spoken_slot_line(slot) for slot in slot_options[:3]]
    return {
        "available_slots": slot_options,
        "unavailable_slots": unavailable_slots,
        "service_type": service_type,
        "message": (
            "Here are the emergency openings available today through the next two days."
            if normalized_urgency == "emergency"
            else "Here are the next available appointment openings."
        ),
        "spoken_summary": ". ".join(spoken_lines) + ".",
        "repeat_prompt": "If you would like, I can repeat those openings more slowly.",
        "note": "Technician will call 30 minutes before arrival to confirm.",
        "urgency": normalized_urgency,
    }


def get_slot_technicians(date: str, time: str) -> dict:
    """Return which technicians are available for one exact slot."""
    if not _slot_is_offered(date, time):
        return {
            "found": False,
            "reason": "That date and time is not on the current availability list.",
        }

    available_techs = _available_technicians(date, time)
    if not available_techs:
        return {
            "found": False,
            "reason": "No technicians are available for that date and time.",
        }

    return {
        "found": True,
        "date": date,
        "time": time,
        "available_technicians": available_techs,
        "spoken_summary": f"For {date} at {time}, I currently have {', '.join(available_techs)} available.",
    }


def get_technician_slots(
    technician_name: str,
    start_date: str = "",
    end_date: str = "",
) -> dict:
    """Return openings where a requested technician is available."""
    resolved_name = _resolve_technician_name(technician_name)
    if not resolved_name:
        return {
            "found": False,
            "reason": "That technician name was not found.",
        }

    normalized_start, normalized_end = _date_window(start_date, end_date)
    matches = []
    for slot in AVAILABLE_SLOTS:
        date = slot["date"]
        if not _date_in_range(date, normalized_start, normalized_end):
            continue
        for time in slot["times"]:
            if resolved_name in _available_technicians(date, time):
                matches.append(
                    {
                        "date": date,
                        "time": time,
                        "technician": resolved_name,
                    }
                )

    if not matches:
        return {
            "found": False,
            "technician": resolved_name,
            "reason": "That technician has no open slots in the current date range.",
        }

    spoken_lines = [_spoken_slot_line(slot) for slot in matches[:3]]
    return {
        "found": True,
        "technician": resolved_name,
        "available_slots": matches,
        "spoken_summary": ". ".join(spoken_lines) + ".",
    }


def book_appointment(
    customer_name: str,
    date: str,
    time: str,
    service_type: str,
    technician_name: str = "",
) -> dict:
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
    requested_technician = " ".join(technician_name.strip().split())
    if requested_technician:
        resolved_technician = _resolve_technician_name(requested_technician)
        if not resolved_technician:
            return {
                "success": False,
                "reason": "That technician name was not found.",
            }
        if resolved_technician not in available_techs:
            technician_alternatives = get_technician_slots(
                resolved_technician,
                start_date=date,
                end_date=AVAILABLE_SLOTS[-1]["date"],
            )
            return {
                "success": False,
                "reason": "That technician is not available at the selected date and time.",
                "available_technicians": available_techs,
                "technician_alternatives": technician_alternatives.get("available_slots", []),
                "repeat_prompt": "I can keep the same time with a different technician or look for another time with your preferred technician.",
            }
        requested_technician = resolved_technician
    account_number, acc, created_new_account = _register_customer(cleaned_name)
    appointment_id = "APT-" + "".join(random.choices(string.digits, k=4))
    assigned_tech = requested_technician or available_techs[0]
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


def update_appointment_customer_name(appointment_id: str, customer_name: str) -> dict:
    """Update the customer name on an existing appointment."""
    cleaned_name = " ".join(customer_name.strip().split())
    if not cleaned_name:
        return {"success": False, "reason": "Customer name is required."}

    appointment_key = _normalize_appointment_id(appointment_id)
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

    account_number = existing.get("account", "")
    if account_number:
        _update_account_name(account_number, cleaned_name)

    sheet_result = csv_service.update_appointment_customer_row(
        appointment_key,
        cleaned_name,
    )
    if sheet_result.get("error"):
        return {"success": False, "reason": sheet_result["error"]}

    return {
        "success": True,
        "appointment_id": appointment_key,
        "customer": cleaned_name,
        "date": existing["date"],
        "time": existing["time"],
        "service": existing["service"],
        "technician": existing["tech"],
        "message": "I updated the appointment to the corrected customer name.",
    }


def cancel_appointment(first_name: str, appointment_id: str) -> dict:
    """Cancel an existing service appointment."""
    cleaned_first_name = _first_name(first_name)
    if not cleaned_first_name:
        return {"success": False, "reason": "First name is required."}
    appointment_key = _normalize_appointment_id(appointment_id)
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

    if recorded_name and _first_name(recorded_name) != cleaned_first_name:
        return {
            "success": False,
            "reason": "The first name does not match the appointment on file.",
        }

    cancelled = APPOINTMENTS.pop(appointment_key, existing)
    csv_service.cancel_appointment_row(appointment_key)
    return {
        "success": True,
        "appointment_id": appointment_key,
        "customer": recorded_name or cleaned_first_name.title(),
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
    "get_technician_feedback": get_technician_feedback,
    "get_available_slots":    get_available_slots,
    "get_slot_technicians":   get_slot_technicians,
    "get_technician_slots":   get_technician_slots,
    "book_appointment":       book_appointment,
    "update_appointment_customer_name": update_appointment_customer_name,
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
