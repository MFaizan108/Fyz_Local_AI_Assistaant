from core.action_executor import router as router_module
from core.action_executor.dispatch import handle_utterance
from core.brain.context import ConversationContext
from core.brain.schemas import Intent
from core.permissions.levels import PermissionLevel

# Uses a fake injected DANGEROUS tool rather than a real one (delete_file,
# kill_process, propose_improvement) so this test stays fast and has no
# side effects of its own.


def _fake_dangerous_handler(intent, context, confirm_prompt):
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
