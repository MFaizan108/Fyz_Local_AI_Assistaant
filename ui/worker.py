import threading
import traceback
from typing import Callable

import numpy as np
from PySide6.QtCore import QThread, Signal

from core.brain.context import ConversationContext
from voice.vad_listener import ContinuousListener


class UtteranceWorker(QThread):
    """Runs handle_utterance() (an LLM call, sometimes two) off the GUI
    thread so the window stays responsive while Fyz is thinking."""

    finished_with_reply = Signal(str, str)
    failed = Signal(str)

    def __init__(self, text: str, context: ConversationContext, confirm_prompt: Callable[[str], str], parent=None):
        super().__init__(parent)
        self.text = text
        self.context = context
        self.confirm_prompt = confirm_prompt

    def run(self) -> None:
        from core.action_executor.dispatch import handle_utterance

        try:
            reply = handle_utterance(self.text, self.context, confirm_prompt=self.confirm_prompt)
        except Exception:
            self.failed.emit(traceback.format_exc(limit=3))
            return

        self.finished_with_reply.emit(self.text, reply)


class TranscribeWorker(QThread):
    """Runs faster-whisper transcription off the GUI thread."""

    finished_with_text = Signal(str)
    failed = Signal(str)

    def __init__(self, audio: np.ndarray, parent=None):
        super().__init__(parent)
        self.audio = audio

    def run(self) -> None:
        from voice.stt import transcribe

        try:
            text = transcribe(self.audio)
        except Exception:
            self.failed.emit(traceback.format_exc(limit=3))
            return

        self.finished_with_text.emit(text)


class ContinuousListenWorker(QThread):
    """Jarvis-style always-on listening for the mic button's toggle mode:
    runs ContinuousListener's speech-detection loop off the GUI thread and
    emits transcribed text per detected utterance. Pauses itself after each
    utterance (via a threading.Event, since this loop lives on a real OS
    thread outside Qt's signal machinery) until the main thread calls
    resume() - otherwise the mic would still be "listening" while Fyz is
    speaking its reply out loud, right back into itself.

    A failure here (e.g. transcription raising) used to kill the thread
    silently, leaving the GUI stuck showing "Hamesha sun raha hoon..."
    forever with no indication anything went wrong - failed surfaces that
    instead of swallowing it."""

    utterance_ready = Signal(str)
    failed = Signal(str)

    def __init__(self, listener: ContinuousListener, parent=None):
        super().__init__(parent)
        self.listener = listener
        self._resume_event = threading.Event()
        self._resume_event.set()

    def resume(self) -> None:
        self._resume_event.set()

    def run(self) -> None:
        from voice.stt import transcribe

        try:
            for audio in self.listener.listen_for_utterances():
                text = transcribe(audio).strip()
                if text:
                    self._resume_event.clear()
                    self.utterance_ready.emit(text)
                    self._resume_event.wait()
        except Exception:
            self.failed.emit(traceback.format_exc(limit=3))
