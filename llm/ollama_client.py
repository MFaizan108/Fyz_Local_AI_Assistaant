from typing import List, Optional

import httpx

from core.config import (
    EMBED_MODEL,
    OLLAMA_CONNECT_TIMEOUT,
    OLLAMA_HOST,
    OLLAMA_KEEP_ALIVE,
    OLLAMA_MODEL,
    OLLAMA_NUM_PREDICT,
    OLLAMA_READ_TIMEOUT,
    OLLAMA_TEMPERATURE,
)


def chat(
    message: str,
    system: Optional[str] = None,
    history: Optional[List[dict]] = None,
    model: str = OLLAMA_MODEL,
    timeout: Optional[float] = None,
    json_mode: bool = False,
    temperature: float = OLLAMA_TEMPERATURE,
    num_predict: int = OLLAMA_NUM_PREDICT,
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
        "keep_alive": OLLAMA_KEEP_ALIVE,
        "options": {"temperature": temperature, "num_predict": num_predict},
    }
    if json_mode:
        # Grammar-constrains the output to valid JSON. Needed because plain
        # prompt instructions ("output raw JSON only") aren't reliable - the
        # model would sometimes reply with confirmatory prose instead of
        # JSON for destructive-sounding requests (e.g. delete_file), which
        # broke intent parsing entirely for those cases.
        payload["format"] = "json"

    # Connect and read are split deliberately: connecting to a local Ollama
    # instance should be near-instant, so a slow/refused connection fails
    # fast instead of eating into the same budget as a legitimate slow
    # generation. `timeout=` stays as a back-compat override of just the
    # read timeout (some callers, e.g. the self-improvement sandbox's code
    # rewrite, need more generation headroom than the default).
    request_timeout = httpx.Timeout(
        connect=OLLAMA_CONNECT_TIMEOUT,
        read=timeout if timeout is not None else OLLAMA_READ_TIMEOUT,
        write=10.0,
        pool=10.0,
    )

    response = httpx.post(
        f"{OLLAMA_HOST}/api/chat",
        json=payload,
        timeout=request_timeout,
    )
    response.raise_for_status()
    return response.json()["message"]["content"]


def embed(text: str, model: str = EMBED_MODEL, timeout: float = 30.0) -> List[float]:
    response = httpx.post(
        f"{OLLAMA_HOST}/api/embeddings",
        json={"model": model, "prompt": text},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()["embedding"]
