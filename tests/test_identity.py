from core.action_executor.dispatch import handle_utterance
from core.brain.context import ConversationContext
from core.brain.identity import CREATOR, NAME, PRIMARY_USER, get_identity_reply


def test_who_are_you():
    reply = get_identity_reply("tum kon ho?")
    assert NAME in reply


def test_who_made_you():
    reply = get_identity_reply("aap ka founder kon hai?")
    assert CREATOR in reply


def test_who_created_you_alt_phrasing():
    reply = get_identity_reply("tumhe kis ne banaya?")
    assert CREATOR in reply


def test_whose_assistant():
    reply = get_identity_reply("tum kis ke assistant ho?")
    assert PRIMARY_USER in reply


def test_english_phrasings_also_detected():
    assert get_identity_reply("who created you?") is not None
    assert get_identity_reply("who are you?") is not None


def test_unrelated_text_returns_none():
    assert get_identity_reply("chrome kholo") is None
    assert get_identity_reply("kya haal hai") is None


def test_unrelated_founder_mention_is_not_falsely_matched():
    # Must not trigger just because "founder" appears - only when it's
    # clearly a question about Fyz's own identity.
    assert get_identity_reply("Tesla ka founder Elon Musk hai") is None


def test_identity_question_never_reaches_llm_intent_classifier(monkeypatch):
    def _boom(text, context=None):
        raise AssertionError("get_intent should never be called for identity questions")

    monkeypatch.setattr("core.action_executor.dispatch.get_intent", _boom)

    context = ConversationContext()
    reply = handle_utterance("tumhe kis ne banaya?", context)

    assert CREATOR in reply


def test_identity_reply_never_denies_being_the_assistant():
    reply = get_identity_reply("tum kis ke assistant ho?")
    assert "nahi" not in reply.lower()
