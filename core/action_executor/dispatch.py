from typing import Callable

from core.action_executor.router import get_permission_level, route
from core.brain.brain import get_intent
from core.brain.context import ConversationContext
from core.brain.conversation import get_chat_reply
from core.brain.normalize import normalize_text
from core.permissions.levels import PermissionLevel
from memory.action_log import log_action

_YES_WORDS = {"y", "yes", "haan", "han", "ji", "ji haan"}
_DANGEROUS_CONFIRM_PHRASE = "confirm"


def handle_utterance(
    text: str,
    context: ConversationContext,
    confirm_prompt: Callable[[str], str] = input,
) -> str:
    """Run one user utterance through intent parsing, then either the chat
    persona or the tool router. CONFIRM-tier tools need a y/n; DANGEROUS-tier
    tools need the exact confirm phrase typed back, not just "y" - a casual
    yes should never be enough to trigger something destructive. Every
    routed (non-chat) intent gets logged to actions_history regardless of
    whether it actually ran, so declined actions are auditable too. Shared
    by the text and voice entrypoints."""
    text = normalize_text(text)
    intent = get_intent(text, context)

    if intent.intent == "chat":
        reply = get_chat_reply(text, context)
        context.add_user_turn(text)
        context.add_assistant_turn(reply)
        return reply

    level = get_permission_level(intent.intent)
    executed = True

    if level == PermissionLevel.DANGEROUS:
        answer = confirm_prompt(
            f"Fyz: Yeh DANGEROUS action hai ({intent.intent}: {intent.target}). "
            f"Pakka karna hai? Type '{_DANGEROUS_CONFIRM_PHRASE}' to proceed: "
        )
        if answer.strip().lower() == _DANGEROUS_CONFIRM_PHRASE:
            reply = route(intent, context) or "(no result)"
        else:
            reply = "Theek hai, cancel kar diya - yeh dangerous tha."
            executed = False
    elif level == PermissionLevel.CONFIRM:
        answer = confirm_prompt(f"Fyz: Confirm karoon? ({intent.intent}: {intent.target}) [y/n] ")
        if answer.strip().lower() in _YES_WORDS:
            reply = route(intent, context) or "(no result)"
        else:
            reply = "Theek hai, nahi karta."
            executed = False
    else:
        reply = route(intent, context) or "(no result)"

    log_action(
        intent=intent.intent,
        target=intent.target,
        level=level.value if level else "unknown",
        result=reply,
        executed=executed,
    )

    context.add_user_turn(text)
    context.add_assistant_turn(reply)
    return reply
