"""Fyz's text-to-speech pipeline (Brain v3.2: Piper Urdu neural voice).

Architecture (unchanged from Brain v3.1's fix for "only the first reply
gets spoken"): one persistent background worker thread owns a queue, so
replies are never dropped and callers never block. What changed is the
synthesis backend - Piper (a local neural TTS model) replaces pyttsx3 as
the primary voice, and the Roman Urdu reply is converted to Urdu script
(voice/text_converter.py) before synthesis so it's pronounced as real Urdu
instead of an English voice sounding out Roman letters.

    speak(text, on_done)
        -> enqueue (returns immediately, never blocks the caller)
        -> persistent worker thread
        -> Roman Urdu -> Urdu script (voice/text_converter.py)
        -> Piper synthesis (in-memory float audio, no temp files)
        -> sounddevice playback, blocked on until genuinely finished
        -> on_done() fires only after playback actually completes

Piper's ONNX voice model is stateless, so - unlike the old pyttsx3 engine,
which was a COM object that broke on reuse - it's loaded ONCE and kept
resident rather than reloaded per utterance (reloading took ~2s, which
would otherwise mean ~2s of dead air before every single reply).
"""

import queue
import threading
import wave
from typing import Callable, Optional

import numpy as np
import sounddevice as sd

from core.config import (
    PIPER_CONFIG_PATH,
    PIPER_ENABLED,
    PIPER_VOICE_PATH,
    TTS_ENABLED,
    TTS_FALLBACK_TO_PYTTSX3,
)
from core.logging_setup import get_logger
from voice.text_converter import prepare_for_piper, strip_emoji

_logger = get_logger(__name__)

_piper_voice = None
_piper_load_failed = False


def _load_piper_voice():
    from piper import PiperVoice

    return PiperVoice.load(PIPER_VOICE_PATH, PIPER_CONFIG_PATH)


def _get_piper_voice():
    """Lazy singleton - the ~2s model load happens on first use (on the
    worker thread, not at import time, so importing this module or
    starting the GUI never blocks on it), then the same voice object is
    reused for every subsequent utterance."""
    global _piper_voice, _piper_load_failed
    if _piper_voice is None and not _piper_load_failed:
        try:
            _piper_voice = _load_piper_voice()
        except Exception:
            _piper_load_failed = True
            _logger.exception("Failed to load Piper voice (path=%r, config=%r)", PIPER_VOICE_PATH, PIPER_CONFIG_PATH)
    return _piper_voice


def _synthesize(voice, text: str):
    """Returns (audio: float32 numpy array, sample_rate) or (None, None)
    if synthesis produced no audio chunks."""
    chunks = []
    sample_rate = None
    for chunk in voice.synthesize(text):
        chunks.append(np.asarray(chunk.audio_float_array, dtype=np.float32))
        sample_rate = chunk.sample_rate
    if not chunks:
        return None, None
    return np.concatenate(chunks), sample_rate


def _play_audio(audio: np.ndarray, sample_rate: int) -> None:
    """Blocks until playback genuinely finishes. This must never return
    early - the caller's on_done fires right after, and always-listening
    mode resumes the mic on that signal, so an early return here would mean
    the mic re-arms while Fyz is still audibly talking."""
    sd.play(audio, samplerate=sample_rate)
    sd.wait()


def _speak_with_piper(text: str) -> bool:
    """Returns True if Piper handled this utterance (including the
    legitimate case of empty/silent text) - False only means Piper itself
    is unavailable, so the caller can decide whether to fall back."""
    voice = _get_piper_voice()
    if voice is None:
        return False

    urdu_text = prepare_for_piper(text)
    if not urdu_text:
        return True

    audio, sample_rate = _synthesize(voice, urdu_text)
    if audio is None:
        return True

    _play_audio(audio, sample_rate)
    return True


