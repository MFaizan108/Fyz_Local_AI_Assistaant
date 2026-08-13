from core.action_executor.router import route
from core.brain.brain import get_intent


def main() -> None:
    print("Fyz is listening (text mode). Type 'exit' to quit.")
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

        intent = get_intent(text)
        result = route(intent)

        if result is None:
            print("Fyz: (just chatting - conversation mode isn't built yet, Phase 4)")
        else:
            print(f"Fyz: {result}")


if __name__ == "__main__":
    main()
