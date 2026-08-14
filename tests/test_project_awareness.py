from core.action_executor import router
from core.brain.context import ConversationContext
from core.brain.schemas import Intent


def test_project_info_returns_registry_description_not_hallucinated():
    intent = Intent(intent="project_info", target="healthcare project", raw_text="healthcare project kya karta hai?")
    context = ConversationContext()

    reply = router.route(intent, context, confirm_prompt=lambda p: "y")

    assert "healthcare" in reply.lower()
    assert context.last_project is not None


def test_project_info_unknown_project_does_not_hallucinate():
    intent = Intent(intent="project_info", target="totally nonexistent project xyz123", raw_text="x")
    context = ConversationContext()

    reply = router.route(intent, context, confirm_prompt=lambda p: "y")

    assert "nahi mila" in reply


def test_current_project_query_uses_active_context():
    intent = Intent(intent="current_project_query", target=None, raw_text="main kis project par kaam kar raha hoon?")
    context = ConversationContext(last_project="FaizanMart")

    reply = router.route(intent, context, confirm_prompt=lambda p: "y")

    assert "FaizanMart" in reply


def test_current_project_query_falls_back_to_recent_action_log(monkeypatch):
    fake_entry = type("Fake", (), {"intent": "open_project", "executed": True, "target": "TaskFlow"})()
    monkeypatch.setattr(router, "recent_actions", lambda limit=20: [fake_entry])

    intent = Intent(intent="current_project_query", target=None, raw_text="x")
    context = ConversationContext()

    reply = router.route(intent, context, confirm_prompt=lambda p: "y")

    assert "TaskFlow" in reply


def test_current_project_query_with_nothing_known_asks_naturally(monkeypatch):
    monkeypatch.setattr(router, "recent_actions", lambda limit=20: [])

    intent = Intent(intent="current_project_query", target=None, raw_text="x")
    context = ConversationContext()

    reply = router.route(intent, context, confirm_prompt=lambda p: "y")

    assert "kis wale" in reply.lower() or "kuch projects" in reply.lower()
