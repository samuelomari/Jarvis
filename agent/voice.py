"""Voice module - wake word detection, speech-to-text (STT), and text-to-speech (TTS)."""

import queue
import shutil
import subprocess
import threading
import time
from typing import Callable, Optional


# ── TTS Engine ─────────────────────────────────────────────────────────────────

class TTSEngine:
    """Text-to-speech engine with multiple backend support."""

    def __init__(self):
        self._pyttsx3_engine = None
        self._lock = threading.Lock()
        self._backend = self._detect_backend()

    def _detect_backend(self) -> str:
        """Detect the best available TTS backend."""
        if shutil.which("espeak-ng"):
            return "espeak-ng"
        if shutil.which("espeak"):
            return "espeak"
        if shutil.which("spd-say"):
            return "spd-say"
        if shutil.which("say"):
            return "say"  # macOS
        try:
            import pyttsx3
            return "pyttsx3"
        except ImportError:
            pass
        return "none"

    def speak(self, text: str, rate: int = 175, voice: Optional[str] = None) -> bool:
        """Speak text using the best available backend. Returns True on success."""
        if not text or not text.strip():
            return False

        clean_text = text.strip()

        with self._lock:
            if self._backend == "espeak-ng":
                cmd = ["espeak-ng", "-s", str(rate), clean_text]
                if voice:
                    cmd = ["espeak-ng", "-v", voice, "-s", str(rate), clean_text]
                try:
                    subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
                    return True
                except Exception:
                    pass

            if self._backend in ("espeak", "espeak-ng"):
                cmd = ["espeak", "-s", str(rate), clean_text]
                try:
                    subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
                    return True
                except Exception:
                    pass

            if self._backend == "spd-say":
                try:
                    subprocess.run(["spd-say", clean_text], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
                    return True
                except Exception:
                    pass

            if self._backend == "say":
                try:
                    subprocess.run(["say", clean_text], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
                    return True
                except Exception:
                    pass

            if self._backend == "pyttsx3":
                try:
                    import pyttsx3
                    if self._pyttsx3_engine is None:
                        self._pyttsx3_engine = pyttsx3.init()
                    self._pyttsx3_engine.setProperty("rate", rate)
                    self._pyttsx3_engine.say(clean_text)
                    self._pyttsx3_engine.runAndWait()
                    return True
                except Exception:
                    pass

        return False

    def speak_async(self, text: str, rate: int = 175) -> threading.Thread:
        """Speak text in a background thread."""
        t = threading.Thread(target=self.speak, args=(text, rate), daemon=True)
        t.start()
        return t

    @property
    def available(self) -> bool:
        return self._backend != "none"

    @property
    def backend_name(self) -> str:
        return self._backend


# ── STT Engine ─────────────────────────────────────────────────────────────────

class STTEngine:
    """Speech-to-text engine using SpeechRecognition library."""

    def __init__(self):
        self._available = False
        try:
            import speech_recognition as sr
            self._sr = sr
            self._recognizer = sr.Recognizer()
            self._recognizer.energy_threshold = 300
            self._recognizer.dynamic_energy_threshold = True
            self._recognizer.pause_threshold = 0.8
            self._available = True
        except ImportError:
            self._sr = None
            self._recognizer = None

    @property
    def available(self) -> bool:
        return self._available

    def listen_once(self, timeout: int = 5, phrase_limit: int = 15) -> Optional[str]:
        """Listen for a single utterance and return transcribed text."""
        if not self._available:
            return None

        try:
            with self._sr.Microphone() as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.3)
                audio = self._recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)

            # Try Google STT first (free, online)
            try:
                text = self._recognizer.recognize_google(audio)
                return text.strip()
            except Exception:
                pass

            # Fallback: Sphinx (offline, less accurate)
            try:
                text = self._recognizer.recognize_sphinx(audio)
                return text.strip()
            except Exception:
                pass

        except self._sr.WaitTimeoutError:
            return None
        except Exception:
            return None

        return None

    def listen_continuous(
        self,
        callback: Callable[[str], None],
        stop_event: threading.Event,
        timeout: int = 5,
    ) -> None:
        """Continuously listen and call callback with each transcription."""
        if not self._available:
            return

        while not stop_event.is_set():
            text = self.listen_once(timeout=timeout)
            if text:
                callback(text)


