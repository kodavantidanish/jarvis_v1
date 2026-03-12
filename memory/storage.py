# memory/storage.py

import json
import os
from datetime import datetime

MEMORY_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'memory.json')


class Storage:
    def __init__(self, path=MEMORY_PATH):
        self.path = os.path.abspath(path)
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        if not os.path.exists(self.path):
            self._write({"sessions": []})

    def _read(self):
        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {"sessions": []}

    def _write(self, data):
        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def save_session(self, conversation_history):
        """Save the current session, keeping only the last 1 session."""
        if not conversation_history:
            return
        data = {
            "sessions": [
                {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "history": conversation_history
                }
            ]
        }
        self._write(data)

    def load_last_session(self):
        """Load the last session's conversation history."""
        data = self._read()
        sessions = data.get("sessions", [])
        if sessions:
            last = sessions[-1]
            print(f"[Memory] Loaded last session from {last['timestamp']} "
                  f"({len(last['history'])} messages)")
            return last["history"]
        return []