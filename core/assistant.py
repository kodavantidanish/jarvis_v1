# core/assistant.py

import atexit
import config
from core.intent_parser import IntentParser
from commands.system_commands import SystemCommands
from memory.storage import Storage
from utils.logger import get_logger

logger = get_logger("jarvis")


class JarvisAssistant:
    def __init__(self):
        print("Initializing JARVIS...")
        self.intent_parser = IntentParser()
        self.system_commands = SystemCommands()
        self.storage = Storage()

        # Load last session so JARVIS remembers previous convo
        self.conversation_history = self.storage.load_last_session()

        # Auto-save on exit (Ctrl+C, sys.exit, crash)
        atexit.register(self._save_session)

        logger.info("JARVIS initialized.")
        print("JARVIS ready!\n")

    def _save_session(self):
        self.storage.save_session(self.conversation_history)
        logger.info(f"Session saved ({len(self.conversation_history)} messages).")

    def _add_to_history(self, role, content):
        self.conversation_history.append({"role": role, "content": content})
        if len(self.conversation_history) > 40:
            self.conversation_history = self.conversation_history[-40:]

    def process(self, user_input):
        intent = self.intent_parser.parse(user_input)
        action = intent.get("action")

        if config.DEBUG_MODE:
            print(f"Intent: {intent}")

        if action == "open_folder":
            result = self.system_commands.open_folder(
                intent.get("target"),
                intent.get("path")
            )
            if "couldn't find" in result.lower():
                if config.DEBUG_MODE:
                    print("Folder not found, trying as file...")
                result = self.system_commands.open_file_by_name(
                    intent.get("target"),
                    file_type=None
                )
            self._add_to_history("user", user_input)
            self._add_to_history("assistant", result)
            logger.info(f"open_folder | input='{user_input}' | result='{result}'")
            return result

        elif action == "open_file":
            result = self.system_commands.open_file_by_name(
                intent.get("target"),
                file_type=intent.get("path")
            )
            if "couldn't find" in result.lower():
                if config.DEBUG_MODE:
                    print("File not found, trying as folder...")
                result = self.system_commands.open_folder(
                    intent.get("target"),
                    intent.get("path")
                )
            self._add_to_history("user", user_input)
            self._add_to_history("assistant", result)
            logger.info(f"open_file | input='{user_input}' | result='{result}'")
            return result

        elif action == "open_app":
            result = self.system_commands.open_app(intent.get("target"))
            self._add_to_history("user", user_input)
            self._add_to_history("assistant", result)
            logger.info(f"open_app | input='{user_input}' | result='{result}'")
            return result

        else:
            response = self.intent_parser.chat(user_input, self.conversation_history)
            self._add_to_history("user", user_input)
            self._add_to_history("assistant", response)
            logger.info(f"chat | input='{user_input}'")
            return response