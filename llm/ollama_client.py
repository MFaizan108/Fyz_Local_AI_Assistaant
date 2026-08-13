from typing import List, Optional

import httpx

from core.config import OLLAMA_HOST, OLLAMA_MODEL


def chat(
    message: str,
    system: Optional[str] = None,
    history: Optional[List[dict]] = None,
    model: str = OLLAMA_MODEL,
    timeout: float = 60.0,
    json_mode: bool = False,
) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": message})

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    if json_mode:
        # Grammar-constrains the output to valid JSON. Needed because plain
        # prompt instructions ("output raw JSON only") aren't reliable - the
        # model would sometimes reply with confirmatory prose instead of
        # JSON for destructive-sounding requests (e.g. delete_file), which
        # broke intent parsing entirely for those cases.
        payload["format"] = "json"

    response = httpx.post(
        f"{OLLAMA_HOST}/api/chat",
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()["message"]["content"]
