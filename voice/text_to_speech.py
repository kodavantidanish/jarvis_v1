# voice/text_to_speech.py

import asyncio
import edge_tts
import sounddevice as sd
import soundfile as sf
import numpy as np
import threading
import io
import time
import config

class TextToSpeech:
    def __init__(self):
        self.voice = config.VOICE_NAME
        self.is_speaking = False
        self.interrupt_detected = False
        # CHANGED: track when speech actually started so we can ignore
        # late-firing monitor after natural end of speech
        self._speech_start_time = 0

    async def _synthesize(self, text):
        communicate = edge_tts.Communicate(text, self.voice)
        audio_buffer = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_buffer.write(chunk["data"])
        audio_buffer.seek(0)
        return audio_buffer

    def _stream_text(self, text, total_duration):
        words = text.split()
        if not words:
            return
        delay_per_word = total_duration / len(words)
        print("JARVIS: ", end="", flush=True)
        for word in words:
            if not self.is_speaking:
                break
            print(word + " ", end="", flush=True)
            time.sleep(delay_per_word)
        print()

    def _interrupt_monitor(self, energy_threshold=1500):
        """
        Monitors mic during TTS playback.
        CHANGED: Only sets interrupt_detected if speech is still actively playing
        AND enough time has passed since start (avoids triggering on TTS echo).
        """
        frame_size = int(config.AUDIO_SAMPLE_RATE * 0.03)
        # CHANGED: Ignore first 0.5s of playback to avoid TTS echo triggering interrupt
        startup_ignore_frames = int(800 / 30)

        try:
            with sd.InputStream(samplerate=config.AUDIO_SAMPLE_RATE,
                                channels=1, dtype='int16',
                                blocksize=frame_size) as stream:
                consecutive_speech = 0
                frame_count = 0
                while self.is_speaking:
                    frame, _ = stream.read(frame_size)
                    frame_count += 1

                    # CHANGED: Skip first 0.5s to avoid false trigger from TTS echo
                    if frame_count < startup_ignore_frames:
                        continue

                    audio = np.frombuffer(frame.tobytes(), dtype=np.int16).astype(np.float32)
                    rms = np.sqrt(np.mean(audio ** 2))

                    if rms > energy_threshold:
                        consecutive_speech += 1
                        if consecutive_speech >= 4:
                            if config.DEBUG_MODE:
                                print(f"\n[TTS] Interrupt detected (RMS: {rms:.0f})")
                            # CHANGED: Only interrupt if still speaking (not natural end)
                            if self.is_speaking:
                                self.interrupt_detected = True
                                self.stop()
                            break
                    else:
                        consecutive_speech = 0
        except Exception as e:
            if config.DEBUG_MODE:
                print(f"[TTS] Interrupt monitor error: {e}")

    def speak(self, text, interruptible=True):
        if not text or not text.strip():
            return

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            audio_buffer = loop.run_until_complete(self._synthesize(text))
            loop.close()

            data, samplerate = sf.read(audio_buffer, dtype='float32')
            duration = len(data) / samplerate

            self.is_speaking = True
            self.interrupt_detected = False
            self._speech_start_time = time.time()

            text_thread = threading.Thread(
                target=self._stream_text,
                args=(text, duration),
                daemon=True
            )
            text_thread.start()

            if interruptible:
                monitor_thread = threading.Thread(
                    target=self._interrupt_monitor,
                    daemon=True
                )
                monitor_thread.start()

            sd.play(data, samplerate)
            sd.wait()

            # CHANGED: Mark speech as done BEFORE sleeping
            self.is_speaking = False
            # CHANGED: Brief pause so monitor thread sees is_speaking=False and stops
            time.sleep(0.1)
            text_thread.join(timeout=1)

        except Exception as e:
            self.is_speaking = False
            if config.DEBUG_MODE:
                print(f"[TTS] Error: {e}")
            print(f"JARVIS: {text}")

    def stop(self):
        
        self.is_speaking = False
        sd.stop()