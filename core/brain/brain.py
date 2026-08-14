import json
import re
from typing import Optional

from core.brain.context import ConversationContext
from core.brain.prompts import SYSTEM_PROMPT
from core.brain.schemas import Intent
from llm.ollama_client import chat

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def get_intent(user_text: str, context: Optional[ConversationContext] = None) -> Intent:
    history = context.recent_messages() if context else None
    # A multi_step_task's JSON can run longer than a single-intent object
    # (one nested {"intent","target","params"} dict per step), so this gets
    # more headroom than the conversational reply's default num_predict.
    reply = chat(user_text, system=SYSTEM_PROMPT, history=history, json_mode=True, num_predict=350)

    match = _JSON_BLOCK_RE.search(reply)
    if not match:
        return Intent(intent="chat", raw_text=user_text)

    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return Intent(intent="chat", raw_text=user_text)

    if not isinstance(data, dict) or "intent" not in data:
        return Intent(intent="chat", raw_text=user_text)

    data.setdefault("params", {})
    return Intent(raw_text=user_text, **data)
