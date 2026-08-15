"""Low-level OS interaction for desktop_control - the only place pyautogui/
pywin32 calls happen, so executor.py and tests have one seam to work with
(mock these three functions, never the underlying libraries directly)."""

from typing import Optional, Tuple

import psutil
import pyautogui

# pyautogui's own fail-safe (abort on mouse-to-corner) doesn't apply to
# hotkey-only usage, but keep the tiny inter-key delay it defaults to -
# sending a combo with zero delay is what makes modifier keys get missed.
pyautogui.PAUSE = 0.05


def send_hotkey(keys: Tuple[str, ...]) -> None:
    """Sends a key combo to whatever application currently has OS focus -
    this is the actual "shortcut" action. Never claims success without this
    call actually happening; if pyautogui raises, the caller must not report
    the action as done."""
    pyautogui.hotkey(*keys)


def is_process_running(exe_name: str) -> bool:
    exe_name = exe_name.lower()
    return any((p.info.get("name") or "").lower() == exe_name for p in psutil.process_iter(["name"]))


def focus_window_by_process(exe_name: str) -> bool:
    """Brings the first visible top-level window belonging to `exe_name` to
    the foreground. Returns False (not an exception) if no such window is
    found or focusing fails - Windows' own foreground-lock protection can
    refuse a focus request from a background process, so this is
    best-effort, and callers must degrade to a natural "sent it, but
    couldn't confirm it's focused" message rather than assuming success."""
    try:
        import win32con
        import win32gui
        import win32process
    except ImportError:
        return False

    target_hwnd: Optional[int] = None

    def _callback(hwnd, _):
        nonlocal target_hwnd
        if not win32gui.IsWindowVisible(hwnd) or not win32gui.GetWindowText(hwnd):
            return True
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc = psutil.Process(pid)
            if proc.name().lower() == exe_name.lower():
                target_hwnd = hwnd
                return False
        except (psutil.Error, Exception):
            pass
        return True

    win32gui.EnumWindows(_callback, None)
    if target_hwnd is None:
        return False

    try:
        win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(target_hwnd)
        return True
    except Exception:
        return False


def get_foreground_window_rect() -> Optional[Tuple[int, int, int, int]]:
    try:
        import win32gui
    except ImportError:
        return None

    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        return None
    return win32gui.GetWindowRect(hwnd)
