import sys

from core.action_executor.router import get_permission_level, route
from core.brain.brain import get_intent
from core.brain.context import ConversationContext
from core.brain.conversation import get_chat_reply
from core.permissions.levels import PermissionLevel

# Windows consoles default to a legacy codepage (e.g. cp1252) that can't
# encode emoji or Urdu script, which Fyz's replies will routinely contain.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_YES_WORDS = {"y", "yes", "haan", "han", "ji", "ji haan"}


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

        intent = get_intent(text, context)

        if intent.intent == "chat":
            reply = get_chat_reply(text, context)
        elif get_permission_level(intent.intent) == PermissionLevel.CONFIRM:
            confirm = input(f"Fyz: Confirm karoon? ({intent.intent}: {intent.target}) [y/n] ")
            if confirm.strip().lower() in _YES_WORDS:
                reply = route(intent, context) or "(no result)"
            else:
                reply = "Theek hai, nahi karta."
        else:
            reply = route(intent, context) or "(no result)"

        print(f"Fyz: {reply}")
        context.add_user_turn(text)
        context.add_assistant_turn(reply)


if __name__ == "__main__":
    main()
