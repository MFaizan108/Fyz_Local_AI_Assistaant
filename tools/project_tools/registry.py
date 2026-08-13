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
    {
        "name": "TaskFlow",
        "aliases": ["taskflow", "project management tool", "task management tool"],
        "path": r"C:\Users\pakcomp\OneDrive\Desktop\Project Management Tool",
        "description": (
            "Full-stack collaborative project management tool (Trello/Asana/Linear-style) - "
            "Kanban boards, tasks, comments, notifications, activity feeds."
        ),
        "tech_stack": ["Django", "DRF", "django-cors-headers"],
    },
    {
        "name": "Social Media Platform",
        "aliases": ["social media platform", "mini social app", "codealpha mini social app"],
        "path": r"C:\Users\pakcomp\OneDrive\Desktop\Social Media Platform",
        "description": "Django social media app with posts, accounts, and media uploads.",
        "tech_stack": ["Django", "PostgreSQL", "Pillow"],
    },
    {
        "name": "General Store Management System",
        "aliases": ["gsms", "general store management system", "store management system"],
        "path": r"C:\Users\pakcomp\OneDrive\Desktop\GSMS_Django_Project\gsms",
        "description": (
            "Django-based mini-ERP for a general store: inventory, suppliers/customers, "
            "purchases/sales, PDF invoicing, a double-entry finance ledger, reports, "
            "role-based login."
        ),
        "tech_stack": ["Django", "ERP", "inventory management"],
    },
    {
        "name": "Midasbuy Automation",
        "aliases": ["midasbuy", "midasbuy automation", "midasbuy links automation"],
        "path": r"C:\Users\pakcomp\OneDrive\Desktop\Midasbuy_Automation",
        "description": "Django + Playwright automation tool for Midasbuy links.",
        "tech_stack": ["Django", "Playwright", "automation"],
    },
    {
        "name": "Portfolio Website",
        "aliases": ["portfolio", "my portfolio", "portfolio website"],
        "path": r"C:\Users\pakcomp\OneDrive\Desktop\portfolio",
        "description": "Personal Django portfolio website, deployable to Heroku, with a GitHub Pages static export.",
        "tech_stack": ["Django", "Gunicorn", "Cloudinary"],
    },
    {
        "name": "Flashcard Quiz App",
        "aliases": ["flashcard", "flashcards", "flashcard quiz", "flashcard quiz app"],
        "path": r"C:\Users\pakcomp\OneDrive\Desktop\FlashCard",
        "description": (
            "Django flashcard study app - flip cards to reveal answers, categorize, "
            "search/filter, full CRUD."
        ),
        "tech_stack": ["Django"],
    },
    {
        "name": "Random Quote Generator",
        "aliases": ["random quote generator", "quote generator", "codealpha quote generator"],
        "path": r"C:\Users\pakcomp\OneDrive\Desktop\CodeAlpha\Random_Quote_Generator",
        "description": "Simple Django random quote generator built during the CodeAlpha internship.",
        "tech_stack": ["Django"],
    },
    {
        "name": "Birchfields Dental Care Redesign",
        "aliases": ["birchfields", "birchfields dental", "birchfields dentle care"],
        "path": r"C:\Users\pakcomp\OneDrive\Desktop\Web_Clients\BirchFields_Dentle_Care",
        "description": (
            "Independent, unofficial redesign concept website for Birchfields Family "
            "Dental Care - static HTML/CSS/JS, no backend."
        ),
        "tech_stack": ["HTML", "CSS", "JavaScript"],
    },
    {
        "name": "Church Lane Dental Practice Redesign",
        "aliases": ["church lane", "church lane dental", "church lane dental practice"],
        "path": r"C:\Users\pakcomp\OneDrive\Desktop\Web_Clients\Church Lane Dental Practice",
        "description": (
            "Independent, unofficial redesign concept website for Church Lane Dental "
            "Practice - static HTML/CSS/JS, no backend."
        ),
        "tech_stack": ["HTML", "CSS", "JavaScript"],
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
