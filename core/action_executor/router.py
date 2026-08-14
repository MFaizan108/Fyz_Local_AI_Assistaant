import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Tuple

from core.brain.context import ConversationContext
from core.brain.introduction import build_introduction
from core.brain.schemas import Intent
from core.permissions.levels import PermissionLevel
from core.self_improve.sandbox import SandboxError, cleanup_experiment, merge_experiment, propose_change
from memory.action_log import recent_actions
from memory.long_term import MemoryCategory, list_memories, save_memory, semantic_search_memories
from tools.app_control.apps import open_app, open_path_in_vscode
from tools.app_control.browser_profiles import open_chrome_profile
from tools.file_manager.files import delete_file, read_file, search_files
from tools.project_tools.dev_tools import git_status, run_tests
from tools.project_tools.registry import Project, find_project
from tools.system_tools.process import kill_process, list_processes
from tools.system_tools.screenshot import take_screenshot
from tools.system_tools.system_info import get_system_info

_PRONOUN_WORDS = {
    "iska", "iski", "isko", "iske", "uska", "uski", "usko", "uske", "ye",
    "yeh", "woh", "wo", "us", "wala", "wali", "is", "it", "this", "that",
}
_YES_WORDS = {"y", "yes", "haan", "han", "ji", "ji haan"}

ConfirmPrompt = Callable[[str], str]


@dataclass
class ToolEntry:
    func: Callable[[Intent, Optional[ConversationContext], ConfirmPrompt], str]
    level: PermissionLevel
    description: str


def _resolve_project(
    hint: Optional[str], context: Optional[ConversationContext]
) -> Tuple[Optional[Project], Optional[str]]:
    """Shared by every intent that operates on 'a project' (open/git-status/
    run-tests): falls back to context.last_project when there's no hint, or
    when the hint is purely a pronoun reference find_project couldn't match."""
    if not hint and context and context.last_project:
        hint = context.last_project

    if not hint:
        return None, None

    project = find_project(hint)

    if project is None and context and context.last_project:
        hint_words = set(re.findall(r"[a-z0-9]+", hint.lower()))
        if hint_words and hint_words <= _PRONOUN_WORDS:
            project = find_project(context.last_project)

    return project, hint


def _handle_open_app(intent: Intent, context: Optional[ConversationContext], confirm_prompt: ConfirmPrompt) -> str:
    if not intent.target:
        return "Kaunsi app kholni hai bhai?"

    key = intent.target.strip().lower()
    result = open_app(intent.target)
    if result.startswith("I don't know how to open"):
        return f"'{intent.target}' kholna abhi mujhe nahi aata bhai."
    return f"{key.capitalize()} khol raha hoon bhai 😄"


def _handle_open_project(intent: Intent, context: Optional[ConversationContext], confirm_prompt: ConfirmPrompt) -> str:
    project, hint = _resolve_project(intent.target, context)
    if not hint:
        return "Konsa project kholna hai bhai?"
    if project is None:
        return f"Mujhe '{hint}' naam ka koi project nahi mila."

    if context:
        context.last_project = project.name

    open_path_in_vscode(project.path)
    return f"Ji bhai, {project.name} khol raha hoon VS Code mein."


def _handle_git_status(intent: Intent, context: Optional[ConversationContext], confirm_prompt: ConfirmPrompt) -> str:
    project, hint = _resolve_project(intent.target, context)
    if not hint:
        return "Which project's git status do you want?"
    if project is None:
        return f"I couldn't find a project matching '{hint}'."

    if context:
        context.last_project = project.name

    return git_status(project.path)


def _handle_run_tests(intent: Intent, context: Optional[ConversationContext], confirm_prompt: ConfirmPrompt) -> str:
    project, hint = _resolve_project(intent.target, context)
    if not hint:
        return "Which project should I run tests in?"
    if project is None:
        return f"I couldn't find a project matching '{hint}'."

    if context:
        context.last_project = project.name

    return run_tests(project.path)


def _handle_project_info(intent: Intent, context: Optional[ConversationContext], confirm_prompt: ConfirmPrompt) -> str:
    """"Healthcare project kya karta hai?" etc - answers straight from the
    project registry's own description/tech_stack fields, never from the
    LLM guessing, so this can never hallucinate what a project does."""
    project, hint = _resolve_project(intent.target, context)
    if not hint:
        return "Konse project ke bare mein puchna hai bhai?"
    if project is None:
        return f"Mujhe '{hint}' naam ka koi project nahi mila."

    if context:
        context.last_project = project.name

    parts = [project.name]
    if project.description:
        parts.append(project.description)
    if project.tech_stack:
        parts.append(f"Tech stack: {', '.join(project.tech_stack)}")
    return " - ".join(parts)


