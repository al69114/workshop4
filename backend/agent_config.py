"""
Shared Gemini Live configuration for the HVAC agents.
"""

from google.genai import types

MODEL = "gemini-3.1-flash-live-preview"
INPUT_AUDIO_SAMPLE_RATE = 16_000
OUTPUT_AUDIO_SAMPLE_RATE = 24_000
SUPPORTED_LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "hi": "Hindi",
    "it": "Italian",
    "pt": "Portuguese",
}
LANGUAGE_OPENINGS = {
    "en": "Thank you for calling AIRPRO AI AGENT! My name is Alex, and I'm happy to help you today. What can I help you with?",
    "es": "Gracias por llamar a AIRPRO AI AGENT. Mi nombre es Alex y con gusto le ayudo hoy. ¿En qué le puedo ayudar?",
    "fr": "Merci d'avoir appelé AIRPRO AI AGENT. Je m'appelle Alex et je suis heureux de vous aider aujourd'hui. Comment puis-je vous aider ?",
    "de": "Danke, dass Sie AIRPRO AI AGENT angerufen haben. Mein Name ist Alex und ich helfe Ihnen heute gern. Womit kann ich Ihnen helfen?",
    "hi": "AIRPRO AI AGENT को कॉल करने के लिए धन्यवाद। मेरा नाम Alex है, और मैं आज आपकी मदद करके खुश हूँ। मैं आपकी किस तरह मदद कर सकता हूँ?",
    "it": "Grazie per aver chiamato AIRPRO AI AGENT. Mi chiamo Alex e sono felice di aiutarla oggi. In cosa posso aiutarla?",
    "pt": "Obrigado por ligar para a AIRPRO AI AGENT. Meu nome é Alex e fico feliz em ajudar você hoje. Como posso ajudar?",
}
LANGUAGE_OPTION_SUMMARIES = {
    "en": "I can help with scheduling, cancellations, rescheduling, order status, or basic troubleshooting. What do you need today?",
    "es": "Puedo ayudarle con citas nuevas, cancelaciones, cambios de cita, estado de órdenes o solución básica de problemas. ¿Qué necesita hoy?",
    "fr": "Je peux vous aider pour une nouvelle réservation, une annulation, un changement de rendez-vous, le statut d'une commande ou un dépannage de base. De quoi avez-vous besoin aujourd'hui ?",
    "de": "Ich kann Ihnen bei neuen Terminen, Stornierungen, Terminänderungen, dem Status eines Auftrags oder bei einfacher Fehlerbehebung helfen. Wobei brauchen Sie heute Hilfe?",
    "hi": "मैं नई अपॉइंटमेंट बुक करने, कैंसिल करने, रीशेड्यूल करने, ऑर्डर स्टेटस बताने या बेसिक ट्रबलशूटिंग में मदद कर सकता हूँ। आपको आज किस चीज़ में मदद चाहिए?",
    "it": "Posso aiutarla con nuove prenotazioni, cancellazioni, riprogrammazioni, stato degli ordini o assistenza di base. Di cosa ha bisogno oggi?",
    "pt": "Posso ajudar com agendamentos, cancelamentos, remarcações, status de pedidos ou solução básica de problemas. Do que você precisa hoje?",
}


def build_opening_prompt(language_code: str = "en") -> str:
    """Create a language-specific first-turn instruction for the live call."""
    language_name = SUPPORTED_LANGUAGES.get(language_code, SUPPORTED_LANGUAGES["en"])
    opening_line = LANGUAGE_OPENINGS.get(language_code, LANGUAGE_OPENINGS["en"])
    option_summary = LANGUAGE_OPTION_SUMMARIES.get(
        language_code,
        LANGUAGE_OPTION_SUMMARIES["en"],
    )
    return (
        "[Call connected. "
        f"Respond entirely in {language_name}. "
        f'Start with this exact greeting: "{opening_line}" '
        f'If the caller asks what you can help with, use this wording: "{option_summary}".]'
    )

