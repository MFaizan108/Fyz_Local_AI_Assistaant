from typing import List, Optional

import httpx

from core.config import OLLAMA_HOST, OLLAMA_MODEL


def chat(
    message: str,
    system: Optional[str] = None,
    history: Optional[List[dict]] = None,
    model: str = OLLAMA_MODEL,
    timeout: float = 60.0,
) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": message})

    response = httpx.post(
        f"{OLLAMA_HOST}/api/chat",
        json={
            "model": model,
            "messages": messages,
            "stream": False,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()["message"]["content"]
