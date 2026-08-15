from core.action_executor import router as router_module
from core.action_executor.dispatch import _permission_for, handle_utterance
from core.brain.brain import _normalize_desktop_action
from core.brain.context import ConversationContext
from core.brain.schemas import Intent
from core.permissions.levels import PermissionLevel
from tools.desktop_control.executor import execute_action
from tools.desktop_control.registry import ACTIONS, get_action, list_action_names


# --- LLM classification self-healing (found via live testing: the model
# sometimes outputs a registered action name directly as `intent` instead
# of the correct {"intent": "desktop_action", "target": <action name>}
# shape) ---------------------------------------------------------------

def test_normalize_rewrites_action_name_used_directly_as_intent():
    data = {"intent": "lock_laptop", "target": None, "params": {}}
    _normalize_desktop_action(data)
    assert data["intent"] == "desktop_action"
    assert data["target"] == "lock_laptop"


def test_normalize_is_a_noop_for_already_correct_shape():
    data = {"intent": "desktop_action", "target": "copy", "params": {}}
    _normalize_desktop_action(data)
    assert data == {"intent": "desktop_action", "target": "copy", "params": {}}


def test_normalize_is_a_noop_for_unrelated_intents():
    data = {"intent": "open_app", "target": "chrome", "params": {}}
    _normalize_desktop_action(data)
    assert data == {"intent": "open_app", "target": "chrome", "params": {}}


def test_normalize_fixes_steps_inside_multi_step_task():
    data = {
        "intent": "multi_step_task",
        "steps": [
            {"intent": "copy", "target": None, "params": {}},
            {"intent": "open_app", "target": "chrome", "params": {}},
        ],
    }
    _normalize_desktop_action(data)
    assert data["steps"][0] == {"intent": "desktop_action", "target": "copy", "params": {}}
    assert data["steps"][1] == {"intent": "open_app", "target": "chrome", "params": {}}


def test_known_shortcut_mappings_match_the_spec():
    assert ACTIONS["copy"].keys == ("ctrl", "c")
    assert ACTIONS["paste"].keys == ("ctrl", "v")
    assert ACTIONS["cut"].keys == ("ctrl", "x")
    assert ACTIONS["select_all"].keys == ("ctrl", "a")
    assert ACTIONS["undo"].keys == ("ctrl", "z")
    assert ACTIONS["redo"].keys == ("ctrl", "y")
    assert ACTIONS["task_manager"].keys == ("ctrl", "shift", "esc")
    assert ACTIONS["reopen_closed_tab"].keys is None  # special-cased in executor.py
    assert ACTIONS["open_settings"].keys == ("win", "i")
    assert ACTIONS["open_run_dialog"].keys == ("win", "r")
    assert ACTIONS["show_desktop"].keys == ("win", "d")
    assert ACTIONS["windows_search"].keys == ("win", "s")
    assert ACTIONS["lock_laptop"].keys == ("win", "l")
    assert ACTIONS["close_window"].keys == ("alt", "f4")
    assert ACTIONS["switch_window"].keys == ("alt", "tab")
    assert ACTIONS["minimize_window"].keys == ("win", "down")
    assert ACTIONS["maximize_window"].keys == ("win", "up")
    assert ACTIONS["snap_left"].keys == ("win", "left")
    assert ACTIONS["snap_right"].keys == ("win", "right")
    assert ACTIONS["new_tab"].keys == ("ctrl", "t")
    assert ACTIONS["close_tab"].keys == ("ctrl", "w")
    assert ACTIONS["next_tab"].keys == ("ctrl", "tab")
    assert ACTIONS["previous_tab"].keys == ("ctrl", "shift", "tab")
    assert ACTIONS["focus_address_bar"].keys == ("ctrl", "l")
    assert ACTIONS["find_in_page"].keys == ("ctrl", "f")
    assert ACTIONS["refresh"].keys == ("f5",)
    assert ACTIONS["print"].keys == ("ctrl", "p")
    assert ACTIONS["press_delete_key"].keys == ("delete",)


