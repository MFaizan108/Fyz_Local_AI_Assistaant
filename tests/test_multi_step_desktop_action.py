from core.action_executor import router as router_module
from core.action_executor.dispatch import handle_utterance
from core.brain.context import ConversationContext
from core.brain.schemas import Intent


def test_chrome_profile_and_reopen_tabs_execute_in_order(monkeypatch):
    """"Chrome kholo aur Faizan Mahmood profile open karo aur previous
    closed tabs kholo" - the profile step must open Chrome (not a separate
    plain open_app step, which would launch two windows - the existing
    _collapse_redundant_chrome_steps logic already guards that), and
    reopen_closed_tab must run AFTER it, not before."""
    call_order = []

    monkeypatch.setattr(
        router_module, "open_chrome_profile",
        lambda hint: call_order.append(f"open_browser:{hint}") or f"Chrome '{hint}' profile ke saath khol raha hoon bhai 😄",
    )
    monkeypatch.setattr(
        "core.action_executor.router.execute_action",
        lambda name: call_order.append(f"desktop_action:{name}") or "Previous closed tab wapis khol diya bhai 😄",
    )

    steps = [
        {"intent": "open_browser", "target": "chrome", "params": {"profile": "Faizan Mahmood"}},
        {"intent": "desktop_action", "target": "reopen_closed_tab", "params": {}},
    ]
    multi_intent = Intent(intent="multi_step_task", raw_text="chrome kholo aur Faizan Mahmood profile open karo aur previous closed tabs kholo", steps=steps)
    monkeypatch.setattr("core.action_executor.dispatch.get_intent", lambda text, context=None: multi_intent)

    context = ConversationContext()
    reply = handle_utterance(
        "chrome kholo aur Faizan Mahmood profile open karo aur previous closed tabs kholo",
        context, confirm_prompt=lambda p: "y",
    )

    assert call_order == ["open_browser:Faizan Mahmood", "desktop_action:reopen_closed_tab"]
    # Internal intent/action names must never leak into the user-facing reply.
    assert "desktop_action" not in reply
    assert "reopen_closed_tab" not in reply


def test_redundant_plain_chrome_step_is_still_collapsed_alongside_desktop_action_step():
    """A classifier that (despite instructions) also emits a plain
    open_app("chrome") step alongside the profile step must still collapse
    down to one Chrome launch - this pre-existing v3.1 guard must keep
    working now that a third step type (desktop_action) is in the mix."""
    from core.action_executor.dispatch import _collapse_redundant_chrome_steps

    steps = [
        {"intent": "open_app", "target": "chrome", "params": {}},
        {"intent": "open_browser", "target": "chrome", "params": {"profile": "Faizan Mahmood"}},
        {"intent": "desktop_action", "target": "reopen_closed_tab", "params": {}},
    ]

    collapsed = _collapse_redundant_chrome_steps(steps)

    assert len(collapsed) == 2
    assert collapsed[0]["intent"] == "open_browser"
    assert collapsed[1]["intent"] == "desktop_action"
