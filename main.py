import time

from llm.ollama_client import chat


def main() -> None:
    print("Fyz Phase 0 milestone check: sending 'Hello' to Qwen via Ollama...")
    start = time.perf_counter()
    reply = chat("Hello")
    elapsed = time.perf_counter() - start
    print(f"Qwen replied in {elapsed:.2f}s:\n{reply}")


if __name__ == "__main__":
    main()
