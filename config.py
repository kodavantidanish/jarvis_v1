import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# API Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
VOICE_NAME = "en-US-GuyNeural"   # JARVIS-like male voice (try "en-GB-RyanNeural" for British)
WAKE_WORD = "jarvis"              # say "jarvis" or "hey jarvis"
RECORD_SECONDS = 6                # max recording duration for commands
AUDIO_SAMPLE_RATE = 16000         # required by Whisper

# Model
GROQ_MODEL = "llama-3.3-70b-versatile"

# Common paths - Auto-detects your username
COMMON_PATHS = {
    # User folders
    "downloads": os.path.expanduser("~\\Downloads"),
    "documents": os.path.expanduser("~\\Documents"),
    "desktop": os.path.expanduser("~\\Desktop"),
    "pictures": os.path.expanduser("~\\Pictures"),
    "videos": os.path.expanduser("~\\Videos"),
    "music": os.path.expanduser("~\\Music"),

    # ✅ FIX: Added all common drive letter variations
    # C Drive
    "c_drive": "C:\\",
    "c drive": "C:\\",
    "c:": "C:\\",
    "c": "C:\\",

    # D Drive
    "d_drive": "D:\\",
    "d drive": "D:\\",
    "d:": "D:\\",
    "d": "D:\\",

    # E Drive
    "e_drive": "E:\\",
    "e drive": "E:\\",
    "e:": "E:\\",
    "e": "E:\\",

    # F Drive (in case it exists)
    "f_drive": "F:\\",
    "f drive": "F:\\",
    "f:": "F:\\",
    "f": "F:\\",
}

DEBUG_MODE = True