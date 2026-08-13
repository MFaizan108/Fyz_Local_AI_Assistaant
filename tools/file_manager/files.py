import os
from pathlib import Path
from typing import List, Optional

MAX_RESULTS = 20
MAX_SCANNED = 20_000
MAX_READ_BYTES = 20_000

_SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".cache", "staticfiles"}


def _default_root() -> Path:
    onedrive_desktop = Path.home() / "OneDrive" / "Desktop"
    if onedrive_desktop.exists():
        return onedrive_desktop
    return Path.home() / "Desktop"


def search_files(query: str, root: Optional[str] = None) -> List[str]:
    query_lower = query.lower()
    base = Path(root) if root else _default_root()

    matches: List[str] = []
    scanned = 0

    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS and not d.startswith(".")]

        for filename in filenames:
            scanned += 1
            if query_lower in filename.lower():
                matches.append(str(Path(dirpath) / filename))
                if len(matches) >= MAX_RESULTS:
                    return matches
            if scanned >= MAX_SCANNED:
                return matches

    return matches


def read_file(path: str, max_bytes: int = MAX_READ_BYTES) -> str:
    file_path = Path(path)
    if not file_path.is_file():
        return f"File not found: {path}"

    try:
        data = file_path.read_bytes()
    except OSError as e:
        return f"Couldn't read {path}: {e}"

    truncated = len(data) > max_bytes
    text = data[:max_bytes].decode("utf-8", errors="replace")
    return text + "\n...[truncated]" if truncated else text


def delete_file(path: str) -> str:
    file_path = Path(path)
    if not file_path.is_file():
        return f"File not found: {path}"

    file_path.unlink()
    return f"Deleted {path}"
