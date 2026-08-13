from typing import Callable

from core.action_executor.router import get_permission_level, route
from core.brain.brain import get_intent
from core.brain.context import ConversationContext
from core.brain.conversation import get_chat_reply
from core.permissions.levels import PermissionLevel

_YES_WORDS = {"y", "yes", "haan", "han", "ji", "ji haan"}


def handle_utterance(
    text: str,
    context: ConversationContext,
    confirm_prompt: Callable[[str], str] = input,
) -> str:
    """Run one user utterance through intent parsing, then either the chat
    persona or the tool router (with a y/n gate for CONFIRM-tier tools),
    updating context either way. Shared by the text and voice entrypoints."""
    intent = get_intent(text, context)

    if intent.intent == "chat":
        reply = get_chat_reply(text, context)
    elif get_permission_level(intent.intent) == PermissionLevel.CONFIRM:
        answer = confirm_prompt(f"Fyz: Confirm karoon? ({intent.intent}: {intent.target}) [y/n] ")
        if answer.strip().lower() in _YES_WORDS:
            reply = route(intent, context) or "(no result)"
        else:
            reply = "Theek hai, nahi karta."
    else:
        reply = route(intent, context) or "(no result)"

    context.add_user_turn(text)
    context.add_assistant_turn(reply)
    return reply
