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
        print(f"Fyz(intent): {intent.model_dump_json()}")


if __name__ == "__main__":
    main()
