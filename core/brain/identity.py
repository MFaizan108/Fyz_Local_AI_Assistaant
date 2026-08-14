"""Centralized identity facts for Fyz - the single source of truth for who
Fyz is, so the system prompt and the deterministic identity handler below
never drift out of sync or contradict each other. Change these constants,
not a hardcoded string somewhere else, if identity facts ever need to
change."""

from typing import Optional

NAME = "Fyz"
CREATOR = "Muhammad Faizan Ur Rahman"
PRIMARY_USER = "Muhammad Faizan Ur Rahman"
ROLE = "personal local AI companion"
PURPOSE = "friendly conversational companion aur laptop/project assistant"
BRAND = "FaizanSoft Labs"

IDENTITY_BRIEFING = (
    f"Tumhara naam {NAME} hai. Tumhe {CREATOR} ne banaya hai, aur tum sirf unke hi "
    f"{ROLE} ho - kisi aur ke nahi. Tumhara kaam hai: {PURPOSE}. Tum kabhi ye nahi "
    f"kahoge ke tum {PRIMARY_USER} ke assistant nahi ho, aur na hi khud ko kisi doosri "
    f"company/model ka bataoge."
)

# Deliberately require the phrase to be paired with a question word ("kon",
# "kaun", "founder", "creator" etc.) rather than matching bare words like
# "founder" alone - that would false-positive on unrelated sentences (e.g.
# "Tesla ka founder Elon Musk hai") that have nothing to do with Fyz's own
# identity.
_CREATOR_PATTERNS = (
    "kisne banaya", "kis ne banaya", "tumhe banaya", "tumhein banaya",
    "tumhen banaya", "aapko banaya", "aap ko banaya",
    "tumhara founder", "aap ka founder", "tumhara creator", "aap ka creator",
    "founder kon", "founder kaun", "creator kon", "creator kaun",
    "banane wala kon", "banane wala kaun", "banaya kisne", "banaya kis ne",
    "who made you", "who created you", "who built you",
    "your founder", "your creator",
)

_OWNER_PATTERNS = (
    "kis ke assistant", "kiske assistant", "kis ka assistant",
    "kis ke ho", "kiske ho", "kis ka ho", "kiska ho",
    "whose assistant", "who do you work for", "you work for",
    "kis ke liye kaam",
)

_NAME_PATTERNS = (
    "tum kon ho", "tum kaun ho", "aap kon ho", "aap kaun ho",
    "tumhara naam", "tumhara naam kya", "aapka naam", "apna naam batao",
    "who are you", "what is your name", "your name",
)


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def get_identity_reply(text: str) -> Optional[str]:
    """Deterministic answer for identity questions (who are you / who made
    you / whose assistant are you) - bypasses the LLM entirely so this can
    never hallucinate or contradict itself, no matter what the underlying
    model's own training prior says about its own identity. Returns None if
    the text isn't recognized as an identity question, so callers fall
    through to the normal chat/intent pipeline."""
    norm = _normalize(text)

    if any(p in norm for p in _CREATOR_PATTERNS):
        return f"Mujhe {CREATOR} ne banaya hai bhai 😄"

    if any(p in norm for p in _OWNER_PATTERNS):
        return f"Main {PRIMARY_USER} ka personal AI companion hoon."

    if any(p in norm for p in _NAME_PATTERNS):
        return f"Main {NAME} hoon bhai 😄 tumhara local AI companion."

    return None
