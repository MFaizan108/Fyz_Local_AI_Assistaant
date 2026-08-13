import subprocess
from pathlib import Path


def _resolve_python(path: str) -> str:
    """Prefer the target project's own .venv interpreter over whatever
    `python` resolves to on PATH, so tests actually run with that project's
    installed dependencies instead of failing with import errors."""
    venv_python = Path(path) / ".venv" / "Scripts" / "python.exe"
    if venv_python.is_file():
        return str(venv_python)
    return "python"


def git_status(path: str) -> str:
    try:
        result = subprocess.run(
            ["git", "status", "--short", "--branch"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except FileNotFoundError:
        return "Git isn't available on this system."
    except OSError as e:
        return f"Couldn't run git status in {path}: {e}"

    if result.returncode != 0:
        return f"'{path}' doesn't look like a git repo, or git failed:\n{result.stderr.strip()}"

    output = result.stdout.strip()
    return output if output else "Working tree clean, nothing to report."


def run_tests(path: str) -> str:
    """Runs `python -m pytest` in the target project's directory, using that
    project's own .venv interpreter when one exists (see _resolve_python) so
    it runs against the right dependencies instead of the system Python."""
    try:
        result = subprocess.run(
            [_resolve_python(path), "-m", "pytest", "-q"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except FileNotFoundError:
        return "Couldn't find Python to run tests with."
    except subprocess.TimeoutExpired:
        return "Tests timed out after 120s."

    output = (result.stdout + result.stderr).strip()
    tail = "\n".join(output.splitlines()[-15:])
    return tail or "No test output."