def _handle_current_project_query(
    intent: Intent, context: Optional[ConversationContext], confirm_prompt: ConfirmPrompt
) -> str:
    """"Main kis project par kaam kar raha hoon?" / "hamara latest project
    konsa hai?" - uses structured state (context.last_project), falling
    back to the most recent successfully-opened project in the audit log,
    never a guess. If neither is known, asks naturally instead of picking
    one at random."""
    if context and context.last_project:
        return f"Abhi tum {context.last_project} par kaam kar rahe ho bhai."

    for action in recent_actions(limit=20):
        if action.intent == "open_project" and action.executed and action.target:
            return f"Sabse recent project jo khola tha wo hai: {action.target}."

    return "Bhai tumhare paas kuch projects hain 😄 kis wale ki baat kar rahe ho?"


def _handle_introduce_user(intent: Intent, context: Optional[ConversationContext], confirm_prompt: ConfirmPrompt) -> str:
    """"Mere dost ko mere bare mein batao" etc - built deterministically from
    centralized profile data + the project registry (build_introduction()),
    never a fresh LLM generation, so Fyz can never invent facts/projects
    about Faizan when introducing him to someone else."""
    params = intent.params or {}
    return build_introduction(
        audience=params.get("audience", "generic"),
        focus=params.get("focus", "general"),
        level=params.get("level", "medium"),
    )


def _handle_open_browser(intent: Intent, context: Optional[ConversationContext], confirm_prompt: ConfirmPrompt) -> str:
    """Opens Chrome directly into a specific profile in one step (no
    separate "open chrome" then "switch profile" actions, which would open
    two windows) - profile resolution never guesses a directory, it's
    matched against the real profiles Chrome itself reports."""
    browser = (intent.target or "chrome").strip().lower()
    if browser != "chrome":
        return f"'{browser}' abhi supported nahi hai bhai, sirf Chrome."

    profile_hint = (intent.params or {}).get("profile")
    if not profile_hint:
        open_app("chrome")
        return "Chrome khol raha hoon bhai 😄"

    result = open_chrome_profile(profile_hint)
    if context and "khol raha hoon" in result:
        context.active_browser_profile = profile_hint
    return result


def _handle_get_system_info(intent: Intent, context: Optional[ConversationContext], confirm_prompt: ConfirmPrompt) -> str:
    return get_system_info()


def _handle_take_screenshot(intent: Intent, context: Optional[ConversationContext], confirm_prompt: ConfirmPrompt) -> str:
    return take_screenshot()


def _handle_remember(intent: Intent, context: Optional[ConversationContext], confirm_prompt: ConfirmPrompt) -> str:
    if not intent.target:
        return "Kya yaad rakhna hai, bata do."

    category_str = (intent.params or {}).get("category", "context")
    try:
        category = MemoryCategory(category_str)
    except ValueError:
        category = MemoryCategory.CONTEXT

    save_memory(category, intent.target)
    return f"Yaad rakh liya ({category.value}): {intent.target}"


def _handle_recall(intent: Intent, context: Optional[ConversationContext], confirm_prompt: ConfirmPrompt) -> str:
    if intent.target:
        memories = semantic_search_memories(intent.target, top_k=5)
    else:
        memories = list_memories()[:5]

    if not memories:
        return "Mujhe is baare mein kuch yaad nahi."

    lines = [f"- ({m.category}) {m.content}" for m in memories]
    return "Yeh yaad hai:\n" + "\n".join(lines)


def _handle_search_files(intent: Intent, context: Optional[ConversationContext], confirm_prompt: ConfirmPrompt) -> str:
    if not intent.target:
        return "What file are you looking for?"

    root = (intent.params or {}).get("root")
    results = search_files(intent.target, root)
    if not results:
        return f"No files found matching '{intent.target}'."

    return "Found:\n" + "\n".join(results)


def _handle_read_file(intent: Intent, context: Optional[ConversationContext], confirm_prompt: ConfirmPrompt) -> str:
    if not intent.target:
        return "Which file should I read?"

    target = intent.target
    if not Path(target).is_file():
        matches = search_files(target)
        if not matches:
            return f"Couldn't find a file matching '{target}'."
        target = matches[0]

    return read_file(target)


def _handle_delete_file(intent: Intent, context: Optional[ConversationContext], confirm_prompt: ConfirmPrompt) -> str:
    if not intent.target:
        return "Which file should I delete?"

    if not Path(intent.target).is_file():
        return f"'{intent.target}' doesn't look like an existing file path - give me the full path to be safe."

    return delete_file(intent.target)


def _handle_list_processes(intent: Intent, context: Optional[ConversationContext], confirm_prompt: ConfirmPrompt) -> str:
    return list_processes()


def _handle_kill_process(intent: Intent, context: Optional[ConversationContext], confirm_prompt: ConfirmPrompt) -> str:
    if not intent.target:
        return "Which process should I kill?"
    return kill_process(intent.target)


