from core.action_executor import router as router_module
from core.action_executor.dispatch import handle_utterance
from core.brain.context import ConversationContext
from core.brain.schemas import Intent
from core.permissions.levels import PermissionLevel


def _fake_open_app(intent, context, confirm_prompt):
    return f"Opening {intent.target}."


def test_multi_step_executes_supported_step_and_reports_unsupported_step(monkeypatch):
    fake_entry = router_module.ToolEntry(_fake_open_app, PermissionLevel.SAFE, "test")
    monkeypatch.setitem(router_module.TOOL_REGISTRY, "open_app", fake_entry)

    multi_intent = Intent(
        intent="multi_step_task",
        raw_text="open chrome and search todays weather",
        steps=[
            {"intent": "open_app", "target": "chrome", "params": {}},
            {"intent": "search_web", "target": "today's weather", "params": {}},
        ],
    )
    monkeypatch.setattr(
        "core.action_executor.dispatch.get_intent",
        lambda text, context=None: multi_intent,
    )

    context = ConversationContext()
    reply = handle_utterance("open chrome and search todays weather", context, confirm_prompt=lambda p: "y")

    assert "Opening chrome." in reply
    assert "search_web" in reply
    assert "don't have a tool" in reply.lower()


def test_multi_step_with_no_steps_gives_clear_message(monkeypatch):
    multi_intent = Intent(intent="multi_step_task", raw_text="do things", steps=[])
    monkeypatch.setattr(
        "core.action_executor.dispatch.get_intent",
        lambda text, context=None: multi_intent,
    )

    context = ConversationContext()
    reply = handle_utterance("do things", context)

    assert "step" in reply.lower() or "samajh" in reply.lower()


def test_multi_step_dangerous_step_still_requires_exact_confirm_phrase(monkeypatch):
    def _fake_dangerous(intent, context, confirm_prompt):
        return "deleted"

    fake_entry = router_module.ToolEntry(_fake_dangerous, PermissionLevel.DANGEROUS, "test")
    monkeypatch.setitem(router_module.TOOL_REGISTRY, "delete_file", fake_entry)

    multi_intent = Intent(
        intent="multi_step_task",
        raw_text="delete two files",
        steps=[{"intent": "delete_file", "target": "a.txt", "params": {}}],
    )
    monkeypatch.setattr(
        "core.action_executor.dispatch.get_intent",
        lambda text, context=None: multi_intent,
    )

    context = ConversationContext()
    # A plain "y" must NOT be enough for a DANGEROUS step, same as a
    # standalone dangerous command.
    reply = handle_utterance("delete two files", context, confirm_prompt=lambda p: "y")

    assert "deleted" not in reply
