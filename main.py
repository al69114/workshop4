"""
HVAC Voice Agent Workshop
=========================
A real-time voice agent powered by Gemini Live API that handles inbound
customer calls for an HVAC company — rescheduling, order status, account
verification, and basic troubleshooting.

Prerequisites:
  - Python 3.10+
  - A Gemini API key in .env (see .env.example)
  - PortAudio installed (required by PyAudio):
      macOS:  brew install portaudio
      Ubuntu: sudo apt-get install portaudio19-dev
"""

import json
import asyncio
import os
import sys

import pyaudio
from dotenv import load_dotenv
from google import genai
from google.genai import types
from voices import VOICES
import tools

load_dotenv()

# ── Model ──────────────────────────────────────────────────────────────────────
MODEL = "gemini-2.5-flash-native-audio-preview-12-2025"

# ── Audio configuration ────────────────────────────────────────────────────────
MIC_SAMPLE_RATE = 16_000      # Hz — what Gemini Live expects as input
SPEAKER_SAMPLE_RATE = 24_000  # Hz — what Gemini Live sends back
CHANNELS = 1
CHUNK = 1024
FORMAT = pyaudio.paInt16

# ── System Prompt ──────────────────────────────────────────────────────────────
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

# ── Function declarations (tools the agent can call) ──────────────────────────
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


# ── Voice picker ───────────────────────────────────────────────────────────────

def pick_voice() -> dict:
    """Prompt the user to pick a voice and return the full voice dict."""
    print("\nAvailable voices:")
    for key, voice in VOICES.items():
        print(f"  {key}. {voice['name']} — {voice['description']}")
    while True:
        choice = input("\nPick a voice [1-8] (press Enter for default): ").strip()
        if choice == "":
            return VOICES["1"]
        if choice in VOICES:
            return VOICES[choice]
        print("  Invalid choice, please enter a number between 1 and 8.")


# ── Voice agent ────────────────────────────────────────────────────────────────

async def run_agent() -> None:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        sys.exit(
            "Error: GEMINI_API_KEY is not set.\n"
            "Copy .env.example to .env and add your key."
        )

    voice = pick_voice()

    system_prompt_with_style = (
        SYSTEM_PROMPT
        + f"\n\n## Speaking Style\n{voice['style']}"
    )

    client = genai.Client(api_key=api_key)

    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=voice["name"]
                )
            )
        ),
        system_instruction=types.Content(
            parts=[types.Part(text=system_prompt_with_style)]
        ),
        tools=TOOLS,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    )

    pa = pyaudio.PyAudio()
    mic_stream = pa.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=MIC_SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK,
    )
    speaker_stream = pa.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=SPEAKER_SAMPLE_RATE,
        output=True,
    )

    print("=" * 52)
    print(f"  AirPro HVAC Agent ({voice['name']}) — ready for calls!")
    print("  Press Ctrl+C to end the call.")
    print("=" * 52)

    loop = asyncio.get_event_loop()

    # Mute mic while agent speaks to prevent acoustic echo
    agent_speaking = False

    try:
        async with client.aio.live.connect(model=MODEL, config=config) as session:

            # Trigger the opening greeting immediately when the call connects
            await session.send(
                input="[Call connected. Deliver the opening greeting and menu now.]",
                end_of_turn=True,
            )

            async def stream_microphone() -> None:
                nonlocal agent_speaking
                try:
                    while True:
                        pcm = await loop.run_in_executor(
                            None,
                            lambda: mic_stream.read(CHUNK, exception_on_overflow=False),
                        )
                        if not agent_speaking:
                            await session.send_realtime_input(
                                audio=types.Blob(
                                    data=pcm,
                                    mime_type=f"audio/pcm;rate={MIC_SAMPLE_RATE}",
                                )
                            )
                except Exception as e:
                    print(f"[mic error] {e}")
                    raise

            async def play_responses() -> None:
                nonlocal agent_speaking
                try:
                    while True:
                        async for message in session.receive():
                            # ── Audio / text response ──────────────────────
                            server_content = message.server_content
                            if server_content:
                                if server_content.model_turn:
                                    agent_speaking = True
                                    for part in server_content.model_turn.parts:
                                        if getattr(part, "thought", False):
                                            continue
                                        if part.text:
                                            print(f"Agent: {part.text}")
                                        if part.inline_data and part.inline_data.data:
                                            await loop.run_in_executor(
                                                None,
                                                speaker_stream.write,
                                                part.inline_data.data,
                                            )
                                if server_content.turn_complete:
                                    agent_speaking = False
                                    print("[listening...]")

                            # ── Tool call ──────────────────────────────────
                            if message.tool_call:
                                responses = []
                                for func_call in message.tool_call.function_calls:
                                    print(f"[tool] {func_call.name}({json.dumps(dict(func_call.args))})")
                                    result = tools.dispatch(func_call.name, dict(func_call.args))
                                    print(f"[tool result] {json.dumps(result)}")
                                    responses.append(
                                        types.FunctionResponse(
                                            name=func_call.name,
                                            id=func_call.id,
                                            response={"output": json.dumps(result)},
                                        )
                                    )
                                await session.send(
                                    input=types.LiveClientToolResponse(
                                        function_responses=responses
                                    )
                                )

                except Exception as e:
                    print(f"[response error] {e}")
                    raise

            results = await asyncio.gather(
                stream_microphone(), play_responses(), return_exceptions=True
            )
            for r in results:
                if isinstance(r, Exception):
                    print(f"[task error] {r}")

    except KeyboardInterrupt:
        print("\nCall ended. Goodbye!")
    finally:
        mic_stream.stop_stream()
        mic_stream.close()
        speaker_stream.stop_stream()
        speaker_stream.close()
        pa.terminate()


if __name__ == "__main__":
    asyncio.run(run_agent())