# ── Wake Word Detector ─────────────────────────────────────────────────────────

class WakeWordDetector:
    """Simple wake word detector using keyword matching on STT output."""

    DEFAULT_WAKE_WORDS = ["hey jarvis", "jarvis", "ok jarvis", "hello jarvis"]

    def __init__(self, wake_words: Optional[list] = None, stt: Optional[STTEngine] = None):
        self.wake_words = [w.lower() for w in (wake_words or self.DEFAULT_WAKE_WORDS)]
        self.stt = stt or STTEngine()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def _contains_wake_word(self, text: str) -> bool:
        text_lower = text.lower()
        return any(ww in text_lower for ww in self.wake_words)

    def _strip_wake_word(self, text: str) -> str:
        """Remove the wake word from the beginning of the text."""
        text_lower = text.lower()
        for ww in self.wake_words:
            if text_lower.startswith(ww):
                return text[len(ww):].strip(" ,.")
        return text

    def listen_for_wake_word(self, timeout_per_attempt: int = 4) -> Optional[str]:
        """
        Block until a wake word is detected.
        Returns the command text after the wake word, or None if STT unavailable.
        """
        if not self.stt.available:
            return None

        while not self._stop_event.is_set():
            text = self.stt.listen_once(timeout=timeout_per_attempt)
            if text and self._contains_wake_word(text):
                command = self._strip_wake_word(text)
                return command if command else ""

        return None

    def start_background(self, on_wake: Callable[[str], None]) -> None:
        """Start wake word detection in a background thread."""
        self._stop_event.clear()

        def _loop():
            while not self._stop_event.is_set():
                command = self.listen_for_wake_word()
                if command is not None:
                    on_wake(command)

        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop background wake word detection."""
        self._stop_event.set()


# ── Voice Session ──────────────────────────────────────────────────────────────

class VoiceSession:
    """Manages a complete voice interaction session."""

    def __init__(
        self,
        tts: Optional[TTSEngine] = None,
        stt: Optional[STTEngine] = None,
        wake_word_detector: Optional[WakeWordDetector] = None,
    ):
        self.tts = tts or TTSEngine()
        self.stt = stt or STTEngine()
        self.wake_detector = wake_word_detector or WakeWordDetector(stt=self.stt)

    def greet(self) -> None:
        """Speak a startup greeting."""
        if self.tts.available:
            self.tts.speak("Jarvis voice interface online. Say 'Hey Jarvis' to begin.")

    def speak_response(self, text: str) -> None:
        """Speak Jarvis's response, stripping markdown."""
        clean = _strip_markdown(text)
        if self.tts.available and clean:
            self.tts.speak(clean)

    def listen_command(self, prompt_text: Optional[str] = None) -> Optional[str]:
        """Listen for a voice command and return transcribed text."""
        if prompt_text and self.tts.available:
            self.tts.speak(prompt_text)
        return self.stt.listen_once()

    @property
    def voice_available(self) -> bool:
        return self.tts.available

    @property
    def stt_available(self) -> bool:
        return self.stt.available


def _strip_markdown(text: str) -> str:
    """Remove common markdown syntax for cleaner TTS output."""
    import re
    text = re.sub(r"#{1,6}\s*", "", text)
    text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)
    text = re.sub(r"`{1,3}[^`]*`{1,3}", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{2,}", ". ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ── Singletons ─────────────────────────────────────────────────────────────────

_tts_engine: Optional[TTSEngine] = None
_stt_engine: Optional[STTEngine] = None
_voice_session: Optional[VoiceSession] = None


def get_tts() -> TTSEngine:
    global _tts_engine
    if _tts_engine is None:
        _tts_engine = TTSEngine()
    return _tts_engine


def get_stt() -> STTEngine:
    global _stt_engine
    if _stt_engine is None:
        _stt_engine = STTEngine()
    return _stt_engine


def get_voice_session() -> VoiceSession:
    global _voice_session
    if _voice_session is None:
        _voice_session = VoiceSession(tts=get_tts(), stt=get_stt())
    return _voice_session
