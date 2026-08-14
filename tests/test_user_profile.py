from core.action_executor.dispatch import handle_utterance
from core.brain.context import ConversationContext
from core.brain.user_profile import FULL_NAME, get_profile_reply


def test_what_is_my_name():
    reply = get_profile_reply("mera naam kya hai?")
    assert FULL_NAME in reply


def test_who_am_i():
    reply = get_profile_reply("main kon hoon?")
    assert FULL_NAME in reply


def test_english_phrasing_also_detected():
    assert get_profile_reply("what is my name") is not None
    assert get_profile_reply("who am i") is not None


def test_unrelated_text_returns_none():
    assert get_profile_reply("chrome kholo") is None
    assert get_profile_reply("kya haal hai") is None


def test_profile_question_never_reaches_llm_intent_classifier(monkeypatch):
    def _boom(text, context=None):
        raise AssertionError("get_intent should never be called for profile questions")

    monkeypatch.setattr("core.action_executor.dispatch.get_intent", _boom)

    context = ConversationContext()
    reply = handle_utterance("mera naam kya hai?", context)

    assert FULL_NAME in reply
