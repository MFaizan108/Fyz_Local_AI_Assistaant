import sys

from core.action_executor.dispatch import handle_utterance
from core.brain.context import ConversationContext
from voice.recorder import record_until_enter
from voice.stt import transcribe

# Windows consoles default to a legacy codepage (e.g. cp1252) that can't
# encode emoji or Urdu script, which Fyz's replies will routinely contain.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_EXIT_WORDS = {"exit", "quit", "band karo", "bye"}


def main() -> None:
    print("Fyz voice mode. Press Enter to start talking, Enter again to stop. Ctrl+C to quit.")
    context = ConversationContext()

    while True:
        try:
            input("\n[Press Enter to talk to Fyz] ")
        except (EOFError, KeyboardInterrupt):
            print()
            break

        print("Listening... press Enter to stop.")
        audio = record_until_enter()

        text = transcribe(audio).strip()
        if not text:
            print("Fyz: Kuch sunai nahi diya, dobara try karo.")
            continue

        print(f"You (heard): {text}")
        if text.lower() in _EXIT_WORDS:
            break

        reply = handle_utterance(text, context)
        print(f"Fyz: {reply}")


if __name__ == "__main__":
    main()
