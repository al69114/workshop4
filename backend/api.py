"""
FastAPI WebSocket server that streams voice agent events to the Next.js dashboard.

Events broadcast to all connected clients:
  {"type": "status",               "value": "listening" | "speaking" | "idle"}
  {"type": "transcript",           "role": "agent" | "customer", "text": "..."}
  {"type": "tool_call",            "name": "...", "args": {...}}
  {"type": "appointments_updated"}  — tells the dashboard to refetch /appointments
"""

import asyncio
import csv
import json
import os
from pathlib import Path

from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from google import genai
from google.genai import types
from google.genai.live import AsyncSession

load_dotenv(find_dotenv(usecwd=True))

import tools
from agent_config import (
    APPOINTMENT_TOOLS,
    INPUT_AUDIO_SAMPLE_RATE,
    MODEL,
    OPENING_PROMPT,
    build_live_config,
)
from voices import VOICES

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Connected WebSocket clients ────────────────────────────────────────────────

_clients: list[WebSocket] = []


async def broadcast(event: dict) -> None:
    """Send an event to every connected dashboard client."""
    message = json.dumps(event)
    for client in _clients[:]:          # copy so we can safely remove mid-loop
        try:
            await client.send_text(message)
        except Exception:
            _clients.remove(client)


def _resolve_voice(choice: str | None) -> dict:
    """Allow the frontend to pass either a voice number or name."""
    if not choice:
        return VOICES["1"]
    if choice in VOICES:
        return VOICES[choice]
    lowered = choice.strip().lower()
    for voice in VOICES.values():
        if voice["name"].lower() == lowered:
            return voice
    return VOICES["1"]


async def _receive_browser_audio(
    websocket: WebSocket, session: AsyncSession
) -> None:
    """Forward raw PCM chunks from the browser microphone to Gemini Live."""
    while True:
        message = await websocket.receive()
        if message["type"] == "websocket.disconnect":
            raise WebSocketDisconnect()

        audio_chunk = message.get("bytes")
        if audio_chunk:
            await session.send_realtime_input(
                audio=types.Blob(
                    data=audio_chunk,
                    mime_type=f"audio/pcm;rate={INPUT_AUDIO_SAMPLE_RATE}",
                )
            )
            continue

        payload_text = message.get("text")
        if not payload_text:
            continue

        payload = json.loads(payload_text)
        if payload.get("type") == "audio_stream_end":
            await session.send_realtime_input(audio_stream_end=True)


async def _send_model_audio(
    websocket: WebSocket, session: AsyncSession
) -> None:
    """Stream Gemini responses back to the browser and dashboard listeners."""
    agent_speaking = False

    async for message in session.receive():
        server_content = message.server_content

        if server_content:
            if server_content.input_transcription:
                text = (server_content.input_transcription.text or "").strip()
                if text:
                    await broadcast(
                        {"type": "transcript", "role": "customer", "text": text}
                    )

            if server_content.model_turn:
                if not agent_speaking:
                    agent_speaking = True
                    await broadcast({"type": "status", "value": "speaking"})

                for part in server_content.model_turn.parts:
                    if getattr(part, "thought", False):
                        continue
                    if part.text:
                        await broadcast(
                            {
                                "type": "transcript",
                                "role": "agent",
                                "text": part.text,
                            }
                        )
                    if part.inline_data and part.inline_data.data:
                        await websocket.send_bytes(part.inline_data.data)

            if server_content.turn_complete:
                agent_speaking = False
                await broadcast({"type": "status", "value": "listening"})

        if message.tool_call:
            responses = []
            for func_call in message.tool_call.function_calls:
                args = dict(func_call.args)
                await broadcast(
                    {"type": "tool_call", "name": func_call.name, "args": args}
                )
                result = tools.dispatch(func_call.name, args)
                responses.append(
                    types.FunctionResponse(
                        name=func_call.name,
                        id=func_call.id,
                        response={"output": json.dumps(result)},
                    )
                )

            if any(
                func_call.name in APPOINTMENT_TOOLS
                for func_call in message.tool_call.function_calls
            ):
                await broadcast({"type": "appointments_updated"})

            await session.send_tool_response(function_responses=responses)


# ── WebSocket endpoint ─────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    _clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()   # keep connection alive
    except WebSocketDisconnect:
        if websocket in _clients:
            _clients.remove(websocket)


@app.websocket("/voice")
async def voice_endpoint(websocket: WebSocket) -> None:
    """Bridge browser microphone audio to a Gemini Live session."""
    await websocket.accept()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        await websocket.send_text(
            json.dumps(
                {
                    "type": "error",
                    "message": "GEMINI_API_KEY is not set on the backend.",
                }
            )
        )
        await websocket.close(code=1011)
        return

    voice = _resolve_voice(websocket.query_params.get("voice"))
    client = genai.Client(api_key=api_key)
    config = build_live_config(voice["name"], voice["style"])

    await websocket.send_text(
        json.dumps({"type": "session_ready", "voice": voice["name"]})
    )

    try:
        async with client.aio.live.connect(model=MODEL, config=config) as session:
            await broadcast({"type": "status", "value": "listening"})
            await session.send_client_content(
                turns=types.Content(
                    role="user",
                    parts=[types.Part(text=OPENING_PROMPT)],
                )
            )

            browser_task = asyncio.create_task(
                _receive_browser_audio(websocket, session)
            )
            model_task = asyncio.create_task(_send_model_audio(websocket, session))

            done, pending = await asyncio.wait(
                {browser_task, model_task},
                return_when=asyncio.FIRST_EXCEPTION,
            )

            for task in pending:
                task.cancel()
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)

            for task in done:
                if task.cancelled():
                    continue
                exc = task.exception()
                if exc:
                    raise exc
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_text(
                json.dumps({"type": "error", "message": str(exc)})
            )
        except Exception:
            pass
    finally:
        await broadcast({"type": "status", "value": "idle"})
        try:
            await websocket.close()
        except Exception:
            pass


# ── REST endpoints ─────────────────────────────────────────────────────────────

@app.get("/appointments")
async def get_appointments() -> list[dict]:
    """Return the current appointments CSV as JSON."""
    csv_path = Path(os.environ.get("APPOINTMENTS_CSV", "appointments.csv"))
    if not csv_path.exists():
        return []
    with open(csv_path, newline="") as f:
        return list(csv.DictReader(f))