def test_permission_levels_match_the_spec():
    safe_actions = ["copy", "cut", "paste", "select_all", "undo", "redo", "task_manager",
                     "open_settings", "open_run_dialog", "show_desktop", "windows_search",
                     "refresh", "print", "new_tab", "reopen_closed_tab", "next_tab",
                     "previous_tab", "minimize_window", "maximize_window", "snap_left",
                     "snap_right", "switch_window", "screenshot_full", "screenshot_active_window"]
    confirm_actions = ["press_delete_key", "close_window", "lock_laptop", "close_tab"]

    for name in safe_actions:
        assert ACTIONS[name].permission == PermissionLevel.SAFE, name
    for name in confirm_actions:
        assert ACTIONS[name].permission == PermissionLevel.CONFIRM, name


def test_get_action_unknown_returns_none():
    assert get_action("some_action_that_does_not_exist") is None


def test_list_action_names_matches_registry_keys():
    assert set(list_action_names()) == set(ACTIONS.keys())


def test_execute_action_sends_the_right_hotkey(monkeypatch):
    sent = []
    monkeypatch.setattr("tools.desktop_control.executor.send_hotkey", lambda keys: sent.append(keys))

    result = execute_action("copy")

    assert sent == [("ctrl", "c")]
    assert result is not None and "copy" in result.lower()


def test_execute_action_unknown_returns_none(monkeypatch):
    assert execute_action("not_a_real_action") is None


def test_execute_action_never_claims_success_if_hotkey_send_fails(monkeypatch):
    def _boom(keys):
        raise RuntimeError("simulated OS failure")

    monkeypatch.setattr("tools.desktop_control.executor.send_hotkey", _boom)

    try:
        execute_action("copy")
        assert False, "expected the exception to propagate, not be swallowed"
    except RuntimeError:
        pass


# --- reopen_closed_tab: detect / launch / focus / send keys ---------------

def test_reopen_closed_tab_launches_chrome_if_not_running(monkeypatch):
    calls = {"opened": False, "sent": None}
    monkeypatch.setattr("tools.desktop_control.executor.is_process_running", lambda exe: False)
    monkeypatch.setattr("tools.desktop_control.executor.open_app", lambda name: calls.__setitem__("opened", True))
    monkeypatch.setattr("tools.desktop_control.executor.focus_window_by_process", lambda exe: True)
    monkeypatch.setattr("tools.desktop_control.executor.send_hotkey", lambda keys: calls.__setitem__("sent", keys))
    monkeypatch.setattr("tools.desktop_control.executor.time.sleep", lambda s: None)

    result = execute_action("reopen_closed_tab")

    assert calls["opened"] is True
    assert calls["sent"] == ("ctrl", "shift", "t")
    assert result is not None


def test_reopen_closed_tab_does_not_relaunch_if_already_running(monkeypatch):
    calls = {"opened": False}
    monkeypatch.setattr("tools.desktop_control.executor.is_process_running", lambda exe: True)
    monkeypatch.setattr("tools.desktop_control.executor.open_app", lambda name: calls.__setitem__("opened", True))
    monkeypatch.setattr("tools.desktop_control.executor.focus_window_by_process", lambda exe: True)
    monkeypatch.setattr("tools.desktop_control.executor.send_hotkey", lambda keys: None)
    monkeypatch.setattr("tools.desktop_control.executor.time.sleep", lambda s: None)

    execute_action("reopen_closed_tab")

    assert calls["opened"] is False


def test_reopen_closed_tab_still_sends_shortcut_even_if_focus_fails(monkeypatch):
    """Focusing can legitimately fail (Windows foreground-lock) - the
    shortcut should still be sent (best effort) and the reply should be
    honest, not a hard failure."""
    sent = []
    monkeypatch.setattr("tools.desktop_control.executor.is_process_running", lambda exe: True)
    monkeypatch.setattr("tools.desktop_control.executor.focus_window_by_process", lambda exe: False)
    monkeypatch.setattr("tools.desktop_control.executor.send_hotkey", lambda keys: sent.append(keys))
    monkeypatch.setattr("tools.desktop_control.executor.time.sleep", lambda s: None)

    result = execute_action("reopen_closed_tab")

    assert sent == [("ctrl", "shift", "t")]
    assert result is not None


# --- router / dispatch integration -----------------------------------------

