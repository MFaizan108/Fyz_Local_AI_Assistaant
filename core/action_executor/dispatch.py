from typing import Callable

from core.action_executor.router import get_permission_level, route
from core.brain.brain import get_intent
from core.brain.context import ConversationContext
from core.brain.conversation import get_chat_reply
from core.brain.identity import get_identity_reply
from core.brain.normalize import normalize_text
from core.brain.schemas import Intent
from core.permissions.levels import PermissionLevel
from memory.action_log import log_action

_YES_WORDS = {"y", "yes", "haan", "han", "ji", "ji haan"}
_DANGEROUS_CONFIRM_PHRASE = "confirm"

ConfirmPrompt = Callable[[str], str]


def _execute_single_intent(intent: Intent, context: ConversationContext, confirm_prompt: ConfirmPrompt) -> str:
    """Runs one already-classified, non-chat intent through permission
    gating, the tool router, and the audit log. Shared by a normal single
    command and by each step of a multi_step_task, so a step gets exactly
    the same SAFE/CONFIRM/DANGEROUS treatment a standalone command would."""
    level = get_permission_level(intent.intent)
    executed = True

    if level == PermissionLevel.DANGEROUS:
        answer = confirm_prompt(
            f"Fyz: Yeh DANGEROUS action hai ({intent.intent}: {intent.target}). "
            f"Pakka karna hai? Type '{_DANGEROUS_CONFIRM_PHRASE}' to proceed: "
        )
        if answer.strip().lower() == _DANGEROUS_CONFIRM_PHRASE:
            reply = route(intent, context, confirm_prompt) or "(no result)"
        else:
            reply = "Theek hai, cancel kar diya - yeh dangerous tha."
            executed = False
    elif level == PermissionLevel.CONFIRM:
        answer = confirm_prompt(f"Fyz: Confirm karoon? ({intent.intent}: {intent.target}) [y/n] ")
        if answer.strip().lower() in _YES_WORDS:
            reply = route(intent, context, confirm_prompt) or "(no result)"
        else:
            reply = "Theek hai, nahi karta."
            executed = False
    else:
        reply = route(intent, context, confirm_prompt) or "(no result)"

    log_action(
        intent=intent.intent,
        target=intent.target,
        level=level.value if level else "unknown",
        result=reply,
        executed=executed,
    )
    return reply


def _execute_multi_step(intent: Intent, context: ConversationContext, confirm_prompt: ConfirmPrompt) -> str:
    """Runs each step of a multi_step_task through _execute_single_intent in
    order, tracking every step's result so a partially-supported request
    (e.g. "open chrome and search today's weather", where web search has no
    registered tool yet) still executes what it can and clearly reports what
    it couldn't, instead of silently only doing the first thing."""
    steps = intent.steps or []
    if not steps:
        return "Mujhe is command mein koi clear step samajh nahi aaya."

    results = []
    for i, step_data in enumerate(steps, start=1):
        try:
            step_intent = Intent(raw_text=intent.raw_text, **step_data)
        except Exception:
            results.append(f"Step {i}: samajh nahi aaya, skip kar diya.")
            continue

        step_reply = _execute_single_intent(step_intent, context, confirm_prompt)
        results.append(f"Step {i} ({step_intent.intent}): {step_reply}")

    return "\n".join(results)


def handle_utterance(
    text: str,
    context: ConversationContext,
    confirm_prompt: ConfirmPrompt = input,
) -> str:
    """Run one user utterance through identity detection, then intent
    parsing, then either the chat persona, a single tool, or a multi-step
    plan. Identity questions ("who made you", "who are you") are answered
    deterministically before the LLM is ever consulted, so they can't
    hallucinate or contradict Fyz's own identity. CONFIRM-tier tools need a
    y/n; DANGEROUS-tier tools need the exact confirm phrase typed back, not
    just "y" - a casual yes should never be enough to trigger something
    destructive. Every routed (non-chat) intent gets logged to
    actions_history regardless of whether it actually ran, so declined
    actions are auditable too. Shared by the text and voice entrypoints."""
    text = normalize_text(text)

    identity_reply = get_identity_reply(text)
    if identity_reply is not None:
        context.add_user_turn(text)
        context.add_assistant_turn(identity_reply)
        return identity_reply

    intent = get_intent(text, context)

    if intent.intent == "chat":
        reply = get_chat_reply(text, context)
    elif intent.intent == "multi_step_task":
        reply = _execute_multi_step(intent, context, confirm_prompt)
    else:
        reply = _execute_single_intent(intent, context, confirm_prompt)

    context.add_user_turn(text)
    context.add_assistant_turn(reply)
    return reply
