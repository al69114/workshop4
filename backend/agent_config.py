"""
Shared Gemini Live configuration for the HVAC agents.
"""

from google.genai import types

MODEL = "gemini-3.1-flash-live-preview"
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
- For standard: call get_available_slots right away, then read only the first 2 or 3 best openings aloud in a short format: day, time, and available technician names
- Keep availability responses brief and easy to hear, for example: "I have Tuesday at 10 AM with Maria or Jake, Wednesday at 1 PM with Sam, and Thursday at 9 AM with Maria. Which one works for you?"
- When the tool returns a spoken_summary, use that wording closely instead of improvising a long or messy list
- Once they choose an opening, ask for their full name and call book_appointment with that name
- After listing openings, always ask "Would you like me to repeat those options more slowly?"
- Do not ask for an account number for a brand-new booking
- If the caller says "schedule a new appointment" or picks Option 1 without giving dates, treat it as a standard scheduling request and read the next available openings immediately

### Option 2 — Cancel Appointment
- Ask for the caller's full name and appointment ID
- Call cancel_appointment with the full name and appointment ID
- Confirm the cancellation clearly

### Option 3 — Update / Reschedule
- Verify account first
- Call get_appointments to show current bookings
- Call get_available_slots to show new options
- When reading reschedule options, say the date, time, and available technicians for each opening
- After listing the openings, offer to repeat them more slowly if needed
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
- Always call verify_account (account number + last name) before existing-account actions that need account access, such as reschedules or account lookups
- Do not ask for account verification for a cancellation when the caller provides their full name and appointment ID
- Account format: ACC-XXXX (e.g. ACC-1001)
- Never share details or make changes until verified

## General Rules
- Never make up appointment IDs, order numbers, or availability — always use tools
- After every tool call, say the result out loud in a concise natural sentence instead of staying silent
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
                description="Get available appointment openings in a date range, including which technicians are available for each opening.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "start_date": types.Schema(
                            type=types.Type.STRING,
                            description="Start of date range in YYYY-MM-DD format. Optional for next available openings.",
                        ),
                        "end_date": types.Schema(
                            type=types.Type.STRING,
                            description="End of date range in YYYY-MM-DD format. Optional for next available openings.",
                        ),
                        "service_type": types.Schema(
                            type=types.Type.STRING,
                            description="Type of service needed (optional)",
                        ),
                    },
                ),
            ),
            types.FunctionDeclaration(
                name="book_appointment",
                description="Book a new service appointment for a customer by full name using one of the available openings returned by get_available_slots.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "customer_name": types.Schema(
                            type=types.Type.STRING,
                            description="Customer full name for the new booking",
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
                    required=["customer_name", "date", "time", "service_type"],
                ),
            ),
            types.FunctionDeclaration(
                name="cancel_appointment",
                description="Cancel an existing service appointment using the customer's full name and appointment ID.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "customer_name": types.Schema(
                            type=types.Type.STRING,
                            description="Customer full name on the appointment",
                        ),
                        "appointment_id": types.Schema(
                            type=types.Type.STRING,
                            description="Appointment ID to cancel, e.g. APT-4001",
                        ),
                    },
                    required=["customer_name", "appointment_id"],
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
    config_kwargs = {
        "response_modalities": ["AUDIO"],
        "speech_config": types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=voice_name
                )
            )
        ),
        "system_instruction": types.Content(
            parts=[
                types.Part(
                    text=f"{SYSTEM_PROMPT}\n\n## Speaking Style\n{voice_style}"
                )
            ]
        ),
        "tools": TOOLS,
        "input_audio_transcription": types.AudioTranscriptionConfig(),
        "output_audio_transcription": types.AudioTranscriptionConfig(),
        "realtime_input_config": types.RealtimeInputConfig(
            automatic_activity_detection=types.AutomaticActivityDetection(
                disabled=False,
                start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_LOW,
                end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_HIGH,
                prefix_padding_ms=160,
                silence_duration_ms=700,
            ),
            activity_handling=types.ActivityHandling.NO_INTERRUPTION,
        ),
    }

    # The 2.5 native-audio model family documents thinking support explicitly.
    # Avoid sending this field to newer Live models unless they advertise it.
    if "native-audio" in MODEL:
        config_kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)

    return types.LiveConnectConfig(
        **config_kwargs,
    )
