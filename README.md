# AirPro HVAC Voice Agent

A real-time HVAC phone agent built with the Gemini Live API, a Python backend, and a Next.js frontend.

The app supports:
- browser-based voice conversations with the agent
- a live dashboard for transcripts, tool calls, and appointment updates
- a calendar view that updates when appointments are booked, cancelled, or rescheduled
- an optional terminal microphone agent for local testing

## Architecture

```text
Browser mic / terminal mic
        ↓
Gemini Live API
        ↓
Python backend tools
        ↓
appointments.csv
        ↓
Next.js dashboard + calendar
```

Notes:
- Gemini handles the actual audio input and audio output.
- The backend code handles tool calls, transcript cleanup, websocket events, and CSV persistence.
- The frontend renders the live conversation, appointment ledger, and calendar updates.

## Repo Layout

```text
workshop4/
├── backend/
│   ├── main.py                 # Starts the backend API server on port 8000
│   ├── api.py                  # FastAPI app + /ws dashboard socket + /voice call socket
│   ├── agent_config.py         # Gemini model, prompt, tool schema, live config
│   ├── terminal_agent.py       # Optional local mic + speaker agent
│   ├── tools.py                # Mock HVAC business logic and tool dispatcher
│   ├── voices.py               # Voice options
│   ├── appointments.csv        # CSV-backed appointment store
│   ├── requirements.txt
│   └── services/
│       └── csv_service.py      # CSV reads, writes, and seed data
├── frontend/
│   ├── app/page.tsx            # Main dashboard + browser voice agent
│   ├── app/calendar/page.tsx   # Live calendar view
│   ├── app/layout.tsx          # App shell + nav
│   ├── components/site-nav.tsx
│   └── lib/backend.ts          # Frontend API and websocket types/helpers
└── README.md
```

## Requirements

### Backend

- Python 3.10+ recommended
- Gemini API key
- PortAudio if you want to use the optional terminal microphone agent

### Frontend

- Node.js 18+ recommended

## Setup

### 1. Backend environment

From the repo root:

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create `backend/.env` and add:

```env
GEMINI_API_KEY=your_api_key_here
APPOINTMENTS_CSV=appointments.csv
```

`APPOINTMENTS_CSV` is resolved relative to `backend/` unless you provide an absolute path.

### 2. Frontend environment

```bash
cd frontend
npm install
```

If needed, set:

```env
NEXT_PUBLIC_API_BASE=http://localhost:8000
```

The frontend defaults to `http://localhost:8000`, so this is optional for local development.

## Running The App

### Backend API

```bash
cd backend
source venv/bin/activate
python main.py
```

This starts the FastAPI backend on `http://localhost:8000`.

### Frontend dashboard

```bash
cd frontend
npm run dev
```

Open:
- `http://localhost:3000` for the main dashboard
- `http://localhost:3000/calendar` for the calendar page

### Optional terminal agent

If you want to talk to the agent directly from your computer microphone and speakers:

```bash
cd backend
source venv/bin/activate
python terminal_agent.py
```

For the terminal agent only, install PortAudio first.

macOS:
```bash
brew install portaudio
```

Ubuntu / Debian:
```bash
sudo apt-get install portaudio19-dev
```

## Frontend

The frontend has two main screens.

### Dashboard

`/`

Features:
- `Interact With Agent` button for browser voice calls
- live conversation panel
- agent status badges
- tool call stream
- appointment ledger that refreshes after tool actions

### Calendar

`/calendar`

Features:
- month view of appointments
- selected-day appointment list
- occupied vs available technicians
- automatic refresh when bookings, cancellations, or reschedules happen
- auto-focus to the booked day after a successful Option 1 booking

## Backend

The backend exposes:

- `GET /appointments`
- `WS /ws` for dashboard events
- `WS /voice` for the browser voice session

The backend is responsible for:
- connecting to Gemini Live
- forwarding browser PCM audio to Gemini
- returning agent audio back to the browser
- handling tool calls
- updating `appointments.csv`
- broadcasting live transcript, tool-call, status, and appointment-update events

## Voice / Transcription Flow

Transcription is a mix of API output and app code:

- Gemini Live performs the actual input and output audio transcription
- the backend enables that in `backend/agent_config.py`
- the backend merges and normalizes transcript chunks in `backend/api.py`
- the frontend renders those transcript events in the live conversation panel

So:
- speech-to-text itself comes from the Gemini API
- transcript cleanup and display behavior come from your code

## Current Call Flows

### Option 1: Schedule or emergency

- Ask whether it is an emergency or a standard appointment
- For standard scheduling, read only the next few openings in a short format
- Ask if the caller wants the options repeated
- Ask for the caller's full name after they choose a slot
- Book the appointment and update the calendar/dashboard

### Option 2: Cancel appointment

- Ask for the caller's full name
- Ask for the appointment ID
- Cancel only if the provided name matches the appointment on file

### Option 3: Reschedule appointment

- Uses account verification
- Looks up current appointments
- Reads new openings
- Reschedules and updates the calendar/dashboard

### Option 4: Order status

- Ask for an order ID such as `ORD-8001`

### Option 5: Troubleshooting

- No tool call required

## Mock Test Data

Useful values in the mock backend:

| Type | Value |
|---|---|
| Account number | `ACC-1001` |
| Last name | `Garcia` |
| Appointment ID | `APT-4001` |
| Order ID | `ORD-8001` |

## Model

Current live audio model:

- `gemini-3.1-flash-live-preview`

Notes:
- the backend uses Gemini Live audio input/output
- browser opening prompts are sent with `send_realtime_input(...)`
- the voice socket is run through the backend, not directly from the frontend to Gemini

## Development Notes

- Appointment data is stored in `backend/appointments.csv`
- Seed demo data is created when the CSV is empty
- The calendar and dashboard both refresh from backend websocket events
- To replace mock business logic with real systems, start with `backend/tools.py`
