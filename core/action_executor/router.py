import re
from dataclasses import dataclass
from typing import Callable, Optional

from core.brain.context import ConversationContext
from core.brain.schemas import Intent
from core.permissions.levels import PermissionLevel
from memory.long_term import MemoryCategory, save_memory, search_memories
from tools.app_control.apps import open_app, open_path_in_vscode
from tools.project_tools.registry import find_project
from tools.system_tools.screenshot import take_screenshot
from tools.system_tools.system_info import get_system_info

_PRONOUN_WORDS = {
    "iska", "iski", "isko", "iske", "uska", "uski", "usko", "ye", "yeh",
    "woh", "wo", "is", "it", "this", "that",
}


@dataclass
class ToolEntry:
    func: Callable[[Intent, Optional[ConversationContext]], str]
    level: PermissionLevel
    description: str


def _handle_open_app(intent: Intent, context: Optional[ConversationContext]) -> str:
    if not intent.target:
        return "Which app should I open?"
    return open_app(intent.target)


def _handle_open_project(intent: Intent, context: Optional[ConversationContext]) -> str:
    hint = intent.target

    if not hint and context and context.last_project:
        hint = context.last_project

    if not hint:
        return "Which project do you mean?"

    project = find_project(hint)

    if project is None and context and context.last_project:
        hint_words = set(re.findall(r"[a-z0-9]+", hint.lower()))
        if hint_words and hint_words <= _PRONOUN_WORDS:
            project = find_project(context.last_project)

    if project is None:
        return f"I couldn't find a project matching '{hint}'."

    if context:
        context.last_project = project.name

    open_path_in_vscode(project.path)
    return f"Opening {project.name} in VS Code."


def _handle_get_system_info(intent: Intent, context: Optional[ConversationContext]) -> str:
    return get_system_info()


def _handle_take_screenshot(intent: Intent, context: Optional[ConversationContext]) -> str:
    return take_screenshot()


def _handle_remember(intent: Intent, context: Optional[ConversationContext]) -> str:
    if not intent.target:
        return "Kya yaad rakhna hai, bata do."

    category_str = (intent.params or {}).get("category", "context")
    try:
        category = MemoryCategory(category_str)
    except ValueError:
        category = MemoryCategory.CONTEXT

    save_memory(category, intent.target)
    return f"Yaad rakh liya ({category.value}): {intent.target}"


def _handle_recall(intent: Intent, context: Optional[ConversationContext]) -> str:
    memories = search_memories(intent.target or "")[:5]
    if not memories:
        return "Mujhe is baare mein kuch yaad nahi."

    lines = [f"- ({m.category}) {m.content}" for m in memories]
    return "Yeh yaad hai:\n" + "\n".join(lines)


TOOL_REGISTRY: dict[str, ToolEntry] = {
    "open_app": ToolEntry(_handle_open_app, PermissionLevel.SAFE, "Open an application"),
    "open_project": ToolEntry(_handle_open_project, PermissionLevel.SAFE, "Open a known project"),
    "get_system_info": ToolEntry(_handle_get_system_info, PermissionLevel.SAFE, "Report system info"),
    "take_screenshot": ToolEntry(_handle_take_screenshot, PermissionLevel.SAFE, "Take a screenshot"),
    "remember": ToolEntry(_handle_remember, PermissionLevel.CONFIRM, "Save something to long-term memory"),
    "recall": ToolEntry(_handle_recall, PermissionLevel.SAFE, "Recall something from long-term memory"),
}


def route(intent: Intent, context: Optional[ConversationContext] = None) -> Optional[str]:
    """Execute the tool for an intent. Returns None for 'chat' (caller should
    fall through to conversation handling)."""
    if intent.intent == "chat":
        return None

    entry = TOOL_REGISTRY.get(intent.intent)
    if entry is None:
        return f"I don't have a tool for '{intent.intent}' yet."

    return entry.func(intent, context)


def get_permission_level(intent_name: str) -> Optional[PermissionLevel]:
    entry = TOOL_REGISTRY.get(intent_name)
    return entry.level if entry else None
