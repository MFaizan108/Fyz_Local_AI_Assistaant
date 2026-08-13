from PySide6.QtCore import QObject, Qt, Signal, Slot
from PySide6.QtWidgets import QInputDialog


class ConfirmBridge(QObject):
    """dispatch.handle_utterance()'s confirm_prompt is a plain callable that
    blocks until it has an answer. When the reply comes from a worker
    QThread (so the GUI doesn't freeze during an LLM call), that callable
    still needs to show a real modal dialog on the MAIN thread and hand the
    answer back to the worker thread. Qt.BlockingQueuedConnection is exactly
    built for this: emitting ask_signal from the worker thread blocks that
    thread until the main thread's slot has run and filled in the holder."""

    ask_signal = Signal(str, object)

    def __init__(self, parent_widget):
        super().__init__()
        self.parent_widget = parent_widget
        self.ask_signal.connect(self._handle_ask, Qt.ConnectionType.BlockingQueuedConnection)

    @Slot(str, object)
    def _handle_ask(self, message: str, holder: dict) -> None:
        text, ok = QInputDialog.getText(self.parent_widget, "Fyz", message)
        holder["answer"] = text if ok else ""

    def confirm_prompt(self, message: str) -> str:
        holder: dict = {}
        self.ask_signal.emit(message, holder)
        return holder.get("answer", "")
