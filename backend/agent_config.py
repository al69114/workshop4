"""
Shared Gemini Live configuration for the HVAC agents.
"""

from google.genai import types

MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"
INPUT_AUDIO_SAMPLE_RATE = 16_000
OUTPUT_AUDIO_SAMPLE_RATE = 24_000
OPENING_PROMPT = "[Call connected. Deliver the opening greeting and menu now.]"

SYSTEM_PROMPT = """
You are a professional and friendly customer service agent for AirPro HVAC Services.
Your job is to handle inbound customer calls efficiently and helpfully.

## Opening Greeting (say this immediately when the call starts)
"Thank you for calling AirPro HVAC Services! My name is Alex, and I'm happy to help you today.
I can assist you with the following:
  Option 1 — Schedule a new appointment or report an emergency
  Option 2 — Cancel an existing appointment
  Option 3 — Update or reschedule an appointment on our calendar
  Option 4 — Check the status of a current service order
  Option 5 — Basic troubleshooting over the phone
Which option would you like?"

## Menu Options in Detail

### Option 1 — Schedule / Emergency
- Ask if this is an emergency or a standard appointment request
- For emergencies: call estimate_arrival_time with urgency="emergency" and tell the customer how long until a tech arrives
- For standard: call get_available_slots, present the options, then call book_appointment once they choose
- Always verify account first before booking

### Option 2 — Cancel Appointment
- Verify account first
- Call get_appointments to show them what they have
- Ask which appointment to cancel, then call cancel_appointment
- Confirm the cancellation clearly

### Option 3 — Update / Reschedule
- Verify account first
- Call get_appointments to show current bookings
- Call get_available_slots to show new options
- Call reschedule_appointment once they confirm the new time
- Read back the new date and time to confirm

### Option 4 — Order Status
- Ask for their order ID (format: ORD-XXXX, e.g. ORD-8001)
- Call get_order_status and read the result clearly

### Option 5 — Basic Troubleshooting (no tools needed)
- AC not cooling: Check thermostat set to COOL, replace filter, ensure vents open
- Heating not working: Check thermostat set to HEAT, check breaker, clean filter
- Strange noises: Banging = loose part; squealing = belt issue; rattling = debris
- High energy bills: Dirty filter or aging system — recommend maintenance visit
- Unit won't turn on: Check thermostat batteries, breaker, emergency shutoff switch

## Account Verification Rules
- Always call verify_account (account number + last name) before any account action
- Account format: ACC-XXXX (e.g. ACC-1001)
- Never share details or make changes until verified

## General Rules
- Never make up appointment IDs, order numbers, or availability — always use tools
- If you cannot resolve an issue, offer to escalate or book a technician
- Be concise — customers want quick, clear help
- After completing a request, ask if there is anything else you can help with
"""

TOOLS = [
    types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="verify_account",
                description="Verify a customer's identity using their account number and last name before accessing any account information or making changes.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "account_number": types.Schema(
                            type=types.Type.STRING,
                            description="Customer account number, e.g. ACC-1001",
                        ),
                        "last_name": types.Schema(
                            type=types.Type.STRING,
                            description="Last name on the account",
                        ),
                    },
                    required=["account_number", "last_name"],
                ),
            ),
            types.FunctionDeclaration(
                name="get_appointments",
                description="Retrieve upcoming service appointments for a verified customer account.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "account_number": types.Schema(
                            type=types.Type.STRING,
                            description="Verified customer account number",
                        ),
                    },
                    required=["account_number"],
                ),
            ),
            types.FunctionDeclaration(
                name="reschedule_appointment",
                description="Reschedule an existing service appointment to a new date and time.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "appointment_id": types.Schema(
                            type=types.Type.STRING,
                            description="Appointment ID to reschedule, e.g. APT-4001",
                        ),
                        "new_date": types.Schema(
                            type=types.Type.STRING,
                            description="New date in YYYY-MM-DD format",
                        ),
                        "new_time": types.Schema(
                            type=types.Type.STRING,
                            description="New time, e.g. '10:00 AM'",
                        ),
                    },
                    required=["appointment_id", "new_date", "new_time"],
                ),
            ),
            types.FunctionDeclaration(
                name="get_order_status",
                description="Check the current status of a service or parts order.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "order_id": types.Schema(
                            type=types.Type.STRING,
                            description="Order ID to check, e.g. ORD-8001",
                        ),
                    },
                    required=["order_id"],
                ),
            ),
            types.FunctionDeclaration(
                name="get_available_slots",
                description="Get available appointment slots so the customer can pick a new time.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "start_date": types.Schema(
                            type=types.Type.STRING,
                            description="Start of date range in YYYY-MM-DD format",
                        ),
                        "end_date": types.Schema(
                            type=types.Type.STRING,
                            description="End of date range in YYYY-MM-DD format",
                        ),
                        "service_type": types.Schema(
                            type=types.Type.STRING,
                            description="Type of service needed (optional)",
                        ),
                    },
                    required=["start_date", "end_date"],
                ),
            ),
            types.FunctionDeclaration(
                name="book_appointment",
                description="Book a new service appointment for a verified customer.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "account_number": types.Schema(
                            type=types.Type.STRING,
                            description="Verified customer account number",
                        ),
                        "date": types.Schema(
                            type=types.Type.STRING,
                            description="Appointment date in YYYY-MM-DD format",
                        ),
                        "time": types.Schema(
                            type=types.Type.STRING,
                            description="Appointment time, e.g. '10:00 AM'",
                        ),
                        "service_type": types.Schema(
                            type=types.Type.STRING,
                            description="Type of service, e.g. 'AC Tune-Up', 'Heating Repair'",
                        ),
                    },
                    required=["account_number", "date", "time", "service_type"],
                ),
            ),
            types.FunctionDeclaration(
                name="cancel_appointment",
                description="Cancel an existing service appointment.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "appointment_id": types.Schema(
                            type=types.Type.STRING,
                            description="Appointment ID to cancel, e.g. APT-4001",
                        ),
                    },
                    required=["appointment_id"],
                ),
            ),
            types.FunctionDeclaration(
                name="estimate_arrival_time",
                description="Estimate how long until a technician can arrive. Use urgency='emergency' for emergencies.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "service_type": types.Schema(
                            type=types.Type.STRING,
                            description="Type of service or issue reported",
                        ),
                        "urgency": types.Schema(
                            type=types.Type.STRING,
                            description="One of: 'emergency', 'urgent', 'standard'",
                        ),
                    },
                    required=["service_type"],
                ),
            ),
        ]
    )
]

APPOINTMENT_TOOLS = {
    "book_appointment",
    "cancel_appointment",
    "reschedule_appointment",
}


def build_live_config(voice_name: str, voice_style: str) -> types.LiveConnectConfig:
    """Create a consistent Gemini Live config for both terminal and browser sessions."""
    return types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=voice_name
                )
            )
        ),
        system_instruction=types.Content(
            parts=[
                types.Part(
                    text=f"{SYSTEM_PROMPT}\n\n## Speaking Style\n{voice_style}"
                )
            ]
        ),
        tools=TOOLS,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
        input_audio_transcription=types.AudioTranscriptionConfig(),
    )
