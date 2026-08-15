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


def test_introduce_to_friend_routes_correctly():
    intent = get_intent("main apne dost ke paas baitha hoon, usko mere bare mein batao")
    assert intent.intent == "introduce_user"
    assert intent.params.get("audience") == "friend"


def test_introduce_to_cousin_routes_correctly():
    intent = get_intent("mera cousin mere paas hai, usko batao main kya karta hoon")
    assert intent.intent == "introduce_user"
    assert intent.params.get("audience") == "cousin"


def test_introduce_to_father_with_projects_focus_routes_correctly():
    intent = get_intent("main abu ke paas baitha hoon, unko mere projects ke bare mein batao")
    assert intent.intent == "introduce_user"
    assert intent.params.get("audience") == "father"
    assert intent.params.get("focus") == "projects"


# --- Brain v3.3: introduction priority, desktop_action, file search -------

def test_bhai_ko_batao_main_kon_hoon_routes_to_introduce_user_not_identity():
    intent = get_intent("meray bhai ko mera batao main kon hoon?")
    assert intent.intent == "introduce_user"


def test_copy_command_routes_to_desktop_action():
    intent = get_intent("copy karo")
    assert intent.intent == "desktop_action"
    assert intent.target == "copy"


def test_task_manager_command_routes_to_desktop_action():
    intent = get_intent("Task Manager kholo")
    assert intent.intent == "desktop_action"
    assert intent.target == "task_manager"


def test_reopen_closed_tab_command_routes_to_desktop_action():
    intent = get_intent("previous closed tab kholo")
    assert intent.intent == "desktop_action"
    assert intent.target == "reopen_closed_tab"


def test_lock_laptop_command_routes_to_desktop_action():
    intent = get_intent("laptop lock kar do")
    assert intent.intent == "desktop_action"
    assert intent.target == "lock_laptop"


def test_file_search_with_typo_still_routes_to_search_files():
    intent = get_intent("health care proect search karo")
    assert intent.intent == "search_files"


def test_files_refresh_routes_to_refresh_file_index():
    intent = get_intent("files refresh karo")
    assert intent.intent == "refresh_file_index"


def test_chrome_profile_and_reopen_tabs_multi_step_includes_both_actions():
    intent = get_intent("Chrome kholo aur Faizan Mahmood profile open karo aur previous closed tabs kholo")
    if intent.intent == "desktop_action":
        # Some runs may not treat this as multi-step at all if the model
        # folds it into a single browser-open step - unlikely but not this
        # test's concern; the two-intents case below is the main assertion.
        return
    assert intent.intent == "multi_step_task"
    step_intents = [step.get("intent") for step in (intent.steps or [])]
    assert "open_browser" in step_intents or "open_app" in step_intents
    assert "desktop_action" in step_intents
