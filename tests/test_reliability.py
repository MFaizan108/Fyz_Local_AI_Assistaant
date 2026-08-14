import httpx

from core.action_executor.dispatch import TECHNICAL_FAILURE_REPLY, handle_utterance
from core.brain.context import ConversationContext


def test_ollama_timeout_never_exposes_raw_traceback(monkeypatch):
    def _boom(*args, **kwargs):
        raise httpx.ReadTimeout("timed out")

    monkeypatch.setattr("core.brain.brain.chat", _boom)

    context = ConversationContext()
    reply = handle_utterance("healthcare project kholo", context)

    assert reply == TECHNICAL_FAILURE_REPLY
    assert "Traceback" not in reply
    assert "httpx" not in reply
    assert "ReadTimeout" not in reply


def test_ollama_connection_error_never_exposes_raw_traceback(monkeypatch):
    def _boom(*args, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr("core.brain.brain.chat", _boom)

    context = ConversationContext()
    reply = handle_utterance("kya haal hai", context)

    assert reply == TECHNICAL_FAILURE_REPLY


def test_tool_execution_failure_never_exposes_raw_traceback(monkeypatch):
    def _boom(text, context=None):
        raise RuntimeError("some unexpected tool bug")

    monkeypatch.setattr("core.action_executor.dispatch.get_intent", _boom)

    context = ConversationContext()
    reply = handle_utterance("Chrome kholo", context)

    assert reply == TECHNICAL_FAILURE_REPLY


def test_failure_is_still_logged_internally(monkeypatch):
    monkeypatch.setattr(
        "core.action_executor.dispatch.get_intent",
        lambda text, context=None: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    logged = []
    monkeypatch.setattr(
        "core.action_executor.dispatch._logger",
        type("FakeLogger", (), {"exception": staticmethod(lambda *a, **k: logged.append(a))})(),
    )

    context = ConversationContext()
    handle_utterance("Chrome kholo", context)

    assert len(logged) == 1
