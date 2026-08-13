from pathlib import Path

# Fyz must never be able to modify its own safety rails. Enforced here so
# every caller (currently just the self-improvement sandbox) shares one
# definition instead of each re-deciding what's off-limits.
PROTECTED_DIRS = ["core/security", "core/permissions"]


def is_protected_path(path: str, project_root: str) -> bool:
    try:
        rel = Path(path).resolve().relative_to(Path(project_root).resolve())
    except ValueError:
        return False  # outside project_root entirely - not this function's job to flag that

    rel_str = str(rel).replace("\\", "/")
    return any(rel_str == d or rel_str.startswith(d + "/") for d in PROTECTED_DIRS)
