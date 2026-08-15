"""Smart local file/folder search (Brain v3.3): a persistent, typo-tolerant
index so "healtcare proect" still finds "AI-Powered Healthcare Triage &
Appointment System" without the caller needing the exact name.

Elasticsearch was considered and rejected (see the v3.3 final report) - a
permanently-running JVM service is a bad tradeoff on a 16GB machine already
running Ollama for what's ultimately a few thousand filenames, not a
document-search corpus. Instead: an on-disk SQLite table (memory/db.py's
`file_index`) as the persistent index, and rapidfuzz (a compiled C++
extension, no service, sub-millisecond per comparison) for the actual fuzzy
ranking - fast, typo-tolerant, and adds no idle memory footprint since it
only runs during an actual search/refresh call.

The expensive part is the filesystem walk (disk I/O), not the fuzzy match
over already-indexed names - so the walk is what's cached: an initial scan
builds the index once, searches reuse it, and only an explicit "files
refresh karo" (or an empty index) triggers a rescan."""

import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from rapidfuzz import fuzz, process

from core.config import FILE_INDEX_ROOTS
from memory.db import get_connection, init_db

MAX_INDEXED_ITEMS = 50_000
MIN_SCORE = 55  # below this, not worth surfacing as a "likely match"
TOP_K = 5

_SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".cache", "staticfiles"}


@dataclass
class FileMatch:
    name: str
    path: str
    type: str
    score: float


def default_roots() -> List[Path]:
    """Desktop/Documents/Downloads plus OneDrive's Desktop if present (this
    is where this user's real projects live, per the project registry) -
    deliberately NOT the whole drive. Overridable via FILE_INDEX_ROOTS."""
    if FILE_INDEX_ROOTS:
        return [Path(p) for p in FILE_INDEX_ROOTS if Path(p).exists()]

    home = Path.home()
    roots = []
    for name in ("Desktop", "Documents", "Downloads"):
        candidate = home / name
        if candidate.exists():
            roots.append(candidate)

    onedrive_desktop = home / "OneDrive" / "Desktop"
    if onedrive_desktop.exists() and onedrive_desktop not in roots:
        roots.append(onedrive_desktop)

    return roots


def _normalize(name: str) -> str:
    return re.sub(r"[\s_\-]+", " ", name.lower()).strip()


def _mtime(path: Path) -> str:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).isoformat()
    except OSError:
        return ""


def _scan(roots: List[Path]) -> List[tuple]:
    items = []
    scanned = 0
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")]

            for d in dirnames:
                full = Path(dirpath) / d
                items.append((d, _normalize(d), str(full), "dir", _mtime(full), str(root)))
                scanned += 1
                if scanned >= MAX_INDEXED_ITEMS:
                    return items

            for f in filenames:
                full = Path(dirpath) / f
                items.append((f, _normalize(f), str(full), "file", _mtime(full), str(root)))
                scanned += 1
                if scanned >= MAX_INDEXED_ITEMS:
                    return items

    return items


def refresh_file_index(roots: Optional[List[Path]] = None) -> int:
    """Full rescan + rebuild - the manual "files refresh karo" command.
    Returns the number of items indexed."""
    init_db()
    items = _scan(roots if roots is not None else default_roots())

    with get_connection() as conn:
        conn.execute("DELETE FROM file_index")
        conn.executemany(
            "INSERT INTO file_index (name, normalized_name, path, type, modified_time, root) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            items,
        )
    return len(items)


def _index_size() -> int:
    init_db()
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) AS c FROM file_index").fetchone()
    return row["c"]


def smart_search_files(query: str, top_k: int = TOP_K) -> List[FileMatch]:
    """Fuzzy, typo-tolerant search over the persistent index - builds it
    once automatically on first use (the "initial scan"), then reuses it
    until refresh_file_index() rebuilds it. Returns matches ranked
    best-first, score 0-100 (rapidfuzz's WRatio), already filtered to
    MIN_SCORE so a query with no reasonable match returns an empty list
    rather than forcing a low-confidence guess on the caller."""
    if not query or not query.strip():
        return []

    if _index_size() == 0:
        refresh_file_index()

    init_db()
    with get_connection() as conn:
        rows = conn.execute("SELECT name, normalized_name, path, type FROM file_index").fetchall()

    if not rows:
        return []

    # Names shorter than 4 chars (locale-code-style folders like "ar"/"ca"
    # from dependency trees, found via a real acceptance run, not assumed in
    # advance) spuriously score very high against WRatio's partial-match
    # bias on longer typo'd queries - e.g. "healtcare" matching "ar" at 90
    # because "ar" is a substring of "care". Excluding them from the fuzzy
    # candidate pool fixed this without hurting genuine matches, since real
    # target names in practice are always longer than 3 characters.
    choices = {i: row["normalized_name"] for i, row in enumerate(rows) if len(row["normalized_name"]) >= 4}
    if not choices:
        return []
    results = process.extract(_normalize(query), choices, scorer=fuzz.WRatio, limit=top_k)

    matches = []
    for _matched_text, score, idx in results:
        if score < MIN_SCORE:
            continue
        row = rows[idx]
        matches.append(FileMatch(name=row["name"], path=row["path"], type=row["type"], score=score))
    return matches
