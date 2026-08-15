"""Generic Windows keyboard-shortcut/action registry (Brain v3.3).

One reusable action -> keystroke mapping, not a separate tool function per
shortcut. Each `ShortcutAction` is self-describing (name, natural-language
aliases, the actual key combo, its SAFE/CONFIRM/DANGEROUS permission level)
so the brain's intent classifier, the router's permission gate, and the
executor all read from this single source of truth instead of three
different hardcoded lists that could drift out of sync.

Not every action here is a plain keystroke - a few (`reopen_closed_tab`,
`screenshot_full`, `screenshot_active_window`) need extra logic (detecting/
focusing Chrome, grabbing a specific window's bounds) and are implemented in
`executor.py`, but they're still registered here with the same metadata
shape so permission-gating and "is this a known action" validation treat
them identically to a plain hotkey.

This is deliberately NOT "every Windows shortcut" - it's the common,
useful set from the v3.3 spec, structured so adding one more is a single
dict entry, not a new function/intent/test file each time."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from core.permissions.levels import PermissionLevel


@dataclass(frozen=True)
class ShortcutAction:
    name: str
    aliases: Tuple[str, ...]
    keys: Optional[Tuple[str, ...]]  # None for actions executor.py implements specially
    permission: PermissionLevel
    description: str
    target_os: str = "windows"

    @property
    def requires_confirmation(self) -> bool:
        return self.permission != PermissionLevel.SAFE


ACTIONS: Dict[str, ShortcutAction] = {
    # --- Clipboard / editing - act on whatever app currently has focus ---
    "copy": ShortcutAction("copy", ("copy karo", "yeh copy kar do", "copy kar do"), ("ctrl", "c"), PermissionLevel.SAFE, "Copy the current selection"),
    "cut": ShortcutAction("cut", ("cut karo", "yeh cut kar do"), ("ctrl", "x"), PermissionLevel.SAFE, "Cut the current selection"),
    "paste": ShortcutAction("paste", ("paste karo", "paste kar do"), ("ctrl", "v"), PermissionLevel.SAFE, "Paste from clipboard"),
    "select_all": ShortcutAction("select_all", ("select all karo", "sab select karo"), ("ctrl", "a"), PermissionLevel.SAFE, "Select all"),
    "undo": ShortcutAction("undo", ("undo karo",), ("ctrl", "z"), PermissionLevel.SAFE, "Undo the last action"),
    "redo": ShortcutAction("redo", ("redo karo",), ("ctrl", "y"), PermissionLevel.SAFE, "Redo the last undone action"),
    # Distinct from the existing `delete_file` tool (which permanently
    # unlinks a NAMED path and is DANGEROUS) - this just presses the Delete
    # key on whatever's currently selected in the focused app (e.g. Explorer
    # -> Recycle Bin, reversible), so CONFIRM rather than DANGEROUS, but
    # never silent either way.
    "press_delete_key": ShortcutAction("press_delete_key", ("selected item delete karo", "yeh delete karo", "delete karo"), ("delete",), PermissionLevel.CONFIRM, "Press Delete on the current selection"),

    # --- Screenshots (special-cased in executor.py) ---
    "screenshot_full": ShortcutAction("screenshot_full", ("screenshot lo", "screen shot lo", "meri screen ka screenshot lo"), None, PermissionLevel.SAFE, "Full-screen screenshot"),
    "screenshot_active_window": ShortcutAction("screenshot_active_window", ("active window ka screenshot lo",), None, PermissionLevel.SAFE, "Screenshot of the active window only"),
    "screenshot_region": ShortcutAction("screenshot_region", ("region screenshot lo", "screenshot region select karo"), ("win", "shift", "s"), PermissionLevel.SAFE, "Launch Windows' interactive region-capture tool"),

    # --- Task Manager / processes ---
    "task_manager": ShortcutAction("task_manager", ("task manager kholo",), ("ctrl", "shift", "esc"), PermissionLevel.SAFE, "Open Task Manager"),

    # --- Window management ---
    "minimize_window": ShortcutAction("minimize_window", ("window minimize karo", "minimize karo"), ("win", "down"), PermissionLevel.SAFE, "Minimize the active window"),
    "maximize_window": ShortcutAction("maximize_window", ("window maximize karo", "maximize karo"), ("win", "up"), PermissionLevel.SAFE, "Maximize the active window"),
    "snap_left": ShortcutAction("snap_left", ("window left snap karo", "window left karo"), ("win", "left"), PermissionLevel.SAFE, "Snap the active window to the left half"),
    "snap_right": ShortcutAction("snap_right", ("window right snap karo", "window right karo"), ("win", "right"), PermissionLevel.SAFE, "Snap the active window to the right half"),
    "switch_window": ShortcutAction("switch_window", ("window switch karo", "alt tab karo"), ("alt", "tab"), PermissionLevel.SAFE, "Switch to the next window"),
    # Can lose unsaved work - CONFIRM unless the caller can prove there's no
    # risk, which Fyz has no reliable way to do from outside the app.
    "close_window": ShortcutAction("close_window", ("window band karo", "active window close karo"), ("alt", "f4"), PermissionLevel.CONFIRM, "Close the active window"),

    # --- Windows Search ---
    "windows_search": ShortcutAction("windows_search", ("search kholo", "windows search kholo"), ("win", "s"), PermissionLevel.SAFE, "Open Windows Search"),

    # --- Lock ---
    "lock_laptop": ShortcutAction("lock_laptop", ("laptop lock karo", "screen lock karo"), ("win", "l"), PermissionLevel.CONFIRM, "Lock the laptop"),

    # --- Settings / Run / Desktop ---
    "open_settings": ShortcutAction("open_settings", ("settings kholo", "laptop settings kholo"), ("win", "i"), PermissionLevel.SAFE, "Open Windows Settings"),
    "open_run_dialog": ShortcutAction("open_run_dialog", ("run kholo",), ("win", "r"), PermissionLevel.SAFE, "Open the Run dialog"),
    "show_desktop": ShortcutAction("show_desktop", ("desktop dikhao", "desktop par jao"), ("win", "d"), PermissionLevel.SAFE, "Show the desktop"),

    # --- Generic refresh / print ---
    "refresh": ShortcutAction("refresh", ("refresh karo", "page refresh karo"), ("f5",), PermissionLevel.SAFE, "Refresh the current view/page"),
    "print": ShortcutAction("print", ("print karo",), ("ctrl", "p"), PermissionLevel.SAFE, "Open the print dialog (does not print automatically)"),

    # --- Browser tabs (special-cased for reopen_closed_tab) ---
    "new_tab": ShortcutAction("new_tab", ("new tab kholo", "new tab open karo"), ("ctrl", "t"), PermissionLevel.SAFE, "Open a new browser tab"),
    # Could lose unsaved form data on the current page - CONFIRM per the
    # same "no way to know if it's safe" reasoning as close_window.
    "close_tab": ShortcutAction("close_tab", ("tab band karo", "current tab close karo"), ("ctrl", "w"), PermissionLevel.CONFIRM, "Close the current browser tab"),
    "reopen_closed_tab": ShortcutAction("reopen_closed_tab", ("previous closed tab kholo", "closed tab wapis kholo", "last tab reopen karo", "previous tabs restore karo", "closed tabs open karo"), None, PermissionLevel.SAFE, "Reopen the last closed browser tab"),
    "next_tab": ShortcutAction("next_tab", ("next tab kholo", "next tab par jao"), ("ctrl", "tab"), PermissionLevel.SAFE, "Switch to the next browser tab"),
    "previous_tab": ShortcutAction("previous_tab", ("previous tab par jao", "previous tab kholo"), ("ctrl", "shift", "tab"), PermissionLevel.SAFE, "Switch to the previous browser tab"),
    "focus_address_bar": ShortcutAction("focus_address_bar", ("address bar kholo", "address bar par jao"), ("ctrl", "l"), PermissionLevel.SAFE, "Focus the browser address bar"),
    "find_in_page": ShortcutAction("find_in_page", ("page mein search karo", "page search karo"), ("ctrl", "f"), PermissionLevel.SAFE, "Search within the current page"),
}


def get_action(name: str) -> Optional[ShortcutAction]:
    return ACTIONS.get(name)


def list_action_names() -> List[str]:
    return list(ACTIONS.keys())
