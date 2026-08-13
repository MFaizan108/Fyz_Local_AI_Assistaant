import sys

from core.action_executor.dispatch import handle_utterance
from core.brain.context import ConversationContext
from voice.recorder import record_until_enter
from voice.stt import transcribe
from voice.tts import speak
from voice.vad_listener import ContinuousListener, is_exit_phrase

# Windows consoles default to a legacy codepage (e.g. cp1252) that can't
# encode emoji or Urdu script, which Fyz's replies will routinely contain.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _handle_one_utterance(audio, context: ConversationContext) -> bool:
    """Returns False if the conversation should stop."""
    text = transcribe(audio).strip()
    if not text:
        return True

    print(f"You (heard): {text}")

    if is_exit_phrase(text):
        reply = "Theek hai bhai, phir milte hain."
        print(f"Fyz: {reply}")
        speak(reply)
        return False

    reply = handle_utterance(text, context)
    print(f"Fyz: {reply}")
    speak(reply)
    return True


def main_always_listening() -> None:
    """Jarvis-style: no button, no Enter key - Fyz is always listening and
    automatically detects when you start/stop talking (voice activity
    detection). Say "band karo" / "exit" / "stop" to end, or Ctrl+C."""
    print("Fyz hamesha sun raha hai - jab chaho bolna shuru karo. Rukne ke liye 'band karo' bolo ya Ctrl+C.")
    context = ConversationContext()
    listener = ContinuousListener()

    try:
        for audio in listener.listen_for_utterances():
            if not _handle_one_utterance(audio, context):
                listener.stop()
    except KeyboardInterrupt:
        print()


def main_push_to_talk() -> None:
    """Fallback mode: press Enter to start talking, Enter again to stop -
    useful if always-listening mode is too sensitive/insensitive for your
    mic and room before the VAD threshold gets tuned."""
    print("Fyz voice mode (push-to-talk). Press Enter to start talking, Enter again to stop. Ctrl+C to quit.")
    context = ConversationContext()

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


def main() -> None:
    if "--push-to-talk" in sys.argv:
        main_push_to_talk()
    else:
        main_always_listening()


if __name__ == "__main__":
    main()
