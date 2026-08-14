from core.action_executor import router as router_module
from core.action_executor.dispatch import handle_utterance
from core.brain.context import ConversationContext

# Live-Ollama integration test: the classifier is not fully reliable about
# whether "Chrome kholo aur Faizan profile open karo" comes back as a single
# open_browser intent or a multi_step_task split into open_app + open_browser
# (see test_conversation_routing.py). Either way, the end user must only see
# Chrome launched ONCE, with the right profile - this test verifies that
# real guarantee end-to-end rather than pinning to one specific classifier
# output shape. Launch calls are monkeypatched so this never actually spawns
# a real Chrome process during the test run.


def test_chrome_with_profile_request_launches_chrome_exactly_once_with_the_right_profile(monkeypatch):
    calls = []
    monkeypatch.setattr(
        router_module, "open_app",
        lambda name: calls.append(("open_app", name)) or f"Opening {name}.",
    )
    monkeypatch.setattr(
        router_module, "open_chrome_profile",
        lambda hint: calls.append(("open_chrome_profile", hint)) or f"Chrome '{hint}' profile ke saath khol raha hoon bhai 😄",
    )

    context = ConversationContext()
    reply = handle_utterance("Chrome kholo aur Faizan profile open karo", context, confirm_prompt=lambda p: "y")

    profile_calls = [c for c in calls if c[0] == "open_chrome_profile"]
    plain_chrome_opens = [c for c in calls if c[0] == "open_app" and c[1].strip().lower() == "chrome"]

    assert len(profile_calls) == 1
    assert "faizan" in profile_calls[0][1].lower()
    assert len(plain_chrome_opens) == 0
    assert "faizan" in reply.lower()
