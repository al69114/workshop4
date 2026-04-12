# KTP Voice Agent Workshop

A real-time voice agent powered by the **Gemini Live API** that answers questions about [Kappa Theta Pi (KTP)](https://ktpgeorgia.com) — UGA's professional technology fraternity.

Speak naturally and the agent responds with voice — no buttons, no typing.

---

## How it works

```
Your Microphone → Gemini Live API → Speaker
     (16 kHz PCM)   gemini-2.5-flash-native-audio   (24 kHz PCM)
```

The Gemini Live API handles everything natively:
- **Speech understanding** — listens to your voice in real time
- **AI reasoning** — answers questions about KTP
- **Text-to-speech** — responds with a natural voice (no separate TTS needed)

---

## Setup

### 1. Install system dependency (PortAudio)

**macOS**
```bash
brew install portaudio
```

**Ubuntu / Debian**
```bash
sudo apt-get install portaudio19-dev
```

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Add your Gemini API key

```bash
cp .env.example .env
```

Edit `.env` and paste your key (get one free at [aistudio.google.com/apikey](https://aistudio.google.com/apikey)):

```
GEMINI_API_KEY=your_api_key_here
```

### 4. Run the agent

```bash
python main.py
```

---

## Try asking...

- *"What is KTP?"*
- *"When is rush?"*
- *"What are the three pillars of KTP?"*
- *"What companies do KTP alumni work at?"*
- *"What happens at Shark Tank night?"*
- *"How do I join KTP?"*

Press **Ctrl+C** to quit.

---

## Project structure

```
workshop4/
├── main.py          # Voice agent — start here
├── requirements.txt
├── .env.example     # Copy to .env and add your API key
└── README.md
```

## Model used

| Property | Value |
|---|---|
| Model | `gemini-2.5-flash-native-audio-preview-12-2025` |
| Input | Live audio (microphone) |
| Output | Native audio (speaker) |
| Voice | Aoede |
