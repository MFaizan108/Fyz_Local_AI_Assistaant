from core.action_executor.router import route
from core.brain.schemas import Intent


def test_propose_improvement_refuses_protected_path():
    """Fast and deterministic: refuses before any git/LLM call happens, so
    it doesn't need the slower full propose->diff->tests cycle to verify
    the one rule that matters most here - Fyz can never touch its own
    security/permissions code."""
    intent = Intent(
        intent="propose_improvement",
        target="add a comment",
        params={"file": "core/security/protected_paths.py"},
        raw_text="test",
    )
    reply = route(intent, context=None, confirm_prompt=lambda p: "confirm")
    assert "protected" in reply.lower()
