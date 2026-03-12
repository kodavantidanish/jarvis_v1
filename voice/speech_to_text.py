# voice/speech_to_text.py

import sounddevice as sd
import numpy as np
import io
import wave
import collections
import config
from groq import Groq

class SpeechToText:
    def __init__(self):
        self.client = Groq(api_key=config.GROQ_API_KEY)
        self.sample_rate = config.AUDIO_SAMPLE_RATE

        self.frame_duration_ms = 30
        self.frame_size = int(self.sample_rate * self.frame_duration_ms / 1000)

        self.silence_timeout_ms = 2000
        self.silence_frames = self.silence_timeout_ms // self.frame_duration_ms

        self.min_speech_frames = 2
        self.max_duration_seconds = 15

        # CHANGED: Calibrate once at startup — no more per-listen ambient sampling
        # that was eating the first 0.5s of every utterance
        self.dynamic_threshold = self._calibrate_noise()

    def _calibrate_noise(self):
        """
        CHANGED: Called once at init — measures ambient noise and sets threshold.
        This runs before JARVIS prints "ready" so it doesn't interfere with usage.
        """
        print("[STT] Calibrating mic noise floor...")
        ambient_frames = int(800 / self.frame_duration_ms)  # 0.8s sample
        levels = []

        try:
            with sd.InputStream(samplerate=self.sample_rate, channels=1,
                                dtype='int16', blocksize=self.frame_size) as stream:
                for _ in range(ambient_frames):
                    frame, _ = stream.read(self.frame_size)
                    audio = np.frombuffer(frame.tobytes(), dtype=np.int16).astype(np.float32)
                    levels.append(np.sqrt(np.mean(audio ** 2)))

            ambient_rms = np.mean(levels)
            # CHANGED: threshold = ambient * 3.0 for noisy rooms, minimum 400
            threshold = max(ambient_rms * 2.5, 350)
            print(f"[STT] Noise floor: {ambient_rms:.0f} RMS → threshold set to {threshold:.0f}")
            return threshold

        except Exception as e:
            print(f"[STT] Calibration failed, using default threshold. Error: {e}")
            return 600  # safe fallback

    def recalibrate(self):
        """CHANGED: Call this if environment changes (e.g. music turned on)."""
        self.dynamic_threshold = self._calibrate_noise()

    def _is_speech(self, frame_bytes):
        """Energy-based VAD using calibrated threshold."""
        audio = np.frombuffer(frame_bytes, dtype=np.int16).astype(np.float32)
        rms = np.sqrt(np.mean(audio ** 2))
        return rms > self.dynamic_threshold

    def record_with_vad(self):
        """
        CHANGED: No more per-call ambient sampling — uses pre-calibrated threshold.
        Starts listening immediately so first word is never missed.
        """
        max_frames = int(self.max_duration_seconds * 1000 / self.frame_duration_ms)

        # Ring buffer — captures ~600ms before speech trigger so start isn't clipped
        ring_buffer = collections.deque(maxlen=20)

        recorded_frames = []
        speech_started = False
        silent_frame_count = 0
        speech_frame_count = 0

        with sd.InputStream(samplerate=self.sample_rate, channels=1,
                            dtype='int16', blocksize=self.frame_size) as stream:
            for _ in range(max_frames):
                frame, _ = stream.read(self.frame_size)
                frame_bytes = frame.tobytes()
                is_speech = self._is_speech(frame_bytes)

                if not speech_started:
                    ring_buffer.append(frame_bytes)
                    if is_speech:
                        speech_frame_count += 1
                        if speech_frame_count >= self.min_speech_frames:
                            speech_started = True
                            recorded_frames.extend(ring_buffer)
                            ring_buffer.clear()
                            if config.DEBUG_MODE:
                                print("[STT] Speech detected, recording...")
                    else:
                        speech_frame_count = 0

                else:
                    recorded_frames.append(frame_bytes)
                    if not is_speech:
                        silent_frame_count += 1
                        if silent_frame_count >= self.silence_frames:
                            if config.DEBUG_MODE:
                                print("[STT] Silence detected, stopping.")
                            break
                    else:
                        silent_frame_count = max(0, silent_frame_count - 3)

        if not recorded_frames:
            return None

        return b"".join(recorded_frames)

    def audio_bytes_to_wav(self, raw_bytes):
        """Convert raw PCM bytes to in-memory WAV for Groq API."""
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(raw_bytes)
        wav_buffer.seek(0)
        return wav_buffer

    def transcribe(self, raw_bytes):
        """Send audio to Groq Whisper and return transcribed text."""
        if not raw_bytes:
            return ""

        try:
            wav_file = self.audio_bytes_to_wav(raw_bytes)

            response = self.client.audio.transcriptions.create(
                model="whisper-large-v3-turbo",
                file=("audio.wav", wav_file, "audio/wav"),
                language="en",
                prompt="JARVIS desktop assistant. User speaks commands like: open chrome, open downloads, hey jarvis."
            )

            text = response.text.strip()

            hallucinations = {
                 "thanks for watching", "you",
                 "thank you for watching", ".", "", " ",
                "you."
            }
            if text.lower() in hallucinations:
                if config.DEBUG_MODE:
                    print(f"[STT] Filtered hallucination: '{text}'")
                return ""

            if config.DEBUG_MODE:
                print(f"[STT] Transcribed: '{text}'")

            return text

        except Exception as e:
            if config.DEBUG_MODE:
                print(f"[STT] Transcription error: {e}")
            return ""

    def record_with_vad_timeout(self, timeout=2.5):
        """Shorter VAD for wake word detection."""
        original = self.max_duration_seconds
        self.max_duration_seconds = timeout
        result = self.record_with_vad()
        self.max_duration_seconds = original
        return result

    def listen(self, duration=None):
        """Full pipeline: VAD record → transcribe → return text."""
        raw_bytes = self.record_with_vad()
        return self.transcribe(raw_bytes)