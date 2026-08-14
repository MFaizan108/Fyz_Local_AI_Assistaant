import sys
import threading

from core.action_executor.dispatch import TECHNICAL_FAILURE_REPLY, handle_utterance
from core.brain.context import ConversationContext
from core.logging_setup import get_logger
from voice.recorder import record_until_enter
from voice.stt import transcribe
from voice.tts import speak, stop_speaking
from voice.vad_listener import ContinuousListener, is_exit_phrase

# Windows consoles default to a legacy codepage (e.g. cp1252) that can't
# encode emoji or Urdu script, which Fyz's replies will routinely contain.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_logger = get_logger(__name__)


def _speak_and_wait(text: str) -> None:
    """speak() now just enqueues onto a persistent background TTS worker
    and returns immediately (so the GUI never freezes) - but this CLI loop
    still needs to wait for speech to actually finish before listening
    again, otherwise the mic would re-arm mid-sentence and risk hearing
    Fyz's own voice as new input."""
    done = threading.Event()
    speak(text, on_done=done.set)
    done.wait()


def _handle_one_utterance(audio, context: ConversationContext) -> bool:
    """Returns False if the conversation should stop."""
    try:
        text = transcribe(audio).strip()
    except Exception:
        _logger.exception("STT transcription failed")
        print("Fyz: Sunte waqt error aa gaya, phir try karo.")
        return True

    if not text:
        return True

    print(f"You (heard): {text}")

    if is_exit_phrase(text):
        reply = "Theek hai bhai, phir milte hain."
        print(f"Fyz: {reply}")
        _speak_and_wait(reply)
        return False

    try:
        reply = handle_utterance(text, context)
    except Exception:
        # handle_utterance() already catches its own internal failures -
        # this is a last-resort net for anything unexpected outside that.
        _logger.exception("Unexpected failure handling: %r", text)
        reply = TECHNICAL_FAILURE_REPLY

    print(f"Fyz: {reply}")
    _speak_and_wait(reply)
    return True


def main_always_listening() -> None:
    """Jarvis-style: no button, no Enter key - Fyz is always listening and
    automatically detects when you start/stop talking (voice activity
    detection). Say "band karo" / "exit" / "stop" to end, or Ctrl+C."""
    from voice.vad_listener import ENERGY_THRESHOLD

    print(f"[VAD_ENERGY_THRESHOLD = {ENERGY_THRESHOLD} - agar detect nahi ho raha, "
          f"'python voice_main.py --mic-check' chala ke apna mic level dekho]")
    print("Fyz hamesha sun raha hai - jab chaho bolna shuru karo. Rukne ke liye 'band karo' bolo ya Ctrl+C.")
    context = ConversationContext()
    listener = ContinuousListener()

    try:
        for audio in listener.listen_for_utterances():
            if not _handle_one_utterance(audio, context):
                listener.stop()
    except KeyboardInterrupt:
        print()
    finally:
        stop_speaking()


def main_push_to_talk() -> None:
    """Fallback mode: press Enter to start talking, Enter again to stop -
    useful if always-listening mode is too sensitive/insensitive for your
    mic and room before the VAD threshold gets tuned."""
    print("Fyz voice mode (push-to-talk). Press Enter to start talking, Enter again to stop. Ctrl+C to quit.")
    context = ConversationContext()

    try:
        while True:
            try:
                input("\n[Press Enter to talk to Fyz] ")
            except (EOFError, KeyboardInterrupt):
                print()
                break

            print("Listening... press Enter to stop.")
            audio = record_until_enter()
            if not _handle_one_utterance(audio, context):
                break
    finally:
        stop_speaking()


def main() -> None:
    if "--mic-check" in sys.argv:
        from voice.vad_listener import print_mic_check

        print_mic_check()
    elif "--push-to-talk" in sys.argv:
        main_push_to_talk()
    else:
        main_always_listening()


if __name__ == "__main__":
    main()
