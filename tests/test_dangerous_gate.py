from core.action_executor import router as router_module
from core.action_executor.dispatch import handle_utterance
from core.brain.context import ConversationContext
from core.brain.schemas import Intent
from core.permissions.levels import PermissionLevel

# No real DANGEROUS-tier tool exists in the router yet (nothing destructive
# has been built), so this injects a fake one for the duration of the test
# to exercise the gate that will matter once Phase 10 adds one.


def _fake_dangerous_handler(intent, context):
    return "danger executed"


def test_dangerous_tool_rejects_plain_yes(monkeypatch):
    fake_entry = router_module.ToolEntry(_fake_dangerous_handler, PermissionLevel.DANGEROUS, "test")
    monkeypatch.setitem(router_module.TOOL_REGISTRY, "test_dangerous", fake_entry)
    monkeypatch.setattr(
        "core.action_executor.dispatch.get_intent",
        lambda text, context: Intent(intent="test_dangerous", target="x", raw_text=text),
    )

    context = ConversationContext()
    reply = handle_utterance("do the dangerous thing", context, confirm_prompt=lambda p: "y")

    assert reply != "danger executed"
    assert "cancel" in reply.lower()


def test_dangerous_tool_runs_on_exact_confirm_phrase(monkeypatch):
    fake_entry = router_module.ToolEntry(_fake_dangerous_handler, PermissionLevel.DANGEROUS, "test")
    monkeypatch.setitem(router_module.TOOL_REGISTRY, "test_dangerous", fake_entry)
    monkeypatch.setattr(
        "core.action_executor.dispatch.get_intent",
        lambda text, context: Intent(intent="test_dangerous", target="x", raw_text=text),
    )

    context = ConversationContext()
    reply = handle_utterance("do the dangerous thing", context, confirm_prompt=lambda p: "confirm")

    assert reply == "danger executed"
