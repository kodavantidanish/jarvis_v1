# main.py

import config
import threading
import time
import sys
from core.assistant import JarvisAssistant
from commands.system_commands import SystemCommands
from voice.speech_to_text import SpeechToText
from voice.text_to_speech import TextToSpeech

_quit = threading.Event()


def print_banner(voice_mode=False):
    print("=" * 50)
    print("JARVIS - AI Desktop Assistant")
    print("=" * 50)
    if voice_mode:
        print("Voice Mode ACTIVE")
        print(f"  - Say '{config.WAKE_WORD}' to start a conversation")
        print("  - Interrupt JARVIS anytime by speaking")
        print("  - Say 'goodbye jarvis' to exit")
        print("  - Type anything to switch to Text Mode automatically")
    else:
        print("Text Mode ACTIVE")
        print("  - Type your commands and press Enter")
        print("  - Type 'voice mode' to enable voice")
        print("  - Type 'quit' to exit")
    print("=" * 50)


def handle_command(jarvis, sys_commands, user_input, tts=None):
    """Process a command and speak/print the response."""
    user_lower = user_input.lower().strip()

    if user_lower in ['where am i', 'current location', 'where']:
        result = sys_commands.show_current_location()
    elif user_lower in ['list', 'show contents', 'ls', 'dir']:
        result = sys_commands.list_current_folder()
    elif user_lower in ['go back', 'back', 'previous']:
        result = sys_commands.go_back()
    elif user_lower in ['go up', 'up', 'parent', 'parent folder']:
        result = sys_commands.go_up()
    elif 'rebuild index' in user_lower or 'refresh index' in user_lower:
        sys_commands.folder_finder.rebuild_index()
        result = "Index rebuilt successfully!"
    elif user_lower == 'stats':
        stats = sys_commands.folder_finder.indexer.get_stats()
        result = (f"Folders: {stats['folders']}, Apps: {stats['apps']}, "
                  f"Index age: {stats.get('index_age_hours', 0):.1f} hours")
    else:
        result = jarvis.process(user_input)

    if tts:
        tts.speak(result)
    else:
        print(f"JARVIS: {result}")

    return result


def is_exit_command(text):
    EXIT_PHRASES = {
        'goodbye jarvis', 'goodbye javis', 'goodbye',
        'exit jarvis', 'quit jarvis',
        'shut down', 'shutdown', 'turn off jarvis'
    }
    return text.lower().strip() in EXIT_PHRASES


# FIX 2: Accept voice_mode_ref so we only speak goodbye in voice mode
def shutdown(tts, jarvis, voice_mode=True):
    """Clean shutdown — only speaks goodbye if in voice mode."""
    if voice_mode:
        tts.speak("Goodbye! See you next time.", interruptible=False)
    print("JARVIS: Goodbye! See you next time.")
    _quit.set()
    time.sleep(0.3)
    sys.exit(0)


def voice_conversation_loop(jarvis, sys_commands, stt, tts, stop_event):
    """Continuous voice conversation — always listening."""
    conversation_active = False
    print(f"\n[Voice] Always listening for '{config.WAKE_WORD}'...")

    while not stop_event.is_set() and not _quit.is_set():
        try:
            raw = stt.record_with_vad()
            if not raw or stop_event.is_set() or _quit.is_set():
                continue

            text = stt.transcribe(raw).strip()
            if not text:
                continue

            text_lower = text.lower()

            if config.DEBUG_MODE:
                print(f"[Voice] Heard: '{text}'")

            if not conversation_active:
                if config.WAKE_WORD.lower() in text_lower:
                    conversation_active = True
                    command = text_lower.replace(config.WAKE_WORD.lower(), "").strip()
                    if command:
                        if is_exit_command(command):
                            shutdown(tts, jarvis, voice_mode=True)
                        print(f"You: {text}")
                        handle_command(jarvis, sys_commands, command, tts)
                    else:
                        tts.speak("Yes, I'm listening.", interruptible=False)
                continue

            if is_exit_command(text_lower):
                shutdown(tts, jarvis, voice_mode=True)

            if tts.is_speaking:
                tts.stop()
                time.sleep(0.1)

            print(f"You: {text}")
            handle_command(jarvis, sys_commands, text, tts)

            if tts.interrupt_detected:
                tts.interrupt_detected = False
                if config.DEBUG_MODE:
                    print("[Voice] Capturing follow-up after interrupt...")
                time.sleep(0.15)
                follow_raw = stt.record_with_vad()
                if follow_raw:
                    follow_text = stt.transcribe(follow_raw).strip()
                    if follow_text and len(follow_text.split()) > 1:
                        if config.DEBUG_MODE:
                            print(f"[Voice] Follow-up: '{follow_text}'")
                        if is_exit_command(follow_text.lower()):
                            shutdown(tts, jarvis, voice_mode=True)
                        print(f"You: {follow_text}")
                        handle_command(jarvis, sys_commands, follow_text, tts)

        except Exception as e:
            print(f"[Voice] Error: {e}")  # always print, not just DEBUG
            import traceback
            traceback.print_exc()          # show full crash trace
            time.sleep(0.2)


