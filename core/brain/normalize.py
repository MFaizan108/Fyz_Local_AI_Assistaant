import re
from difflib import get_close_matches

from tools.project_tools.registry import list_projects

_STATIC_TERMS = [
    "chrome", "vscode", "code", "explorer", "notepad",
    "Django", "Ollama", "Qwen", "DRF", "Redis", "Elasticsearch", "FaizanMart",
]

_WORD_RE = re.compile(r"[A-Za-z]+")


def _known_terms() -> list:
    terms = list(_STATIC_TERMS)
    for project in list_projects():
        terms.append(project.name)
        terms.extend(project.aliases)
        terms.extend(project.tech_stack)
    return terms


def normalize_text(text: str) -> str:
    """Collapse whitespace and correct near-miss spellings of known app/
    project/tech names (the kind of drift speech-to-text or typos introduce)
    back to their canonical form, so downstream exact-match lookups (like
    tools/app_control/apps.py's command dict) don't silently fail."""
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return text

    # First occurrence wins, so canonical names (_STATIC_TERMS, project.name)
    # take priority over lowercase aliases that would otherwise clobber them.
    terms_by_lower: dict = {}
    for term in _known_terms():
        terms_by_lower.setdefault(term.lower(), term)

    def fix_word(match: re.Match) -> str:
        word = match.group(0)
        lower = word.lower()
        if lower in terms_by_lower:
            return terms_by_lower[lower]

        close = get_close_matches(lower, terms_by_lower.keys(), n=1, cutoff=0.8)
        if close:
            return terms_by_lower[close[0]]

        return word

    return _WORD_RE.sub(fix_word, text)
