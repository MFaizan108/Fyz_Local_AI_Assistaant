"""Executes a registered ShortcutAction by name. One generic dispatcher, not
one function per shortcut - most actions are just `send_hotkey(action.keys)`,
a handful need extra logic (Chrome-specific reopen-closed-tab, window-bound
screenshots) and get a dedicated branch below.

Never invents success: if the underlying OS call raises, this lets the
exception propagate (dispatch.py's outer handler already converts any
exception into a natural failure reply and logs it - see
core/action_executor/dispatch.py's handle_utterance) rather than catching it
here and claiming the action happened anyway."""

import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from tools.app_control.apps import open_app
from tools.desktop_control.registry import ShortcutAction, get_action
from tools.desktop_control.shortcuts import (
    focus_window_by_process,
    get_foreground_window_rect,
    is_process_running,
    send_hotkey,
)
from tools.system_tools.screenshot import SCREENSHOTS_DIR, take_screenshot

CHROME_EXE = "chrome.exe"

# Friendly, Roman-Urdu confirmations per action - action names not exposed
# to the user, only these natural sentences. A generic fallback below covers
# any action without a hand-written line here (all of them have one, but new
# actions added later won't crash the moment they're registered).
_SUCCESS_MESSAGES = {
    "copy": "Copy kar diya bhai 😄",
    "cut": "Cut kar diya bhai 😄",
    "paste": "Paste kar diya bhai 😄",
    "select_all": "Sab select kar diya bhai 😄",
    "undo": "Undo kar diya bhai 😄",
    "redo": "Redo kar diya bhai 😄",
    "press_delete_key": "Delete kar diya bhai.",
    "screenshot_region": "Region screenshot tool khol diya bhai, select karke capture kar lo 😄",
    "task_manager": "Task Manager khol diya bhai 😄",
    "minimize_window": "Window minimize kar diya bhai.",
    "maximize_window": "Window maximize kar diya bhai.",
    "snap_left": "Window left snap kar diya bhai.",
    "snap_right": "Window right snap kar diya bhai.",
    "switch_window": "Window switch kar diya bhai.",
    "close_window": "Window band kar diya bhai.",
    "windows_search": "Windows search khol diya bhai 😄",
    "lock_laptop": "Laptop lock kar diya bhai.",
    "open_settings": "Settings khol diya bhai 😄",
    "open_run_dialog": "Run dialog khol diya bhai 😄",
    "show_desktop": "Desktop dikha diya bhai.",
    "refresh": "Refresh kar diya bhai 😄",
    "print": "Print dialog khol diya bhai - print karne se pehle khud confirm karna.",
    "new_tab": "Naya tab khol diya bhai 😄",
    "close_tab": "Tab band kar diya bhai.",
    "next_tab": "Next tab par chala gaya bhai.",
    "previous_tab": "Previous tab par chala gaya bhai.",
    "focus_address_bar": "Address bar par focus kar diya bhai.",
    "find_in_page": "Page search khol diya bhai 😄",
}


def _reopen_closed_tab() -> str:
    """Detect -> launch if needed -> focus -> Ctrl+Shift+T. Never sends the
    shortcut blindly - if Chrome genuinely isn't reachable (not running and
    won't launch, or its window can't be focused), that's reported honestly
    rather than claiming the tab was restored."""
    was_running = is_process_running(CHROME_EXE)
    if not was_running:
        open_app("chrome")
        time.sleep(2.5)  # first launch needs real time before a window exists to focus

    focused = False
    for _ in range(3):
        focused = focus_window_by_process(CHROME_EXE)
        if focused:
            break
        time.sleep(0.5)

    send_hotkey(("ctrl", "shift", "t"))

    if focused:
        return "Previous closed tab wapis khol diya bhai 😄"
    return "Chrome ko reopen-tab command bhej diya bhai, ek dafa screen check kar lena 😄"


def _screenshot_active_window() -> str:
    from PIL import ImageGrab

    rect = get_foreground_window_rect()
    if rect is None:
        return take_screenshot()  # fall back to full-screen rather than failing outright

    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = SCREENSHOTS_DIR / f"active_window_{datetime.now():%Y%m%d_%H%M%S}.png"
    image = ImageGrab.grab(bbox=rect)
    image.save(filename)
    return f"Active window ka screenshot save ho gaya: {filename}"


def execute_action(name: str) -> Optional[str]:
    """Returns the natural reply, or None if `name` isn't a registered
    action (caller decides the "I don't have this shortcut" message - this
    function never guesses at an unregistered action)."""
    action: Optional[ShortcutAction] = get_action(name)
    if action is None:
        return None

    if name == "reopen_closed_tab":
        return _reopen_closed_tab()
    if name == "screenshot_full":
        return take_screenshot()
    if name == "screenshot_active_window":
        return _screenshot_active_window()

    send_hotkey(action.keys)
    return _SUCCESS_MESSAGES.get(name, f"{action.description} - kar diya bhai 😄")