def _speak_with_pyttsx3(text: str) -> None:
    """Legacy English-voice backend. Only runs if TTS_FALLBACK_TO_PYTTSX3
    is explicitly enabled - an English voice reading Roman Urdu phonetically
    is the exact bad experience Piper replaces, so it must never come back
    silently just because Piper hiccuped. Fresh engine per call, per the
    Brain v3.1 finding that a cached/reused pyttsx3 engine silently stops
    speaking after its first use."""
    import pyttsx3

    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()
    engine.stop()


class _TTSWorker:
    """Owns all live speech on one persistent background thread with a
    queue, so replies are never dropped/skipped and the caller (GUI or CLI)
    never blocks waiting for speech to finish."""

    def __init__(self) -> None:
        self._queue: "queue.Queue" = queue.Queue()
        self._stopped = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while True:
            item = self._queue.get()
            if item is None:  # shutdown sentinel
                self._queue.task_done()
                return
            text, on_done = item
            if not self._stopped.is_set():
                self._speak_one(text)
            if on_done is not None:
                try:
                    on_done()
                except Exception:
                    _logger.exception("TTS on_done callback failed")
            self._queue.task_done()

    def _speak_one(self, text: str) -> None:
        try:
            if PIPER_ENABLED and _speak_with_piper(text):
                return
        except Exception:
            _logger.exception("Piper synthesis/playback failed for: %r", text)

        if TTS_FALLBACK_TO_PYTTSX3:
            try:
                _speak_with_pyttsx3(text)
            except Exception:
                _logger.exception("pyttsx3 fallback speech failed for: %r", text)
        else:
            _logger.warning(
                "No audio produced for reply (Piper unavailable/disabled, "
                "pyttsx3 fallback off): %r", text,
            )

    def enqueue(self, text: str, on_done: Optional[Callable[[], None]]) -> None:
        if self._stopped.is_set():
            if on_done is not None:
                on_done()
            return
        self._queue.put((text, on_done))

    def stop(self) -> None:
        """Stop accepting new speech, interrupt whatever is currently
        playing, and let the worker thread exit - used on app shutdown so
        Fyz doesn't keep talking after the window closes and no orphaned
        playback/process is left running."""
        self._stopped.set()
        sd.stop()
        self._queue.put(None)


_worker: Optional[_TTSWorker] = None
_worker_lock = threading.Lock()


def _get_worker() -> _TTSWorker:
    global _worker
    if _worker is None:
        with _worker_lock:
            if _worker is None:
                _worker = _TTSWorker()
    return _worker


def speak(text: str, on_done: Optional[Callable[[], None]] = None) -> None:
    """Queues `text` for speech and returns immediately - never blocks the
    caller, and multiple calls queue up and play in order rather than one
    silently breaking another. `on_done`, if given, runs on the TTS worker
    thread once this utterance finishes speaking (or fails) - used by
    callers (e.g. the GUI's always-listening mode) that need to know when
    it's safe to start listening again without blocking their own thread."""
    if not TTS_ENABLED:
        if on_done is not None:
            on_done()
        return

    text = strip_emoji(text).strip()
    if not text:
        if on_done is not None:
            on_done()
        return
    _get_worker().enqueue(text, on_done)


def stop_speaking() -> None:
    """Stop accepting new speech, interrupt current playback, and shut the
    worker thread down. Call this on app exit."""
    global _worker
    with _worker_lock:
        if _worker is not None:
            _worker.stop()
            _worker = None


def speak_to_file(text: str, path: str) -> None:
    """Synchronous, one-off rendering to a WAV file - a diagnostic tool
    (used by tests and manual verification), not part of the live speak()
    pipeline."""
    voice = _get_piper_voice()
    if voice is None:
        raise RuntimeError("Piper voice is not available - check PIPER_VOICE_PATH/PIPER_CONFIG_PATH")

    urdu_text = prepare_for_piper(text)
    with wave.open(path, "wb") as wf:
        voice.synthesize_wav(urdu_text, wf)
