# AirPro HVAC Voice Agent

A real-time AI phone agent powered by the **Gemini Live API** that handles inbound customer calls for an HVAC company — booking, cancellations, rescheduling, order status checks, account verification, and basic troubleshooting.

Customers speak naturally, the agent responds with voice, and every appointment change is written to a CSV file the HVAC team can open at any time.

---

## How it works

```
Customer speaks → Gemini Live API → Calls a tool (book/cancel/reschedule) → Speaks result back
                  (native audio)         ↓
                                  appointments.csv updated in real time
```

- **No separate STT or TTS** — Gemini handles voice in and voice out natively
- **Function calling** — agent can look up and update real data mid-conversation
- **CSV tracking** — every appointment action is logged automatically

---

## Setup

### 1. Install PortAudio (required by PyAudio)

**macOS**
```bash
brew install portaudio
```

**Ubuntu / Debian**
```bash
sudo apt-get install portaudio19-dev
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install backend dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cd backend
cp .env.example .env
```

Edit `.env`:

```
GEMINI_API_KEY=your_api_key_here      # https://aistudio.google.com/apikey
APPOINTMENTS_CSV=appointments.csv     # path to the CSV file (auto-created)
```

### 5. Run the backend API

```bash
cd backend
python main.py
```

### 6. Run the frontend

```bash
cd frontend
npm run dev
```

Open `http://localhost:3000`, then start the browser-based agent from the UI.

### 7. Optional: run the terminal microphone agent

```bash
cd backend
python terminal_agent.py
```

---

## What the agent can do

| Option | What happens |
|---|---|
| **Book appointment / Emergency** | Verifies account → shows available slots → books → writes to CSV |
| **Cancel appointment** | Verifies account → shows appointments → cancels → updates CSV |
| **Reschedule appointment** | Verifies account → shows slots → moves appointment → updates CSV |
| **Order status** | Looks up a service or parts order by ID |
| **Troubleshooting** | Walks the customer through common HVAC fixes over the phone |

---

## Test data

Use these with the mock data in `backend/tools.py`:

| What | Value |
|---|---|
| Account number | `ACC-1001` |
| Last name | `Garcia` |
| Appointment ID | `APT-4001` |
| Order ID | `ORD-8001` |

---

## Project structure

```
workshop4/
├── backend/
│   ├── main.py              # FastAPI backend server
│   ├── terminal_agent.py    # Optional local microphone agent
│   ├── api.py               # FastAPI + browser voice websocket
│   ├── tools.py             # HVAC business logic + tool dispatcher
│   ├── voices.py            # Voice options and speaking personalities
│   ├── services/
│   │   └── csv_service.py   # Reads and writes appointments.csv
│   ├── requirements.txt
│   └── .env.example
├── frontend/
└── .gitignore
```

**To connect a real backend:** replace the mock data and functions in `backend/tools.py` with calls to your actual CRM, scheduling system, or database. The agent logic in `backend/main.py` and `backend/api.py` does not need to change.

---

## Available voices

| # | Voice | Character |
|---|---|---|
| 1 | Aoede | Warm, conversational (default) |
| 2 | Puck | Upbeat, energetic |
| 3 | Charon | Deep, authoritative |
| 4 | Kore | Clear, neutral |
| 5 | Fenrir | Expressive |
| 6 | Leda | Friendly |
| 7 | Orus | Confident |
| 8 | Zephyr | Calm |

---

## Model

| Property | Value |
|---|---|
| Model | `gemini-2.5-flash-native-audio-preview-12-2025` |
| Input | Live microphone audio (16 kHz PCM) |
| Output | Native audio (24 kHz PCM) |
| Function calling | Supported |
| Thinking | Disabled (not needed for real-time voice) |