def text_input_loop(jarvis, sys_commands, tts, stop_event, voice_mode_ref, quit_flag):
    """
    Text input loop — runs alongside voice thread.

    FIX 1: We NEVER pass tts here regardless of voice_mode_ref.
    Typing = text output only. Voice thread handles all speech.
    If user types while in voice mode, we auto-switch to text mode.
    """
    while not stop_event.is_set() and not _quit.is_set():
        try:
            user_input = input("" if voice_mode_ref[0] else "You: ").strip()

            if stop_event.is_set() or _quit.is_set():
                break
            if not user_input:
                continue

            user_lower = user_input.lower()

            # FIX 2: pass current voice_mode so goodbye is silent in text mode
            if user_lower in ['quit', 'exit', 'goodbye', 'bye']:
                shutdown(tts, jarvis, voice_mode=voice_mode_ref[0])

            elif user_lower == 'voice mode' and not voice_mode_ref[0]:
                voice_mode_ref[0] = True
                stop_event.set()

            elif user_lower == 'text mode' and voice_mode_ref[0]:
                voice_mode_ref[0] = False
                stop_event.set()

            else:
                # FIX 1: Auto-switch to text mode if user types while in voice mode
                if voice_mode_ref[0]:
                    print("[JARVIS] Switching to Text Mode (keyboard detected)...")
                    if tts.is_speaking:
                        tts.stop()
                    voice_mode_ref[0] = False
                    stop_event.set()
                    # Still answer this command in text
                    handle_command(jarvis, sys_commands, user_input, tts=None)
                    break
                else:
                    # Already in text mode — just answer, no TTS
                    handle_command(jarvis, sys_commands, user_input, tts=None)

        # FIX 2: Ctrl+C respects current mode — no voice if in text mode
        except (KeyboardInterrupt, EOFError):
            shutdown(tts, jarvis, voice_mode=voice_mode_ref[0])


def main():
    jarvis = JarvisAssistant()
    sys_commands = jarvis.system_commands
    stt = SpeechToText()
    tts = TextToSpeech()

    print("=" * 50)
    print("JARVIS - AI Desktop Assistant")
    print("=" * 50)
    print("  1 - Text mode")
    print("  2 - Voice mode")
    print("=" * 50)

    while True:
        choice = input("Enter 1 or 2: ").strip()
        if choice in ['1', '2']:
            break

    voice_mode_ref = [choice == '2']
    quit_flag = [False]

    while not quit_flag[0] and not _quit.is_set():
        stop_event = threading.Event()
        print_banner(voice_mode=voice_mode_ref[0])

        if voice_mode_ref[0]:
            tts.speak("Voice mode activated. Say Jarvis to start talking.", interruptible=False)
            voice_thread = threading.Thread(
                target=voice_conversation_loop,
                args=(jarvis, sys_commands, stt, tts, stop_event),
                daemon=True
            )
            voice_thread.start()

        text_input_loop(jarvis, sys_commands, tts, stop_event, voice_mode_ref, quit_flag)
        time.sleep(0.2)


if __name__ == "__main__":
    main()