# --- Screenshots ------------------------------------------------------------

def test_screenshot_full_delegates_to_existing_take_screenshot(monkeypatch, tmp_path):
    monkeypatch.setattr("tools.desktop_control.executor.take_screenshot", lambda: "Screenshot saved to X")
    result = execute_action("screenshot_full")
    assert result == "Screenshot saved to X"


def test_screenshot_active_window_falls_back_to_full_screen_if_no_window_rect(monkeypatch):
    monkeypatch.setattr("tools.desktop_control.executor.get_foreground_window_rect", lambda: None)
    monkeypatch.setattr("tools.desktop_control.executor.take_screenshot", lambda: "Screenshot saved to FULL")
    result = execute_action("screenshot_active_window")
    assert result == "Screenshot saved to FULL"


def test_screenshot_active_window_saves_a_new_uniquely_named_file(monkeypatch, tmp_path):
    monkeypatch.setattr("tools.desktop_control.executor.get_foreground_window_rect", lambda: (0, 0, 100, 100))
    monkeypatch.setattr("tools.desktop_control.executor.SCREENSHOTS_DIR", tmp_path)

    class _FakeImage:
        def save(self, path):
            with open(path, "wb") as f:
                f.write(b"fake-png-bytes")

    monkeypatch.setattr("PIL.ImageGrab.grab", lambda bbox=None: _FakeImage())

    result = execute_action("screenshot_active_window")

    saved_files = list(tmp_path.glob("active_window_*.png"))
    assert len(saved_files) == 1
    assert str(saved_files[0]) in result


def test_desktop_action_router_rejects_unregistered_target():
    intent = Intent(intent="desktop_action", raw_text="x", target="not_a_real_shortcut", params={})
    reply = router_module.route(intent, ConversationContext(), confirm_prompt=lambda p: "y")
    assert "shortcut abhi mere paas nahi hai" in reply


def test_desktop_action_router_does_not_expose_internal_action_names(monkeypatch):
    monkeypatch.setattr("core.action_executor.router.execute_action", lambda name: "Copy kar diya bhai 😄")
    intent = Intent(intent="desktop_action", raw_text="copy karo", target="copy", params={})
    reply = router_module.route(intent, ConversationContext(), confirm_prompt=lambda p: "y")
    assert "copy" not in reply.lower() or "kar diya" in reply.lower()  # never a raw "Step N (copy):" style leak
    assert "intent" not in reply.lower()


def test_permission_for_is_target_aware_for_desktop_action():
    safe_intent = Intent(intent="desktop_action", raw_text="x", target="copy", params={})
    confirm_intent = Intent(intent="desktop_action", raw_text="x", target="lock_laptop", params={})

    assert _permission_for(safe_intent) == PermissionLevel.SAFE
    assert _permission_for(confirm_intent) == PermissionLevel.CONFIRM


def test_lock_laptop_requires_confirmation_end_to_end(monkeypatch):
    executed = {"called": False}
    monkeypatch.setattr("core.action_executor.router.execute_action", lambda name: executed.__setitem__("called", True) or "Laptop lock kar diya bhai.")
    monkeypatch.setattr(
        "core.action_executor.dispatch.get_intent",
        lambda text, context=None: Intent(intent="desktop_action", raw_text=text, target="lock_laptop", params={}),
    )

    context = ConversationContext()
    reply = handle_utterance("laptop lock karo", context, confirm_prompt=lambda p: "n")

    assert executed["called"] is False
    assert "cancel" in reply.lower() or "nahi karta" in reply.lower()


def test_copy_does_not_require_confirmation_end_to_end(monkeypatch):
    executed = {"called": False}
    monkeypatch.setattr("core.action_executor.router.execute_action", lambda name: executed.__setitem__("called", True) or "Copy kar diya bhai 😄")
    monkeypatch.setattr(
        "core.action_executor.dispatch.get_intent",
        lambda text, context=None: Intent(intent="desktop_action", raw_text=text, target="copy", params={}),
    )

    context = ConversationContext()
    reply = handle_utterance("copy karo", context, confirm_prompt=lambda p: (_ for _ in ()).throw(AssertionError("should not need confirmation")))

    assert executed["called"] is True
