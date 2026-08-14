from core.action_executor.dispatch import handle_utterance
from core.brain.context import ConversationContext
from core.brain.identity import PERSONA_GENDER, get_identity_reply


def test_gender_question_variants_are_deterministic():
    for q in ["tum male ho yaa female", "tumhara gender kya hai", "tum ladka ho ya ladki"]:
        reply = get_identity_reply(q)
        assert reply is not None
        assert PERSONA_GENDER in reply


def test_gender_reply_does_not_claim_a_biological_fact():
    reply = get_identity_reply("tum male ho ya female")
    assert "biological gender nahi hai" in reply.lower() or "biological" in reply.lower()


def test_unrelated_text_does_not_trigger_gender_reply():
    assert get_identity_reply("Chrome kholo") is None


def test_gender_question_never_reaches_llm_intent_classifier(monkeypatch):
    def _boom(text, context=None):
        raise AssertionError("get_intent should never be called for a deterministic persona question")

    monkeypatch.setattr("core.action_executor.dispatch.get_intent", _boom)

    context = ConversationContext()
    reply = handle_utterance("tum male ho ya female?", context)

    assert PERSONA_GENDER in reply
