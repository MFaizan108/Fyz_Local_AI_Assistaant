from typing import Callable, Optional

from core.action_executor.router import get_permission_level, route
from core.brain.brain import get_intent
from core.brain.context import ConversationContext
from core.brain.conversation import get_chat_reply
from core.brain.identity import get_identity_reply
from core.brain.introduction import looks_like_introduction_request
from core.brain.normalize import normalize_text
from core.brain.schemas import Intent
from core.brain.user_profile import get_profile_reply
from core.logging_setup import get_logger
from core.permissions.levels import PermissionLevel
from memory.action_log import log_action
from tools.desktop_control.registry import get_action

_YES_WORDS = {"y", "yes", "haan", "han", "ji", "ji haan"}
_DANGEROUS_CONFIRM_PHRASE = "confirm"

# Shown to the user instead of any raw exception/traceback - GUI, CLI, and
# voice mode all use this same message via handle_utterance() rather than
# each entry point improvising its own (or, worse, printing the traceback
# itself, which is what used to happen in the GUI's failure path).
TECHNICAL_FAILURE_REPLY = "Bhai 😅 response thora late ho gaya. Ek dafa dobara bolo."

_logger = get_logger(__name__)

ConfirmPrompt = Callable[[str], str]


def _permission_for(intent: Intent) -> Optional[PermissionLevel]:
    """Permission level for an intent - target-aware for desktop_action
    specifically, since one intent name covers ~25 different registered
    shortcuts with different risk levels (copy is SAFE, lock_laptop is
    CONFIRM). Everything else keeps the existing per-intent-name lookup
    unchanged."""
    if intent.intent == "desktop_action" and intent.target:
        action = get_action(intent.target.strip().lower().replace(" ", "_"))
        if action is not None:
            return action.permission
    return get_permission_level(intent.intent)


def _execute_single_intent(intent: Intent, context: ConversationContext, confirm_prompt: ConfirmPrompt) -> str:
    """Runs one already-classified, non-chat intent through permission
    gating, the tool router, and the audit log. Shared by a normal single
    command and by each step of a multi_step_task, so a step gets exactly
    the same SAFE/CONFIRM/DANGEROUS treatment a standalone command would."""
    level = _permission_for(intent)
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


def _collapse_redundant_chrome_steps(steps: list) -> list:
    """A plain "open Chrome" step alongside an "open_browser" step that
    already opens Chrome into a specific profile is the same request said
    twice - despite the prompt explicitly saying not to, the classifier
    still sometimes splits "Chrome kholo aur Faizan profile open karo" into
    exactly this pair. Rather than depend entirely on prompting to prevent
    it, deterministically drop the redundant plain open_app("chrome") step
    whenever a profile-aware open_browser step is also present, so Chrome
    never launches twice for one request."""
    has_profile_step = any(
        step.get("intent") == "open_browser" and (step.get("params") or {}).get("profile")
        for step in steps
    )
    if not has_profile_step:
        return steps

    return [
        step for step in steps
        if not (step.get("intent") == "open_app" and (step.get("target") or "").strip().lower() == "chrome")
    ]


def _execute_multi_step(intent: Intent, context: ConversationContext, confirm_prompt: ConfirmPrompt) -> str:
    """Runs each step of a multi_step_task through _execute_single_intent in
    order, joining their natural replies into one flowing response - never
    "Step 1 (open_browser): ... Step 2 (reopen_closed_tab): ...", since
    internal intent/action names are implementation detail, not something
    Fyz should ever say out loud. A partially-supported request (e.g. "open
    chrome and search today's weather", where web search has no registered
    tool yet) still executes what it can; what it couldn't do is reported
    through that step's own natural reply, not a technical step label."""
    steps = _collapse_redundant_chrome_steps(intent.steps or [])
    if not steps:
        return "Mujhe is command mein koi clear step samajh nahi aaya."

    results = []
    for step_data in steps:
        try:
            step_intent = Intent(raw_text=intent.raw_text, **step_data)
        except Exception:
            results.append("Ek step samajh nahi aaya, skip kar diya.")
            continue

        results.append(_execute_single_intent(step_intent, context, confirm_prompt))

    return " ".join(results)


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

    # An introduction request (e.g. "meray bhai ko mera batao main kon
    # hoon?") takes priority over the identity/profile fast paths below,
    # even when it happens to contain a phrase like "main kon hoon" - those
    # fast paths match anywhere in the message, so without this check an
    # introduction request would get hijacked into a plain "who am I"
    # answer instead of routing to introduce_user. Skipping them here just
    # means this message falls through to full intent classification
    # instead of the instant deterministic answer - a genuine standalone
    # identity question never contains these audience cues, so it's
    # unaffected.
    if not looks_like_introduction_request(text):
        deterministic_reply = get_identity_reply(text) or get_profile_reply(text)
        if deterministic_reply is not None:
            context.add_user_turn(text)
            context.add_assistant_turn(deterministic_reply)
            return deterministic_reply

    try:
        intent = get_intent(text, context)

        if intent.intent == "chat":
            reply = get_chat_reply(text, context)
        elif intent.intent == "multi_step_task":
            reply = _execute_multi_step(intent, context, confirm_prompt)
        else:
            reply = _execute_single_intent(intent, context, confirm_prompt)
    except Exception:
        # Anything from here down (Ollama timeout/connection errors, a tool
        # raising, a parsing bug) must never reach the user as a raw
        # exception/traceback - logged internally instead, GUI/CLI/voice all
        # get the same natural fallback reply via this single shared path.
        _logger.exception("handle_utterance failed for input: %r", text)
        reply = TECHNICAL_FAILURE_REPLY

    context.add_user_turn(text)
    context.add_assistant_turn(reply)
    return reply
