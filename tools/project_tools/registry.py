import re
from dataclasses import dataclass
from typing import List, Optional

from memory.db import get_connection, init_db


@dataclass
class Project:
    id: int
    name: str
    aliases: List[str]
    path: str
    description: str
    tech_stack: List[str]

    @classmethod
    def from_row(cls, row) -> "Project":
        return cls(
            id=row["id"],
            name=row["name"],
            aliases=_split(row["aliases"]),
            path=row["path"],
            description=row["description"],
            tech_stack=_split(row["tech_stack"]),
        )


def _split(csv: str) -> List[str]:
    return [part.strip() for part in csv.split(",") if part.strip()]


def _join(items: List[str]) -> str:
    return ", ".join(items)


def add_project(
    name: str,
    path: str,
    aliases: Optional[List[str]] = None,
    description: str = "",
    tech_stack: Optional[List[str]] = None,
) -> None:
    init_db()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO projects (name, aliases, path, description, tech_stack) "
            "VALUES (?, ?, ?, ?, ?)",
            (name, _join(aliases or []), path, description, _join(tech_stack or [])),
        )


def list_projects() -> List[Project]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM projects").fetchall()
    return [Project.from_row(row) for row in rows]


DEFAULT_PROJECTS = [
    {
        "name": "AI-Powered Healthcare Triage & Appointment System",
        "aliases": ["healthcare project", "healthcare ai", "triage project", "triage system"],
        "path": r"C:\Users\pakcomp\OneDrive\Desktop\AI-Powered Healthcare Triage & Appointment System\main",
        "description": (
            "Django-based AI healthcare triage and appointment system with an "
            "ai_assistant app powered by Ollama and Qwen."
        ),
        "tech_stack": ["Django", "Ollama", "Qwen", "AI triage", "appointment system"],
    },
    {
        "name": "FaizanMart",
        "aliases": ["faizanmart", "faizan mart"],
        "path": r"C:\Users\pakcomp\OneDrive\Desktop\FaizanMart",
        "description": "Multi-vendor Django e-commerce platform.",
        "tech_stack": ["Django", "DRF", "Redis", "Elasticsearch"],
    },
]


def seed_default_projects() -> None:
    """Idempotent: only inserts projects whose path isn't already registered."""
    existing_paths = {p.path for p in list_projects()}
    for entry in DEFAULT_PROJECTS:
        if entry["path"] in existing_paths:
            continue
        add_project(
            name=entry["name"],
            path=entry["path"],
            aliases=entry["aliases"],
            description=entry["description"],
            tech_stack=entry["tech_stack"],
        )


_STOPWORDS = {
    "project", "projects", "app", "application", "system", "the", "a", "an",
    "my", "mera", "meri", "wala", "waala", "jismein", "jisme", "use", "kiya",
    "tha", "khol", "kholo", "open", "wo", "woh", "us", "usme", "usmein",
    "with", "and", "in", "it", "one", "for", "of", "to", "on", "by", "that",
    "was", "is", "aur",
}


def find_project(hint: str) -> Optional[Project]:
    """Score every known project against the free-text hint and return the
    best match, or None if nothing scores above zero. Generic filler words
    (like "project") are excluded so they can't manufacture a false match."""
    hint_words = set(re.findall(r"[a-z0-9]+", hint.lower())) - _STOPWORDS
    if not hint_words:
        return None

    best_project: Optional[Project] = None
    best_score = 0

    for project in list_projects():
        haystack = " ".join(
            [project.name, _join(project.aliases), project.description, _join(project.tech_stack)]
        ).lower()
        score = sum(1 for word in hint_words if word in haystack)
        if score > best_score:
            best_score = score
            best_project = project

    return best_project
