import sys
from typing import Optional

from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.brain.context import ConversationContext
from memory.action_log import recent_actions
from ui.confirm_bridge import ConfirmBridge
from ui.worker import ContinuousListenWorker, TranscribeWorker, UtteranceWorker
from voice.recorder import Recorder
from voice.tts import speak
from voice.vad_listener import ContinuousListener, is_exit_phrase


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FYZ")
        self.resize(480, 640)

        self.context = ConversationContext()
        self.confirm_bridge = ConfirmBridge(self)
        self.recorder = Recorder()
        self.is_recording = False
        self.worker: Optional[UtteranceWorker] = None
        self.transcribe_worker: Optional[TranscribeWorker] = None

        self.continuous_listener = ContinuousListener()
        self.listen_worker: Optional[ContinuousListenWorker] = None
        self.always_listening = False

        central = QWidget()
        layout = QVBoxLayout(central)

        self.status_label = QLabel("● Idle")
        layout.addWidget(self.status_label)

        self.chat_log = QTextEdit()
        self.chat_log.setReadOnly(True)
        layout.addWidget(self.chat_log, stretch=3)

        input_row = QHBoxLayout()
        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("Fyz se baat karo...")
        self.input_box.returnPressed.connect(self._on_send)
        input_row.addWidget(self.input_box)

        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self._on_send)
        input_row.addWidget(self.send_button)

        self.mic_button = QPushButton("\U0001F3A4")
        self.mic_button.setFixedWidth(40)
        self.mic_button.setToolTip("Click to start always-listening mode (Jarvis-style)")
        self.mic_button.clicked.connect(self._on_mic_clicked)
        input_row.addWidget(self.mic_button)

        layout.addLayout(input_row)

        options_row = QHBoxLayout()
        self.speak_checkbox = QCheckBox("Speak replies")
        self.speak_checkbox.setChecked(True)
        options_row.addWidget(self.speak_checkbox)

        self.push_to_talk_checkbox = QCheckBox("Push-to-talk (instead of always-listening)")
        self.push_to_talk_checkbox.setToolTip(
            "Fallback mode: click mic to start recording, click again to stop - "
            "use this if always-listening mode is too sensitive/insensitive for your mic."
        )
        options_row.addWidget(self.push_to_talk_checkbox)
        layout.addLayout(options_row)

        layout.addWidget(QLabel("Recent Activity"))
        self.activity_list = QListWidget()
        layout.addWidget(self.activity_list, stretch=1)

        self.setCentralWidget(central)
        self._refresh_activity()

    def _append_chat(self, speaker: str, text: str) -> None:
        self.chat_log.append(f"<b>{speaker}:</b> {text}")

    def _set_busy(self, busy: bool, status: str = "") -> None:
        self.input_box.setEnabled(not busy)
        self.send_button.setEnabled(not busy)
        if not self.always_listening:
            self.mic_button.setEnabled(not busy)
        self.status_label.setText(status or ("● Thinking..." if busy else "● Idle"))

    def _on_send(self) -> None:
        text = self.input_box.text().strip()
        if not text:
            return
        self.input_box.clear()
        self._submit(text)

    def _submit(self, text: str) -> None:
        self._append_chat("You", text)
        self._set_busy(True, "● Thinking...")

        self.worker = UtteranceWorker(text, self.context, self.confirm_bridge.confirm_prompt)
        self.worker.finished_with_reply.connect(self._on_reply)
        self.worker.start()

    def _on_reply(self, user_text: str, reply: str) -> None:
        self._append_chat("Fyz", reply)
        self._set_busy(False)
        self._refresh_activity()
        if self.speak_checkbox.isChecked():
            speak(reply)
        if self.always_listening and self.listen_worker is not None:
            self.status_label.setText("● Hamesha sun raha hoon...")
            self.listen_worker.resume()

    def _on_mic_clicked(self) -> None:
        if self.push_to_talk_checkbox.isChecked():
            self._on_push_to_talk_mic_clicked()
        else:
            self._on_always_listening_mic_clicked()

    def _on_push_to_talk_mic_clicked(self) -> None:
        if not self.is_recording:
            self.recorder.start()
            self.is_recording = True
            self.mic_button.setText("⏹")
            self.status_label.setText("● Listening...")
        else:
            audio = self.recorder.stop()
            self.is_recording = False
            self.mic_button.setText("\U0001F3A4")
            self._set_busy(True, "● Transcribing...")

            self.transcribe_worker = TranscribeWorker(audio)
            self.transcribe_worker.finished_with_text.connect(self._on_transcribed)
            self.transcribe_worker.start()

    def _on_transcribed(self, text: str) -> None:
        text = text.strip()
        if not text:
            self._set_busy(False)
            self.status_label.setText("● Kuch sunai nahi diya")
            return
        self._submit(text)

    def _on_always_listening_mic_clicked(self) -> None:
        if not self.always_listening:
            self.always_listening = True
            self.mic_button.setText("\U0001F534")
            self.mic_button.setToolTip("Click to stop always-listening mode")
            self.status_label.setText("● Hamesha sun raha hoon...")
            self.push_to_talk_checkbox.setEnabled(False)

            self.listen_worker = ContinuousListenWorker(self.continuous_listener)
            self.listen_worker.utterance_ready.connect(self._on_continuous_utterance)
            self.listen_worker.start()
        else:
            self._stop_always_listening()

    def _stop_always_listening(self) -> None:
        self.always_listening = False
        self.continuous_listener.stop()
        if self.listen_worker is not None:
            self.listen_worker.resume()
        self.mic_button.setText("\U0001F3A4")
        self.mic_button.setToolTip("Click to start always-listening mode (Jarvis-style)")
        self.push_to_talk_checkbox.setEnabled(True)
        self._set_busy(False)

    def _on_continuous_utterance(self, text: str) -> None:
        if is_exit_phrase(text):
            self._append_chat("You", text)
            self._append_chat("Fyz", "Theek hai, sunna band kar deta hoon.")
            self._stop_always_listening()
            return
        self._submit(text)

    def _refresh_activity(self) -> None:
        self.activity_list.clear()
        for entry in recent_actions(limit=10):
            mark = "✓" if entry.executed else "✗"
            self.activity_list.addItem(f"{mark} {entry.intent}: {entry.target or ''}")


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
