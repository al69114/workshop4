"""
FastAPI WebSocket server that streams voice agent events to the Next.js dashboard.

Events broadcast to all connected clients:
  {"type": "status",               "value": "listening" | "speaking" | "idle"}
  {"type": "transcript",           "role": "agent" | "customer", "text": "..."}
  {"type": "tool_call",            "name": "...", "args": {...}}
  {"type": "appointments_updated"}  — tells the dashboard to refetch /appointments
"""

import asyncio
import json
import os

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
    SUPPORTED_LANGUAGES,
    build_opening_prompt,
    build_live_config,
)
from services import csv_service
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


async def _send_voice_event(websocket: WebSocket, event: dict) -> None:
    """Send a JSON event over the active voice socket."""
    await websocket.send_text(json.dumps(event))


def _normalize_transcript_text(text: str) -> str:
    """Collapse repeated whitespace in transcript text."""
    return " ".join(text.split()).replace(" ,", ",").replace(" .", ".")


def _compact_transcript_text(text: str) -> str:
    """Remove whitespace so partial cumulative transcript chunks can be compared."""
    return "".join(text.split())


def _suffix_after_compact_prefix(text: str, prefix_length: int) -> str:
    """Return the raw suffix after consuming prefix_length non-whitespace chars."""
    consumed = 0
    index = 0
    while index < len(text) and consumed < prefix_length:
        if not text[index].isspace():
            consumed += 1
        index += 1
    return text[index:]


def _merge_transcript_chunks(previous: str, next_chunk: str) -> str:
    """Merge incremental transcript chunks into one readable sentence."""
    previous = _normalize_transcript_text(previous)
    next_chunk = _normalize_transcript_text(next_chunk)
    if not next_chunk:
        return previous
    if not previous:
        return next_chunk

    previous_compact = _compact_transcript_text(previous)
    next_compact = _compact_transcript_text(next_chunk)

    if not next_compact:
        return previous
    if not previous_compact:
        return next_chunk
    if next_compact == previous_compact:
        return previous if len(previous) >= len(next_chunk) else next_chunk
    if next_compact in previous_compact:
        return previous
    if next_compact.startswith(previous_compact):
        suffix = _normalize_transcript_text(
            _suffix_after_compact_prefix(next_chunk, len(previous_compact))
        )
        if not suffix:
            return previous
        separator = (
            " "
            if previous[-1].isalnum() and suffix[0].isalnum()
            else ""
        )
        return _normalize_transcript_text(f"{previous}{separator}{suffix}")
    if previous_compact in next_compact:
        return previous

    max_overlap = min(len(previous_compact), len(next_compact))
    for overlap in range(max_overlap, 0, -1):
        if previous_compact.endswith(next_compact[:overlap]):
            suffix = _normalize_transcript_text(
                _suffix_after_compact_prefix(next_chunk, overlap)
            )
            if not suffix:
                return previous
            separator = (
                " "
                if previous[-1].isalnum() and suffix[0].isalnum()
                else ""
            )
            return _normalize_transcript_text(f"{previous}{separator}{suffix}")

    separator = (
        " "
        if previous[-1].isalnum() and next_chunk[0].isalnum()
        else ""
    )
    return _normalize_transcript_text(f"{previous}{separator}{next_chunk}")


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


