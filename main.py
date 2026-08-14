import sys

from core.action_executor.dispatch import TECHNICAL_FAILURE_REPLY, handle_utterance
from core.brain.context import ConversationContext
from core.logging_setup import get_logger

# Windows consoles default to a legacy codepage (e.g. cp1252) that can't
# encode emoji or Urdu script, which Fyz's replies will routinely contain.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_logger = get_logger(__name__)


def main() -> None:
    print("Fyz is listening (text mode). Type 'exit' to quit.")
    context = ConversationContext()

    while True:
        try:
            text = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not text:
            continue
        if text.lower() in {"exit", "quit"}:
            break

        try:
            reply = handle_utterance(text, context)
        except Exception:
            # handle_utterance() already catches its own internal failures
            # (Ollama timeouts etc.) - this is a last-resort net for
            # anything unexpected outside that, so the CLI never dies with
            # a raw traceback either.
            _logger.exception("Unexpected failure handling: %r", text)
            reply = TECHNICAL_FAILURE_REPLY
        print(f"Fyz: {reply}")


if __name__ == "__main__":
    main()
