from core.action_executor import router
from core.brain.context import ConversationContext
from core.brain.introduction import build_introduction
from core.brain.schemas import Intent
from core.brain.user_profile import FULL_NAME, PREFERRED_NAME


def test_short_introduction_is_brief():
    text = build_introduction(audience="friend", focus="general", level="short")
    assert PREFERRED_NAME in text
    assert len(text.split(".")) <= 3  # roughly 1-2 sentences


def test_medium_introduction_includes_name_education_and_brand():
    text = build_introduction(audience="friend", focus="general", level="medium")
    assert FULL_NAME in text
    assert "FaizanSoft Labs" in text


def test_detailed_introduction_is_longer_than_medium():
    medium = build_introduction(audience="friend", focus="general", level="medium")
    detailed = build_introduction(audience="friend", focus="general", level="detailed")
    assert len(detailed) >= len(medium)


def test_father_audience_has_no_slang_or_bhai():
    text = build_introduction(audience="father", focus="general", level="medium")
    assert "bhai" not in text.lower()


def test_friend_audience_is_casual():
    text = build_introduction(audience="friend", focus="general", level="medium")
    assert "Bhai" in text


def test_coding_focus_mentions_python_and_django():
    text = build_introduction(audience="friend", focus="coding", level="medium")
    assert "Python" in text
    assert "Django" in text


def test_ai_projects_focus_does_not_invent_unregistered_projects():
    text = build_introduction(audience="generic", focus="ai_projects", level="medium")
    # Must only ever mention projects that are genuinely in the registry -
    # never a fabricated one like "Smart Door Lock" that isn't registered.
    assert "Smart Door Lock" not in text


def test_projects_focus_lists_real_registry_projects():
    text = build_introduction(audience="generic", focus="projects", level="medium")
    assert "shamil hain" in text or "kaam kar rahe hain" in text


def test_short_level_still_respects_projects_focus():
    # Regression: build_introduction()'s short-level branches used to
    # ignore `focus` entirely and always return the generic "who is Faizan"
    # blurb, so "mere projects short mein batao" answered as if it were a
    # generic "tell them about me" request instead of naming a project.
    text = build_introduction(audience="generic", focus="projects", level="short")
    assert "kaam kar rahe hain" in text
    assert any(word in text for word in ("Healthcare", "FaizanMart", "System", "TaskFlow"))


def test_short_level_general_focus_stays_generic_and_brief():
    text = build_introduction(audience="generic", focus="general", level="short")
    assert PREFERRED_NAME in text
    assert len(text.split(".")) <= 3


def test_router_dispatches_introduce_user_intent():
    intent = Intent(
        intent="introduce_user",
        raw_text="mera dost mere paas hai, usko mere bare mein batao",
        params={"audience": "friend", "focus": "general", "level": "medium"},
    )
    reply = router.route(intent, ConversationContext(), confirm_prompt=lambda p: "y")
    assert PREFERRED_NAME in reply


def test_router_defaults_missing_params_sensibly():
    intent = Intent(intent="introduce_user", raw_text="x", params={})
    reply = router.route(intent, ConversationContext(), confirm_prompt=lambda p: "y")
    assert FULL_NAME in reply or PREFERRED_NAME in reply
