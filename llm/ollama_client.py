import httpx

from core.config import OLLAMA_HOST, OLLAMA_MODEL


def chat(message: str, model: str = OLLAMA_MODEL, timeout: float = 60.0) -> str:
    response = httpx.post(
        f"{OLLAMA_HOST}/api/chat",
        json={
            "model": model,
            "messages": [{"role": "user", "content": message}],
            "stream": False,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()["message"]["content"]
