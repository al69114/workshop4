"""
Optional local terminal microphone agent for AirPro HVAC.

This is separate from `main.py` so the backend server can run by itself while
the browser controls the live call flow.
"""

import asyncio
import json
import os
import sys

import pyaudio
from dotenv import find_dotenv, load_dotenv
from google import genai
from google.genai import types
from google.genai.errors import APIError

load_dotenv(find_dotenv(usecwd=True))

from agent_config import (
    APPOINTMENT_TOOLS,
    INPUT_AUDIO_SAMPLE_RATE,
    MODEL,
    OUTPUT_AUDIO_SAMPLE_RATE,
    build_opening_prompt,
    build_live_config,
)
from api import broadcast
import tools
from voices import VOICES

MIC_SAMPLE_RATE = INPUT_AUDIO_SAMPLE_RATE
SPEAKER_SAMPLE_RATE = OUTPUT_AUDIO_SAMPLE_RATE
CHANNELS = 1
CHUNK = 1024
FORMAT = pyaudio.paInt16


def pick_voice() -> dict:
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


def _friendly_api_error_message(exc: APIError) -> str:
    details = str(exc)
    if "reported as leaked" in details.lower():
        return (
            "Gemini rejected GEMINI_API_KEY because it was reported as leaked.\n"
            "Create a fresh API key, update backend/.env, and restart the terminal agent."
        )
    return f"Gemini Live connection failed: {details}"


async def run_agent(voice: dict) -> None:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        sys.exit(
            "Error: GEMINI_API_KEY is not set. Copy .env.example to .env and add your key."
        )

    client = genai.Client(api_key=api_key)
    config = build_live_config(voice["name"], voice["style"], "en")

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
    agent_speaking = False

    try:
        async with client.aio.live.connect(model=MODEL, config=config) as session:
            await broadcast({"type": "status", "value": "listening"})
            await session.send_realtime_input(text=build_opening_prompt("en"))

            async def stream_microphone() -> None:
                while True:
                    pcm = await loop.run_in_executor(
                        None,
                        lambda: mic_stream.read(CHUNK, exception_on_overflow=False),
                    )
                    await session.send_realtime_input(
                        audio=types.Blob(
                            data=pcm,
                            mime_type=f"audio/pcm;rate={MIC_SAMPLE_RATE}",
                        )
                    )

            async def play_responses() -> None:
                nonlocal agent_speaking
                async for message in session.receive():
                    server_content = message.server_content

                    if server_content:
                        if server_content.input_transcription:
                            text = server_content.input_transcription.text
                            if text and text.strip():
                                print(f"Customer: {text.strip()}")
                                await broadcast(
                                    {
                                        "type": "transcript",
                                        "role": "customer",
                                        "text": text.strip(),
                                    }
                                )

                        if server_content.model_turn:
                            agent_speaking = True
                            await broadcast({"type": "status", "value": "speaking"})
                            for part in server_content.model_turn.parts:
                                if getattr(part, "thought", False):
                                    continue
                                if part.text:
                                    print(f"Agent: {part.text}")
                                    await broadcast(
                                        {
                                            "type": "transcript",
                                            "role": "agent",
                                            "text": part.text,
                                        }
                                    )
                                if part.inline_data and part.inline_data.data:
                                    await loop.run_in_executor(
                                        None,
                                        speaker_stream.write,
                                        part.inline_data.data,
                                    )

                        if server_content.turn_complete:
                            agent_speaking = False
                            await broadcast({"type": "status", "value": "listening"})
                            print("[listening...]")

                    if message.tool_call:
                        responses = []
                        for func_call in message.tool_call.function_calls:
                            args = dict(func_call.args)
                            print(f"[tool] {func_call.name}({json.dumps(args)})")
                            await broadcast(
                                {"type": "tool_call", "name": func_call.name, "args": args}
                            )
                            result = tools.dispatch(func_call.name, args)
                            print(f"[result] {json.dumps(result)}")
                            responses.append(
                                types.FunctionResponse(
                                    name=func_call.name,
                                    id=func_call.id,
                                    response={"output": json.dumps(result)},
                                )
                            )

                        if any(
                            fc.name in APPOINTMENT_TOOLS
                            for fc in message.tool_call.function_calls
                        ):
                            await broadcast({"type": "appointments_updated"})

                        await session.send_tool_response(function_responses=responses)

            results = await asyncio.gather(
                stream_microphone(),
                play_responses(),
                return_exceptions=True,
            )
            for result in results:
                if isinstance(result, Exception):
                    raise result
    except APIError as exc:
        print(_friendly_api_error_message(exc))
    finally:
        await broadcast({"type": "status", "value": "idle"})
        mic_stream.stop_stream()
        mic_stream.close()
        speaker_stream.stop_stream()
        speaker_stream.close()
        pa.terminate()


async def main() -> None:
    voice = pick_voice()
    await run_agent(voice)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCall ended. Goodbye!")
