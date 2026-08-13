import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path

from core.security.protected_paths import is_protected_path
from llm.ollama_client import chat

FYZ_ROOT = Path(__file__).resolve().parents[2]
EXPERIMENTS_DIR = FYZ_ROOT / "workspace" / "experiments"

CODE_CHANGE_SYSTEM_PROMPT = """You are Fyz's self-improvement code assistant. You will be \
given the full current contents of one existing file and a task describing what to change \
about it. Reply with ONLY the complete new contents of the file after the change - no \
explanation, no markdown code fences, no diff syntax, no commentary. Just the raw file \
content that should replace the old one, preserving everything about the file that the task \
doesn't ask you to change."""


@dataclass
class Experiment:
    branch: str
    worktree_path: Path
    target_file: str
    diff: str
    test_output: str
    tests_passed: bool


class SandboxError(Exception):
    pass


def _run_git(args: list, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=30
    )


def _resolve_project_file(rel_path: str) -> Path:
    """Resolves a path the user/LLM gave us against FYZ_ROOT, refusing
    anything that escapes the project root (e.g. via "..") - this file path
    is attacker-adjacent input (LLM-extracted from free text), so it gets
    the same treatment as any other untrusted path."""
    resolved = (FYZ_ROOT / rel_path).resolve()
    try:
        resolved.relative_to(FYZ_ROOT.resolve())
    except ValueError:
        raise SandboxError(f"'{rel_path}' resolves outside the Fyz project - refusing.")
    return resolved


def propose_change(target_file_rel: str, task_description: str) -> Experiment:
    """Creates an isolated git worktree on a throwaway branch, asks the LLM
    to rewrite ONE file per task_description, commits that single change on
    the branch, runs the project's test suite against it, and returns
    everything needed to show the user a diff + test results before any
    merge decision is made. Never touches the real working tree."""
    target_file_abs = _resolve_project_file(target_file_rel)

    if is_protected_path(str(target_file_abs), str(FYZ_ROOT)):
        raise SandboxError(f"'{target_file_rel}' is protected and can't be self-modified.")

    if not target_file_abs.is_file():
        raise SandboxError(f"'{target_file_rel}' doesn't exist in the Fyz project.")

    original_code = target_file_abs.read_text(encoding="utf-8")

    branch = f"fyz-experiment-{uuid.uuid4().hex[:8]}"
    worktree_path = EXPERIMENTS_DIR / branch
    EXPERIMENTS_DIR.mkdir(parents=True, exist_ok=True)

    add_result = _run_git(["worktree", "add", "-b", branch, str(worktree_path)], cwd=FYZ_ROOT)
    if add_result.returncode != 0:
        raise SandboxError(f"Couldn't create experiment worktree: {add_result.stderr.strip()}")

    try:
        prompt = f"Task: {task_description}\n\nCurrent contents of {target_file_rel}:\n\n{original_code}"
        new_code = chat(prompt, system=CODE_CHANGE_SYSTEM_PROMPT, timeout=90.0)
        if not new_code.endswith("\n"):
            new_code += "\n"

        worktree_target = worktree_path / target_file_rel
        worktree_target.write_text(new_code, encoding="utf-8")

        diff_result = _run_git(["diff", "--", target_file_rel], cwd=worktree_path)
        diff = diff_result.stdout

        if diff.strip():
            _run_git(["add", target_file_rel], cwd=worktree_path)
            _run_git(["commit", "-m", f"Fyz experiment: {task_description}"], cwd=worktree_path)

        venv_python = FYZ_ROOT / ".venv" / "Scripts" / "python.exe"
        python_exe = str(venv_python) if venv_python.is_file() else "python"
        test_result = subprocess.run(
            [python_exe, "-m", "pytest", "-q"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=120,
        )
        tests_passed = test_result.returncode == 0
        test_output = (test_result.stdout + test_result.stderr).strip()
        test_tail = "\n".join(test_output.splitlines()[-15:])

        return Experiment(
            branch=branch,
            worktree_path=worktree_path,
            target_file=target_file_rel,
            diff=diff,
            test_output=test_tail,
            tests_passed=tests_passed,
        )
    except Exception:
        cleanup_experiment_by_branch(branch, worktree_path)
        raise


def merge_experiment(experiment: Experiment) -> str:
    result = _run_git(["merge", "--no-ff", experiment.branch], cwd=FYZ_ROOT)
    cleanup_experiment(experiment)
    if result.returncode != 0:
        return f"Merge failed: {result.stderr.strip()}"
    return f"Merged '{experiment.branch}' into the main branch."


def cleanup_experiment(experiment: Experiment) -> None:
    cleanup_experiment_by_branch(experiment.branch, experiment.worktree_path)


def cleanup_experiment_by_branch(branch: str, worktree_path: Path) -> None:
    _run_git(["worktree", "remove", "--force", str(worktree_path)], cwd=FYZ_ROOT)
    _run_git(["branch", "-D", branch], cwd=FYZ_ROOT)
