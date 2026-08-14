"""Centralized profile of Fyz's primary user - the counterpart to
core/brain/identity.py (which is about who FYZ is). Deliberately kept as a
separate small deterministic layer rather than dumped into every prompt, so
"mera naam kya hai?"-style questions are answered reliably without
depending on the LLM to have retained or correctly recalled it."""

from typing import Optional

from core.brain.identity import BRAND, CREATOR

FULL_NAME = CREATOR  # "Muhammad Faizan Ur Rahman" - single source of truth stays in identity.py
PREFERRED_NAME = "Faizan"
ROLE = "Primary user"
RELATIONSHIP = "Fyz's creator aur primary user"

# Used by core/brain/introduction.py to build FYZ's introductions of Faizan
# to other people - kept here alongside the rest of the user's profile data
# so it's one place to update, not scattered across templates.
EDUCATION = "BS Artificial Intelligence student"
ROLE_FOCUS = ["Backend Developer", "Python Developer", "Django Developer", "AI Enthusiast"]


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


_NAME_PATTERNS = (
    "mera naam kya hai", "mera naam kya", "mera naam batao",
    "what is my name", "what's my name", "my name",
)

_WHO_AM_I_PATTERNS = (
    "main kon hoon", "main kaun hoon", "mai kon hoon", "mai kaun hoon",
    "who am i",
)


def get_profile_reply(text: str) -> Optional[str]:
    """Deterministic answer for questions about the user themselves (not
    about Fyz) - "what's my name", "who am I". Returns None if the text
    isn't recognized as one of these, so callers fall through to the normal
    chat/intent pipeline."""
    norm = _normalize(text)

    if any(p in norm for p in _WHO_AM_I_PATTERNS):
        return f"Tum {FULL_NAME} ho bhai 😄 aur main tumhara personal AI companion hoon."

    if any(p in norm for p in _NAME_PATTERNS):
        return f"Tumhara naam {FULL_NAME} hai bhai 😄"

    return None
