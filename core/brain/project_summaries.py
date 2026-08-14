"""Short, casual one-line summaries for Fyz's personal-introduction feature -
deliberately shorter/more casual than the project registry's own
`description` field (written for technical registry lookups, not spoken
introductions). Only the most introduction-worthy projects are curated
here; anything else falls back to the registry's own description untouched,
so nothing about a project is ever invented."""

from typing import List

from tools.project_tools.registry import Project

NOTABLE_PROJECT_SUMMARIES = {
    "AI-Powered Healthcare Triage & Appointment System": (
        "AI-powered healthcare triage system jo symptoms assess karta hai aur appointments manage karta hai"
    ),
    "General Store Management System": (
        "Django-based store management ERP - inventory, sales aur accounting sab sambhalta hai"
    ),
    "FaizanMart": "Multi-vendor e-commerce platform, modern marketplace features ke saath",
}

# Keyword signal for filtering the registry down to "AI-flavored" projects
# when an introduction focuses on AI work specifically - matched against
# each project's own description/tech_stack, never a hardcoded project list,
# so this stays accurate as the registry grows.
_AI_KEYWORDS = ("ai", "ollama", "qwen", "triage", "face recognition", "computer vision", "machine learning")


def get_project_summary(project: Project) -> str:
    if project.name in NOTABLE_PROJECT_SUMMARIES:
        return NOTABLE_PROJECT_SUMMARIES[project.name]
    # Falls back to the registry's own description untouched (content-wise)
    # rather than invent a nicer-sounding one - just trims a trailing period
    # so it doesn't read oddly once wrapped in "(...)" by the introduction.
    return project.description.rstrip(".")


def filter_ai_projects(projects: List[Project]) -> List[Project]:
    return [
        p for p in projects
        if any(k in f"{p.description} {' '.join(p.tech_stack)}".lower() for k in _AI_KEYWORDS)
    ]


def filter_coding_projects(projects: List[Project]) -> List[Project]:
    return [
        p for p in projects
        if any(t.lower() in ("django", "python", "drf") for t in p.tech_stack)
    ]
