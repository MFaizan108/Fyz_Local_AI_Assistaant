from core.action_executor import router
from core.brain.context import ConversationContext
from core.brain.schemas import Intent


def test_open_browser_without_profile_just_opens_chrome(monkeypatch):
    monkeypatch.setattr(router, "open_app", lambda name: f"Opening {name}.")

    intent = Intent(intent="open_browser", target="chrome", params={}, raw_text="chrome kholo")
    context = ConversationContext()

    reply = router.route(intent, context, confirm_prompt=lambda p: "y")

    assert "khol raha hoon" in reply.lower()


def test_open_browser_with_profile_resolves_and_sets_active_context(monkeypatch):
    monkeypatch.setattr(
        router, "open_chrome_profile",
        lambda hint: f"Chrome '{hint}' profile ke saath khol raha hoon bhai 😄",
    )

    intent = Intent(intent="open_browser", target="chrome", params={"profile": "Faizan"}, raw_text="x")
    context = ConversationContext()

    reply = router.route(intent, context, confirm_prompt=lambda p: "y")

    assert "Faizan" in reply
    assert context.active_browser_profile == "Faizan"


def test_open_browser_unresolved_profile_does_not_set_active_context(monkeypatch):
    monkeypatch.setattr(
        router, "open_chrome_profile",
        lambda hint: f"Mujhe '{hint}' naam ka koi Chrome profile nahi mila bhai.",
    )

    intent = Intent(intent="open_browser", target="chrome", params={"profile": "nonexistent"}, raw_text="x")
    context = ConversationContext()

    router.route(intent, context, confirm_prompt=lambda p: "y")

    assert context.active_browser_profile is None


def test_open_browser_unsupported_browser():
    intent = Intent(intent="open_browser", target="firefox", params={}, raw_text="x")
    context = ConversationContext()

    reply = router.route(intent, context, confirm_prompt=lambda p: "y")

    assert "chrome" in reply.lower()
