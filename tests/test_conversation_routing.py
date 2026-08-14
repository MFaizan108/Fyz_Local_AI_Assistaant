from core.brain.brain import get_intent

# Live-Ollama integration tests, same convention as test_ollama_connection.py -
# checks that casual conversation and real commands land on the correct side
# of the conversation/command split.


def test_greeting_routes_to_chat():
    intent = get_intent("hello")
    assert intent.intent == "chat"


def test_casual_question_routes_to_chat():
    intent = get_intent("kya haal hai?")
    assert intent.intent == "chat"


def test_known_app_command_routes_to_open_app():
    intent = get_intent("Chrome kholo")
    assert intent.intent == "open_app"
    assert intent.target == "chrome"


def test_project_idea_request_routes_to_chat_not_propose_improvement():
    # Regression test: this used to misclassify as propose_improvement
    # (Fyz's own self-modification tool) purely because the message
    # mentions "project", producing "Kya improve karna hai, bata do."
    # instead of actually answering the request.
    intent = get_intent("mujhay koi realistic life problem k solution k liay project batao")
    assert intent.intent == "chat"


def test_chrome_with_named_profile_mentions_the_profile():
    # The classifier sometimes returns a single open_browser intent and
    # sometimes splits it into a multi_step_task (open_app + open_browser)
    # despite being told not to - either way, the profile must be captured
    # somewhere in the plan. See test_chrome_profile_end_to_end.py for the
    # test that this doesn't cause Chrome to actually launch twice.
    intent = get_intent("Chrome kholo aur Faizan profile open karo")
    if intent.intent == "open_browser":
        assert "faizan" in (intent.params.get("profile") or "").lower()
    else:
        assert intent.intent == "multi_step_task"
        profiles = [
            (step.get("params") or {}).get("profile", "")
            for step in (intent.steps or [])
            if step.get("intent") == "open_browser"
        ]
        assert any("faizan" in p.lower() for p in profiles)


def test_current_project_query_routes_correctly():
    intent = get_intent("main kis project par kaam kar raha hoon?")
    assert intent.intent == "current_project_query"


def test_project_info_request_routes_correctly():
    intent = get_intent("healthcare project kya karta hai?")
    assert intent.intent == "project_info"
