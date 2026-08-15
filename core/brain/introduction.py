"""Builds Fyz's introduction of Muhammad Faizan Ur Rahman for someone else
in the room. Deterministic templates over centralized profile + project
registry data - NOT another LLM call - so this can never invent facts about
Faizan or his projects, and stays fast/reliable. Tone and length adapt to
who's listening (audience) and what was asked (focus, level), per the
"introduce_user" intent classified in core/brain/prompts.py."""

import re

from core.brain.identity import BRAND
from core.brain.project_summaries import filter_ai_projects, filter_coding_projects, get_project_summary
from core.brain.user_profile import EDUCATION, FULL_NAME, PREFERRED_NAME, ROLE_FOCUS
from tools.project_tools.registry import list_projects

# Explicit third-party-audience cues from the v3.3 spec, plus their obvious
# variants - checked before the deterministic identity/profile fast paths in
# core/action_executor/dispatch.py so a message like "meray bhai ko mera
# batao main kon hoon?" is never hijacked by the bare "main kon hoon"
# substring match. Bug found from a real report: the fast paths matched
# ANYWHERE in the message, so an introduction request that happened to
# contain "main kon hoon" as a trailing clarifier got answered as a plain
# identity question instead of routed to introduce_user.
#
# Two shapes are covered: an explicit relation word + "ko" ("bhai ko",
# "cousin ko", "kisi ko"...), and a third-person object pronoun ("usko",
# "unko"...) paired with a "tell them" word anywhere in the message (these
# pronouns already encode "ko" as a suffix, e.g. "unko mere projects ke bare
# mein batao" has no standalone "ko" token to match against the first shape).
_RELATION_KO_RE = re.compile(
    r"\b(bhai|dost|friend|cousin|abu|walid|father|ammi|behen|sister|brother|kisi)\s+ko\b"
)
_THIRD_PARTY_PRONOUNS = ("usko", "unko", "isko", "unhein", "unhe", " use ", " ise ")
_TELL_WORDS = ("batao", "bata do", "bata den", "bata dena", "introduction")


def looks_like_introduction_request(text: str) -> bool:
    """True if the message is clearly asking Fyz to describe Faizan to
    someone ELSE present, regardless of what else it contains - callers use
    this to skip the direct identity/profile fast paths (which are only for
    the user asking about themselves) and fall through to full intent
    classification, where introduce_user can be classified correctly."""
    norm = f" {' '.join(text.lower().split())} "

    if _RELATION_KO_RE.search(norm):
        return True

    has_third_party_pronoun = any(p in norm for p in _THIRD_PARTY_PRONOUNS)
    has_tell_word = any(t in norm for t in _TELL_WORDS)
    return has_third_party_pronoun and has_tell_word

# Verb-phrase fragments (no subject/trailing punctuation) so templates can
# drop them into a sentence that already established the subject, without
# repeating "Faizan"/"hain" awkwardly.
_FOCUS_LINES = {
    "coding": "Python aur Django mein backend development karte hain",
    "ai_projects": "AI aur machine learning projects par kaam karte hain",
}


def _focus_line(focus: str, level: str) -> str:
    if focus in _FOCUS_LINES:
        return _FOCUS_LINES[focus]
    roles = ROLE_FOCUS if level == "detailed" else ROLE_FOCUS[:3]
    return f"{', '.join(roles)} hain"


def _relevant_projects(focus: str, limit: int):
    projects = list_projects()
    if focus == "ai_projects":
        projects = filter_ai_projects(projects)
    elif focus == "coding":
        projects = filter_coding_projects(projects)
    return projects[:limit]


def _project_line(focus: str, level: str) -> str:
    if focus == "coding" and level != "detailed":
        return ""  # coding focus is already covered by the focus line itself, unless more detail was asked for

    limit = 1 if level == "short" else (3 if level == "detailed" else 2)
    projects = _relevant_projects(focus, limit)
    if not projects:
        return ""

    summaries = [f"{p.name} ({get_project_summary(p)})" for p in projects]
    if level == "short":
        return f" Abhi {summaries[0]} par kaam kar rahe hain."
    return " Inke projects mein " + ", ".join(summaries) + " shamil hain."


def build_introduction(audience: str = "generic", focus: str = "general", level: str = "medium") -> str:
    audience = (audience or "generic").strip().lower()
    focus = (focus or "general").strip().lower()
    level = (level or "medium").strip().lower()

    focus_line = _focus_line(focus, level)
    project_line = _project_line(focus, level)

    # A short intro that's specifically about projects should lead with the
    # actual project, not a generic role blurb that ignores what was asked -
    # "mere projects short mein batao" must answer with a project, not a
    # copy of the generic "who is Faizan" short intro.
    project_focused_short = level == "short" and focus in ("projects", "ai_projects") and project_line

    if audience == "father":
        # Respectful, warm, no slang, minimal emoji per the spec's explicit
        # tone guidance for this audience.
        if project_focused_short:
            return f"{PREFERRED_NAME},{project_line}"
        if level == "short":
            return f"{FULL_NAME}, yaani {PREFERRED_NAME}, {EDUCATION} hain aur {focus_line}."
        return (
            f"{FULL_NAME}, yaani {PREFERRED_NAME}, {EDUCATION} hain. Yeh {focus_line}, "
            f"aur {BRAND} ke naam se apne software projects develop kar rahe hain.{project_line}"
        )

    # friend / cousin / generic - casual, friendly, an occasional emoji
    # (not one in every sentence, per the "don't overuse emojis" rule).
    if project_focused_short:
        return f"Bhai,{project_line}"
    if level == "short":
        return f"Bhai, yeh {PREFERRED_NAME} hain 😄 {EDUCATION} hain aur {focus_line}."

    return (
        f"Bhai, yeh {FULL_NAME} hain, lekin hum inhein {PREFERRED_NAME} kehte hain. "
        f"{EDUCATION} hain aur {focus_line}. {BRAND} ke naam se apne software aur AI "
        f"projects bhi build kar rahe hain.{project_line}"
    )
