from core.action_executor.dispatch import handle_utterance
from core.brain.context import ConversationContext
from core.brain.introduction import looks_like_introduction_request
from core.brain.schemas import Intent


def test_bhai_ko_batao_is_detected_as_introduction_request():
    assert looks_like_introduction_request("meray bhai ko mera batao main kon hoon?")


def test_dost_ko_batao_main_kon_hoon_is_detected():
    assert looks_like_introduction_request("mere dost ko batao main kon hoon")


def test_cousin_ko_batao_is_detected():
    assert looks_like_introduction_request("cousin ko batao")


def test_abu_ko_batao_is_detected():
    assert looks_like_introduction_request("abu ko batao")


def test_kisi_ko_introduction_do_is_detected():
    assert looks_like_introduction_request("kisi ko mera introduction do")


def test_usko_batao_is_detected():
    assert looks_like_introduction_request("usko batao main kya karta hoon")


def test_unko_projects_ke_bare_mein_batao_is_detected():
    assert looks_like_introduction_request("unko mere projects ke bare mein batao")


def test_bare_who_am_i_is_not_an_introduction_request():
    assert not looks_like_introduction_request("main kon hoon?")
    assert not looks_like_introduction_request("mera naam kya hai?")


def test_unrelated_text_is_not_an_introduction_request():
    assert not looks_like_introduction_request("chrome kholo")
    assert not looks_like_introduction_request("kya haal hai")


def test_bare_who_am_i_still_uses_the_deterministic_fast_path(monkeypatch):
    """Regression guard: the fix must not make EVERY identity question go
    through the slower LLM path - only ones with an introduction audience
    cue should skip the fast path."""

    def _boom(text, context=None):
        raise AssertionError("get_intent should never be called for a bare identity question")

    monkeypatch.setattr("core.action_executor.dispatch.get_intent", _boom)

    context = ConversationContext()
    reply = handle_utterance("main kon hoon?", context)

    assert "Muhammad Faizan Ur Rahman" in reply


def test_introduction_request_skips_the_deterministic_fast_path(monkeypatch):
    """The core regression: "meray bhai ko mera batao main kon hoon?" must
    NOT be answered by the bare who-am-i fast path - it must reach full
    intent classification so introduce_user can be selected."""
    reached_classifier = {"called": False}

    def _fake_get_intent(text, context=None):
        reached_classifier["called"] = True
        return Intent(
            intent="introduce_user",
            raw_text=text,
            params={"audience": "friend", "focus": "general", "level": "medium"},
        )

    monkeypatch.setattr("core.action_executor.dispatch.get_intent", _fake_get_intent)

    context = ConversationContext()
    reply = handle_utterance("meray bhai ko mera batao main kon hoon?", context)

    assert reached_classifier["called"] is True
    # Should NOT be the plain who-am-i deterministic reply's exact wording.
    assert "aur main tumhara personal AI companion hoon" not in reply
