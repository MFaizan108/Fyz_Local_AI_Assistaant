import queue
import re
import threading
from typing import Callable, Optional

import pyttsx3

from core.logging_setup import get_logger

_logger = get_logger(__name__)

# Covers the common emoji blocks (emoticons, symbols/pictographs, transport,
# supplemental symbols, dingbats, variation selectors) plus the zero-width
# joiner used in compound emoji. Emojis are for visual emotion in chat/GUI
# text, not meant to be read aloud - pyttsx3 otherwise spells out their
# Unicode names ("smiling face with smiling eyes"), which is worse than
# just skipping them.
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "\U00002190-\U000021FF"
    "\U00002B00-\U00002BFF"
    "\U0000FE0F"
    "\U0000200D"
    "]+",
    flags=re.UNICODE,
)


def strip_emoji(text: str) -> str:
    return _EMOJI_RE.sub("", text)


class _TTSWorker:
    """Owns all live speech on one persistent background thread with a
    queue, so replies are never dropped/skipped and the caller (GUI or CLI)
    never blocks waiting for speech to finish.

    Root cause of "only the first reply gets spoken": a single cached
    pyttsx3 engine (`@lru_cache`, reused for every call) worked for the
    first say()/runAndWait() cycle but silently did nothing on later calls -
    a well-documented pyttsx3/SAPI5 issue on Windows where runAndWait()'s
    internal COM event loop doesn't cleanly reset for reuse. The reliable
    fix (confirmed against multiple pyttsx3 issue reports, not guessed) is
    a FRESH engine per utterance rather than one long-lived shared instance
    - done here on a single dedicated thread (not a new thread per call) so
    COM/threading stays consistent and speech is naturally serialized."""

    def __init__(self) -> None:
        self._queue: "queue.Queue[tuple[str, Optional[Callable[[], None]]]]" = queue.Queue()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while True:
            text, on_done = self._queue.get()
            try:
                engine = pyttsx3.init()
                engine.say(text)
                engine.runAndWait()
                engine.stop()
            except Exception:
                _logger.exception("TTS speak failed for: %r", text)
            finally:
                if on_done is not None:
                    try:
                        on_done()
                    except Exception:
                        _logger.exception("TTS on_done callback failed")
                self._queue.task_done()

    def enqueue(self, text: str, on_done: Optional[Callable[[], None]]) -> None:
        self._queue.put((text, on_done))


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
    text = strip_emoji(text).strip()
    if not text:
        if on_done is not None:
            on_done()
        return
    _get_worker().enqueue(text, on_done)


def speak_to_file(text: str, path: str) -> None:
    """Synchronous, one-off rendering to a WAV file (used by tests/tools,
    not the live speak() pipeline) - a fresh engine per call for the same
    reliability reason as speak()."""
    text = strip_emoji(text).strip()
    engine = pyttsx3.init()
    engine.save_to_file(text, path)
    engine.runAndWait()
    engine.stop()
