# JARVIS - AI Desktop Assistant

A voice-controlled AI desktop assistant for Windows, inspired by Iron Man's JARVIS. Built with Python, Groq API, and Edge-TTS.

## Features
- 🎙️ Wake word activation ("Jarvis")
- 🗣️ Voice & Text mode with seamless switching
- 🧠 Multi-turn conversation memory across sessions
- 📂 Smart app, file & folder launching
- ⚡ Interrupt JARVIS mid-speech and it listens immediately
- 🔍 Indexed folder/app search with JSON caching

## Tech Stack
- **LLM** — Groq API (llama-3.3-70b-versatile)
- **STT** — Groq Whisper (whisper-large-v3-turbo)
- **TTS** — Edge-TTS (Microsoft Neural Voices)
- **VAD** — Custom energy-based Voice Activity Detection

## Setup
1. Clone the repo
2. Create a virtual environment and install dependencies
```
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements.txt
```
3. Copy `.env.example` to `.env` and add your Groq API key
4. Run
```
   python main.py
```

## Usage
- Say **"Jarvis"** to wake it up
- Ask it to open apps, files, folders
- Have a conversation — it remembers context
- Type anything to switch to text mode
- Press `Ctrl+C` to exit
