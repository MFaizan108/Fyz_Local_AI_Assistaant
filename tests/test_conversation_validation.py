from core.brain import conversation
from core.brain.context import ConversationContext


def test_get_chat_reply_retries_once_on_corrupted_output(monkeypatch):
    responses = iter(["筒پا! मुझे समझ नहीं आया", "Theek hai bhai, sab sahi hai."])
    monkeypatch.setattr(conversation, "chat", lambda *a, **k: next(responses))

    reply = conversation.get_chat_reply("hello", ConversationContext())

    assert reply == "Theek hai bhai, sab sahi hai."


def test_get_chat_reply_falls_back_after_two_bad_attempts(monkeypatch):
    monkeypatch.setattr(conversation, "chat", lambda *a, **k: "筒پا गलत जवाब")

    reply = conversation.get_chat_reply("hello", ConversationContext())

    assert reply == conversation.FALLBACK_REPLY


def test_get_chat_reply_passes_through_clean_output_untouched(monkeypatch):
    calls = []
    monkeypatch.setattr(conversation, "chat", lambda *a, **k: calls.append(1) or "Sab theek hai bhai!")

    reply = conversation.get_chat_reply("hello", ConversationContext())

    assert reply == "Sab theek hai bhai!"
    assert len(calls) == 1  # no retry needed for a clean first response