SYSTEM_PROMPT = """
You are a professional and friendly customer service agent for AIRPRO AI AGENT.
Your job is to handle inbound customer calls efficiently and helpfully.

## Opening Greeting (say this immediately when the call starts)
"Thank you for calling AIRPRO AI AGENT! My name is Alex, and I'm happy to help you today. What can I help you with?"

## If The Caller Asks For Options
- Do not start by reading a numbered menu unless the caller asks for it
- If the caller asks what you can help with, answer in one short natural sentence
- Do not say "Option 1", "Option 2", and so on unless the caller explicitly asks for numbered options
- Preferred concise wording: "I can help with scheduling, cancellations, rescheduling, order status, or basic troubleshooting. What do you need today?"

## Menu Options in Detail

### Option 1 — Schedule / Emergency
- Ask if this is an emergency or a standard appointment request
- For emergencies: call get_available_slots with urgency="emergency" first and only offer openings that are today or within the next two days
- If emergency openings are available, read only the first 2 or 3 concise options aloud
- If no emergency openings are available in that window, call estimate_arrival_time with urgency="emergency" and tell the customer how long until a tech arrives
- For standard: call get_available_slots right away, then read only the first 2 or 3 best openings aloud in a short format: day and time only
- Do not mention technician names when offering scheduling openings
- Keep availability responses brief and easy to hear, for example: "I have Tuesday at 10 AM, Wednesday at 1 PM, and Thursday at 9 AM. Which one works for you?"
- When the tool returns a spoken_summary, use that wording closely instead of improvising a long or messy list
- Once they choose an opening, ask for their full name, then say it back clearly in a confirmation sentence such as "I have your name as Priya Patel, is that correct?"
- Do not call book_appointment until the caller confirms the full name is correct
- After the caller confirms their full name and chosen slot, read the name, date, and time back one more time to finalize the booking details
- Before booking, call get_slot_technicians for that exact date and time and tell the caller which technicians are available for that chosen slot
- If the caller wants a different technician, call get_technician_slots to find another time for that technician and offer the matching openings
- Accept either a technician's first name or full name when the caller asks for a specific technician
- If the caller picks one of those alternate openings, confirm the new date, time, and technician, then call book_appointment with technician_name set
- If the caller is happy with one of the technicians already available for the chosen slot, call book_appointment with that technician_name
- If the caller corrects their name after the booking is already created, call update_appointment_customer_name right away and confirm that the appointment record was fixed
- After listing openings, always ask "Would you like me to repeat those options more slowly?"
- Do not ask for an account number for a brand-new booking
- If the caller says "schedule a new appointment" or picks Option 1 without giving dates, treat it as a standard scheduling request and read the next available openings immediately

### Option 2 — Cancel Appointment
- Ask for the caller's first name and appointment number
- Accept either a bare appointment number like 3487 or a full ID like APT-3487
- Call cancel_appointment with the first name and appointment number
- Confirm the cancellation clearly

### Option 3 — Update / Reschedule
- Ask for the caller's first name and appointment number
- Accept either a bare appointment number like 3487 or a full ID like APT-3487
- Call get_available_slots to show new options
- When reading reschedule options, say only the date and time for each opening
- After listing the openings, offer to repeat them more slowly if needed
- Call reschedule_appointment with the first name, appointment number, and new time once they confirm the new slot
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

## Technician Questions
- If the caller asks about a technician by name, call get_technician_feedback
- Accept either a technician's first name or full name when looking them up
- Read the rating using the tool's exact `rating_text` field so the scale stays "out of 10"
- Then read the summary word for word

## Account Verification Rules
- Always call verify_account (account number + last name) before existing-account actions that need account access, such as account lookups
- Do not ask for account verification for a cancellation when the caller provides their first name and appointment number
- Do not ask for account verification for a reschedule when the caller provides their first name and appointment number
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
                description="Reschedule an existing service appointment using the customer's first name, appointment number, and the new date and time.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "first_name": types.Schema(
                            type=types.Type.STRING,
                            description="Customer first name on the appointment",
                        ),
                        "appointment_id": types.Schema(
                            type=types.Type.STRING,
                            description="Appointment number or full ID to reschedule, e.g. 4001 or APT-4001",
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
                    required=["first_name", "appointment_id", "new_date", "new_time"],
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
                name="get_technician_feedback",
                description="Get a playful rating and summary for a technician when a caller asks about them by name.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "technician_name": types.Schema(
                            type=types.Type.STRING,
                            description="Technician full name, e.g. Ryan Majd",
                        ),
                    },
                    required=["technician_name"],
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
                        "urgency": types.Schema(
                            type=types.Type.STRING,
                            description="Use 'emergency' to limit openings to today through the next two days. Otherwise use 'standard'.",
                        ),
                    },
                ),
            ),
            types.FunctionDeclaration(
                name="get_slot_technicians",
                description="Get the technicians available for one exact appointment slot after the caller has chosen a date and time.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "date": types.Schema(
                            type=types.Type.STRING,
                            description="Appointment date in YYYY-MM-DD format",
                        ),
                        "time": types.Schema(
                            type=types.Type.STRING,
                            description="Appointment time, e.g. '10:00 AM'",
                        ),
                    },
                    required=["date", "time"],
                ),
            ),
            types.FunctionDeclaration(
                name="get_technician_slots",
                description="Find openings where a requested technician is available.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "technician_name": types.Schema(
                            type=types.Type.STRING,
                            description="Technician full name, e.g. Ryan Majd",
                        ),
                        "start_date": types.Schema(
                            type=types.Type.STRING,
                            description="Start of date range in YYYY-MM-DD format. Optional.",
                        ),
                        "end_date": types.Schema(
                            type=types.Type.STRING,
                            description="End of date range in YYYY-MM-DD format. Optional.",
                        ),
                    },
                    required=["technician_name"],
                ),
            ),
            types.FunctionDeclaration(
                name="book_appointment",
                description="Book a new service appointment for a customer by full name using one of the available openings returned by get_available_slots, optionally with a specific available technician.",
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
                        "technician_name": types.Schema(
                            type=types.Type.STRING,
                            description="Optional technician full name if the caller selects a specific available technician",
                        ),
                    },
                    required=["customer_name", "date", "time", "service_type"],
                ),
            ),
            types.FunctionDeclaration(
                name="update_appointment_customer_name",
                description="Update the customer name on an existing appointment when the caller corrects their name after a booking was created.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "appointment_id": types.Schema(
                            type=types.Type.STRING,
                            description="Appointment ID to update, e.g. APT-4001",
                        ),
                        "customer_name": types.Schema(
                            type=types.Type.STRING,
                            description="Corrected customer full name for the appointment",
                        ),
                    },
                    required=["appointment_id", "customer_name"],
                ),
            ),
            types.FunctionDeclaration(
                name="cancel_appointment",
                description="Cancel an existing service appointment using the customer's first name and appointment number.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "first_name": types.Schema(
                            type=types.Type.STRING,
                            description="Customer first name on the appointment",
                        ),
                        "appointment_id": types.Schema(
                            type=types.Type.STRING,
                            description="Appointment number or full ID to cancel, e.g. 4001 or APT-4001",
                        ),
                    },
                    required=["first_name", "appointment_id"],
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
    "update_appointment_customer_name",
    "cancel_appointment",
    "reschedule_appointment",
}


def build_live_config(
    voice_name: str,
    voice_style: str,
    language_code: str = "en",
) -> types.LiveConnectConfig:
    """Create a consistent Gemini Live config for both terminal and browser sessions."""
    language_name = SUPPORTED_LANGUAGES.get(language_code, SUPPORTED_LANGUAGES["en"])
    opening_line = LANGUAGE_OPENINGS.get(language_code, LANGUAGE_OPENINGS["en"])
    option_summary = LANGUAGE_OPTION_SUMMARIES.get(
        language_code,
        LANGUAGE_OPTION_SUMMARIES["en"],
    )
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
                    text=(
                        f"{SYSTEM_PROMPT}\n\n"
                        f"## Response Language\n"
                        f"- Speak entirely in {language_name} unless the caller clearly asks to switch languages\n"
                        f"- Do not answer in English when {language_name} is selected unless the caller explicitly switches to English\n"
                        f"- Keep all greetings, follow-up questions, confirmations, booking prompts, cancellation prompts, rescheduling prompts, troubleshooting steps, and closing lines in {language_name}\n"
                        f"- Keep appointment IDs, order IDs, and exact names accurate when reading them aloud\n\n"
                        f"## Selected Language Opening\n"
                        f'- Use this exact opening in {language_name}: "{opening_line}"\n'
                        f"- If the caller asks what you can help with, use this concise wording in {language_name}: \"{option_summary}\"\n\n"
                        f"## Speaking Style\n{voice_style}"
                    )
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
