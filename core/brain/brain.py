import json
import re
from typing import Optional

from core.brain.context import ConversationContext
from core.brain.prompts import SYSTEM_PROMPT
from core.brain.schemas import Intent
from core.config import OLLAMA_NUM_PREDICT_INTENT
from llm.ollama_client import chat
from tools.desktop_control.registry import get_action

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def _normalize_desktop_action(data: dict) -> None:
    """The system prompt lists ~25 registered shortcut names formatted
    similarly to real top-level intents (`- "lock_laptop": Lock the
    laptop`), and despite the explicit instruction that these are only
    valid `target` VALUES for the `desktop_action` intent, the model
    occasionally outputs the action name directly as `intent` instead (e.g.
    `{"intent": "lock_laptop"}` instead of `{"intent": "desktop_action",
    "target": "lock_laptop"}`) - found via live testing, not assumed. Rather
    than rely purely on prompt wording (which can't be 100% steered),
    self-heal this shape here so the action still executes correctly.
    Mutates `data` in place; a no-op for any already-correct shape."""
    intent_name = data.get("intent")
    if intent_name and intent_name != "desktop_action" and get_action(intent_name) is not None:
        data["target"] = intent_name
        data["intent"] = "desktop_action"

    for step in data.get("steps") or []:
        if isinstance(step, dict):
            _normalize_desktop_action(step)


def get_intent(user_text: str, context: Optional[ConversationContext] = None) -> Intent:
    history = context.recent_messages() if context else None
    # A multi_step_task's JSON can run longer than a single-intent object
    # (one nested {"intent","target","params"} dict per step), so this gets
    # more headroom than the conversational reply's default num_predict -
    # but a realistic 2-3 step plan is well under 150 tokens, so this stays
    # far smaller than a full conversational reply's cap. Smaller cap =
    # faster classification = less likely to hit a slow/cold-load timeout.
    reply = chat(
        user_text, system=SYSTEM_PROMPT, history=history,
        json_mode=True, num_predict=OLLAMA_NUM_PREDICT_INTENT,
    )

    match = _JSON_BLOCK_RE.search(reply)
    if not match:
        return Intent(intent="chat", raw_text=user_text)

    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return Intent(intent="chat", raw_text=user_text)

    if not isinstance(data, dict) or "intent" not in data:
        return Intent(intent="chat", raw_text=user_text)

    _normalize_desktop_action(data)
    data.setdefault("params", {})
    return Intent(raw_text=user_text, **data)