def _handle_propose_improvement(
    intent: Intent, context: Optional[ConversationContext], confirm_prompt: ConfirmPrompt
) -> str:
    """The self-improvement loop end-to-end, gated twice: dispatch's outer
    DANGEROUS gate gets this handler called at all, then this handler asks
    a SECOND time (via the same confirm_prompt) before merging anything
    into the real codebase - a diff and test results are shown first."""
    params = intent.params or {}
    target_file = params.get("file")

    if not intent.target:
        return "Kya improve karna hai, bata do."
    if not target_file:
        return "Mujhe exact file path chahiye (Fyz project ke andar, relative) improve karne ke liye."

    try:
        experiment = propose_change(target_file, intent.target)
    except SandboxError as e:
        return str(e)

    summary = (
        f"Experiment branch '{experiment.branch}' bana diya.\n\n"
        f"Diff:\n{experiment.diff or '(no changes produced)'}\n\n"
        f"Tests {'PASSED' if experiment.tests_passed else 'FAILED'}:\n{experiment.test_output}\n"
    )

    if not experiment.diff.strip():
        cleanup_experiment(experiment)
        return summary + "\nKoi change nahi bana, cleanup kar diya."

    if not experiment.tests_passed:
        answer = confirm_prompt(
            summary + "\nTests fail ho rahe hain - phir bhi review ke liye experiment rakhna hai? [y/n] "
        )
        if answer.strip().lower() not in _YES_WORDS:
            cleanup_experiment(experiment)
            return "Theek hai, experiment discard kar diya."
        return summary + f"\nExperiment '{experiment.branch}' rakha hua hai lekin merge nahi kiya - tests fail ho rahe the."

    answer = confirm_prompt(summary + "\nMerge kar doon? Type 'confirm' to merge: ")
    if answer.strip().lower() == "confirm":
        merge_result = merge_experiment(experiment)
        return summary + "\n" + merge_result

    cleanup_experiment(experiment)
    return summary + "\nTheek hai, merge nahi kiya - experiment discard kar diya."


TOOL_REGISTRY: dict[str, ToolEntry] = {
    "open_app": ToolEntry(_handle_open_app, PermissionLevel.SAFE, "Open an application"),
    "open_project": ToolEntry(_handle_open_project, PermissionLevel.SAFE, "Open a known project"),
    "project_info": ToolEntry(_handle_project_info, PermissionLevel.SAFE, "Describe what a known project does"),
    "current_project_query": ToolEntry(
        _handle_current_project_query, PermissionLevel.SAFE, "Answer which project is currently active"
    ),
    "open_browser": ToolEntry(_handle_open_browser, PermissionLevel.SAFE, "Open a browser, optionally with a specific profile"),
    "introduce_user": ToolEntry(_handle_introduce_user, PermissionLevel.SAFE, "Introduce Faizan to someone else in the room"),
    "get_system_info": ToolEntry(_handle_get_system_info, PermissionLevel.SAFE, "Report system info"),
    "take_screenshot": ToolEntry(_handle_take_screenshot, PermissionLevel.SAFE, "Take a screenshot"),
    "remember": ToolEntry(_handle_remember, PermissionLevel.CONFIRM, "Save something to long-term memory"),
    "recall": ToolEntry(_handle_recall, PermissionLevel.SAFE, "Recall something from long-term memory"),
    "search_files": ToolEntry(_handle_search_files, PermissionLevel.SAFE, "Search for a file by name"),
    "read_file": ToolEntry(_handle_read_file, PermissionLevel.SAFE, "Read a file's contents"),
    "delete_file": ToolEntry(_handle_delete_file, PermissionLevel.DANGEROUS, "Permanently delete a file"),
    "list_processes": ToolEntry(_handle_list_processes, PermissionLevel.SAFE, "List running processes"),
    "kill_process": ToolEntry(_handle_kill_process, PermissionLevel.DANGEROUS, "Force-kill a running process"),
    "git_status": ToolEntry(_handle_git_status, PermissionLevel.SAFE, "Show git status for a project"),
    "run_tests": ToolEntry(_handle_run_tests, PermissionLevel.SAFE, "Run a project's test suite"),
    "propose_improvement": ToolEntry(
        _handle_propose_improvement,
        PermissionLevel.DANGEROUS,
        "Propose and test a code change to Fyz's own codebase in an isolated branch",
    ),
}


def route(
    intent: Intent,
    context: Optional[ConversationContext] = None,
    confirm_prompt: ConfirmPrompt = input,
) -> Optional[str]:
    """Execute the tool for an intent. Returns None for 'chat' (caller should
    fall through to conversation handling)."""
    if intent.intent == "chat":
        return None

    entry = TOOL_REGISTRY.get(intent.intent)
    if entry is None:
        return f"I don't have a tool for '{intent.intent}' yet."

    return entry.func(intent, context, confirm_prompt)


def get_permission_level(intent_name: str) -> Optional[PermissionLevel]:
    entry = TOOL_REGISTRY.get(intent_name)
    return entry.level if entry else None