def _resolve_language(choice: str | None) -> str:
    """Resolve a supported UI language code for the live session."""
    if not choice:
        return "en"
    lowered = choice.strip().lower()
    if lowered in SUPPORTED_LANGUAGES:
        return lowered
    return "en"


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
    agent_turn_id = 0
    customer_turn_id = 0
    customer_turn_open = False
    customer_turn_text = ""
    agent_turn_transcript_text = ""
    agent_turn_model_text = ""

    def ensure_agent_turn_started() -> str:
        nonlocal agent_speaking, agent_turn_id
        nonlocal agent_turn_transcript_text, agent_turn_model_text
        if not agent_speaking:
            agent_speaking = True
            agent_turn_id += 1
            agent_turn_transcript_text = ""
            agent_turn_model_text = ""
        return f"agent-{agent_turn_id}"

    def current_agent_turn_text(final: bool = False) -> str:
        """Prefer model text at the end of a turn; use live transcript while speaking."""
        if final and agent_turn_model_text:
            return agent_turn_model_text
        return agent_turn_transcript_text or agent_turn_model_text

    while True:
        async for message in session.receive():
            server_content = message.server_content

            if server_content:
                if server_content.input_transcription:
                    text = _normalize_transcript_text(
                        server_content.input_transcription.text or ""
                    )
                    if text:
                        if not customer_turn_open:
                            customer_turn_open = True
                            customer_turn_id += 1
                        customer_turn_text = _merge_transcript_chunks(
                            customer_turn_text, text
                        )
                        event = {
                            "type": "transcript",
                            "role": "customer",
                            "text": customer_turn_text,
                            "turn_id": f"customer-{customer_turn_id}",
                            "finished": bool(
                                server_content.input_transcription.finished
                            ),
                        }
                        await _send_voice_event(websocket, event)
                        await broadcast(event)
                        if server_content.input_transcription.finished:
                            customer_turn_open = False
                            customer_turn_text = ""

                output_text = ""
                if server_content.output_transcription:
                    output_text = _normalize_transcript_text(
                        server_content.output_transcription.text or ""
                    )
                    if output_text:
                        ensure_agent_turn_started()
                        agent_turn_transcript_text = _merge_transcript_chunks(
                            agent_turn_transcript_text, output_text
                        )
                        live_text = current_agent_turn_text()
                        event = {
                            "type": "transcript",
                            "role": "agent",
                            "text": live_text,
                            "turn_id": f"agent-{agent_turn_id}",
                            "finished": bool(
                                server_content.output_transcription.finished
                            ),
                        }
                        await _send_voice_event(websocket, event)
                        await broadcast(event)

                if server_content.model_turn:
                    if customer_turn_open and customer_turn_text:
                        event = {
                            "type": "transcript",
                            "role": "customer",
                            "text": customer_turn_text,
                            "turn_id": f"customer-{customer_turn_id}",
                            "finished": True,
                        }
                        await _send_voice_event(websocket, event)
                        await broadcast(event)
                        customer_turn_open = False
                        customer_turn_text = ""
                    if not agent_speaking:
                        ensure_agent_turn_started()
                        await _send_voice_event(
                            websocket, {"type": "agent_state", "value": "speaking"}
                        )
                        await broadcast({"type": "status", "value": "speaking"})

                    for part in server_content.model_turn.parts:
                        if getattr(part, "thought", False):
                            continue
                        if part.text:
                            agent_turn_model_text = _merge_transcript_chunks(
                                agent_turn_model_text, part.text
                            )
                            if not output_text and not agent_turn_transcript_text:
                                event = {
                                    "type": "transcript",
                                    "role": "agent",
                                    "text": current_agent_turn_text(),
                                    "turn_id": f"agent-{agent_turn_id}",
                                    "finished": False,
                                }
                                await _send_voice_event(websocket, event)
                                await broadcast(event)
                        if part.inline_data and part.inline_data.data:
                            await websocket.send_bytes(part.inline_data.data)

                if server_content.turn_complete:
                    if customer_turn_open and customer_turn_text:
                        event = {
                            "type": "transcript",
                            "role": "customer",
                            "text": customer_turn_text,
                            "turn_id": f"customer-{customer_turn_id}",
                            "finished": True,
                        }
                        await _send_voice_event(websocket, event)
                        await broadcast(event)
                        customer_turn_open = False
                        customer_turn_text = ""
                    final_agent_text = current_agent_turn_text(final=True)
                    if agent_speaking and final_agent_text:
                        turn_id = f"agent-{agent_turn_id}"
                        event = {
                            "type": "transcript",
                            "role": "agent",
                            "text": final_agent_text,
                            "turn_id": turn_id,
                            "finished": True,
                        }
                        await _send_voice_event(websocket, event)
                        await broadcast(event)
                    agent_speaking = False
                    agent_turn_transcript_text = ""
                    agent_turn_model_text = ""
                    await _send_voice_event(
                        websocket, {"type": "agent_state", "value": "listening"}
                    )
                    await broadcast({"type": "status", "value": "listening"})

                if server_content.waiting_for_input and agent_speaking:
                    if customer_turn_open and customer_turn_text:
                        event = {
                            "type": "transcript",
                            "role": "customer",
                            "text": customer_turn_text,
                            "turn_id": f"customer-{customer_turn_id}",
                            "finished": True,
                        }
                        await _send_voice_event(websocket, event)
                        await broadcast(event)
                        customer_turn_open = False
                        customer_turn_text = ""
                    final_agent_text = current_agent_turn_text(final=True)
                    if final_agent_text:
                        turn_id = f"agent-{agent_turn_id}"
                        event = {
                            "type": "transcript",
                            "role": "agent",
                            "text": final_agent_text,
                            "turn_id": turn_id,
                            "finished": True,
                        }
                        await _send_voice_event(websocket, event)
                        await broadcast(event)
                    agent_speaking = False
                    agent_turn_transcript_text = ""
                    agent_turn_model_text = ""
                    await _send_voice_event(
                        websocket, {"type": "agent_state", "value": "listening"}
                    )
                    await broadcast({"type": "status", "value": "listening"})

            if message.tool_call:
                responses = []
                appointment_events: list[dict] = []
                for func_call in message.tool_call.function_calls:
                    args = dict(func_call.args)
                    event = {"type": "tool_call", "name": func_call.name, "args": args}
                    await _send_voice_event(websocket, event)
                    await broadcast(event)
                    result = tools.dispatch(func_call.name, args)
                    if func_call.name in APPOINTMENT_TOOLS and result.get("success"):
                        appointment_date = result.get("date") or result.get("new_date")
                        appointment_time = result.get("time") or result.get("new_time")
                        appointment_events.append(
                            {
                                "type": "appointments_updated",
                                "action": func_call.name,
                                "appointment": {
                                    "appointment_id": result.get("appointment_id"),
                                    "date": appointment_date,
                                    "time": appointment_time,
                                    "old_date": result.get("old_date"),
                                    "old_time": result.get("old_time"),
                                    "customer": result.get("customer"),
                                    "service": result.get("service"),
                                    "technician": result.get("technician"),
                                },
                            }
                        )
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
                    if appointment_events:
                        for appointment_event in appointment_events:
                            await _send_voice_event(websocket, appointment_event)
                            await broadcast(appointment_event)
                    else:
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
    language = _resolve_language(websocket.query_params.get("language"))
    client = genai.Client(api_key=api_key)
    config = build_live_config(voice["name"], voice["style"], language)

    try:
        async with client.aio.live.connect(model=MODEL, config=config) as session:
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "session_ready",
                        "voice": voice["name"],
                        "language": language,
                    }
                )
            )
            await _send_voice_event(
                websocket, {"type": "agent_state", "value": "speaking"}
            )
            await broadcast({"type": "status", "value": "speaking"})
            await session.send_realtime_input(text=build_opening_prompt(language))

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
    return csv_service.list_appointments()
