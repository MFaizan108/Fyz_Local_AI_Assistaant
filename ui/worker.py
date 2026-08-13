from typing import Callable

import numpy as np
from PySide6.QtCore import QThread, Signal

from core.brain.context import ConversationContext


class UtteranceWorker(QThread):
    """Runs handle_utterance() (an LLM call, sometimes two) off the GUI
    thread so the window stays responsive while Fyz is thinking."""

    finished_with_reply = Signal(str, str)

    def __init__(self, text: str, context: ConversationContext, confirm_prompt: Callable[[str], str], parent=None):
        super().__init__(parent)
        self.text = text
        self.context = context
        self.confirm_prompt = confirm_prompt

    def run(self) -> None:
        from core.action_executor.dispatch import handle_utterance

        reply = handle_utterance(self.text, self.context, confirm_prompt=self.confirm_prompt)
        self.finished_with_reply.emit(self.text, reply)


class TranscribeWorker(QThread):
    """Runs faster-whisper transcription off the GUI thread."""

    finished_with_text = Signal(str)

    def __init__(self, audio: np.ndarray, parent=None):
        super().__init__(parent)
        self.audio = audio

    def run(self) -> None:
        from voice.stt import transcribe

        text = transcribe(self.audio)
        self.finished_with_text.emit(text)
