from dataclasses import dataclass

from core.action_executor import router as router_module
from core.brain.context import ConversationContext
from core.brain.schemas import Intent


@dataclass
class _FakeMatch:
    name: str
    path: str
    type: str = "dir"
    score: float = 0.0


def _search_intent(target: str) -> Intent:
    return Intent(intent="search_files", raw_text="x", target=target, params={})


def test_no_target_asks_what_to_search():
    reply = router_module.route(_search_intent(""), ConversationContext(), confirm_prompt=lambda p: "y")
    assert "kaunsi" in reply.lower() or "konsi" in reply.lower() or "file" in reply.lower()


def test_single_confident_match_reports_it_directly(monkeypatch):
    monkeypatch.setattr(
        router_module, "smart_search_files",
        lambda query, top_k=5: [_FakeMatch("AI-Powered Healthcare Triage & Appointment System", "C:/x/healthcare", score=90)],
    )
    reply = router_module.route(_search_intent("healtcare"), ConversationContext(), confirm_prompt=lambda p: "y")
    assert "AI-Powered Healthcare Triage & Appointment System" in reply


def test_clearly_best_match_wins_even_with_other_lower_scored_results(monkeypatch):
    monkeypatch.setattr(
        router_module, "smart_search_files",
        lambda query, top_k=5: [
            _FakeMatch("AI-Powered Healthcare Triage & Appointment System", "C:/x/healthcare", score=95),
            _FakeMatch("health", "C:/x/health", score=60),
        ],
    )
    reply = router_module.route(_search_intent("healthcare"), ConversationContext(), confirm_prompt=lambda p: "y")
    assert "AI-Powered Healthcare Triage & Appointment System" in reply
    assert "konsa" not in reply.lower()  # should not ask for clarification


def test_ambiguous_close_scores_asks_for_clarification(monkeypatch):
    monkeypatch.setattr(
        router_module, "smart_search_files",
        lambda query, top_k=5: [
            _FakeMatch("Healthcare API", "C:/x/a", score=80),
            _FakeMatch("AI Healthcare Triage", "C:/x/b", score=78),
        ],
    )
    reply = router_module.route(_search_intent("healthcare"), ConversationContext(), confirm_prompt=lambda p: "y")
    assert "Healthcare API" in reply
    assert "AI Healthcare Triage" in reply
    assert "konsa" in reply.lower() or "konse" in reply.lower()


def test_no_smart_match_falls_back_to_legacy_substring_search(monkeypatch):
    monkeypatch.setattr(router_module, "smart_search_files", lambda query, top_k=5: [])
    monkeypatch.setattr(router_module, "search_files", lambda query: ["C:/x/found_via_legacy.txt"])

    reply = router_module.route(_search_intent("found_via_legacy"), ConversationContext(), confirm_prompt=lambda p: "y")

    assert "found_via_legacy.txt" in reply


def test_no_match_at_all_says_so_naturally(monkeypatch):
    monkeypatch.setattr(router_module, "smart_search_files", lambda query, top_k=5: [])
    monkeypatch.setattr(router_module, "search_files", lambda query: [])

    reply = router_module.route(_search_intent("zzzznonexistentzzzz"), ConversationContext(), confirm_prompt=lambda p: "y")

    assert "nahi mila" in reply.lower() or "not found" in reply.lower() or "no files" in reply.lower()


def test_refresh_file_index_reports_item_count(monkeypatch):
    monkeypatch.setattr(router_module, "refresh_file_index", lambda: 1234)
    intent = Intent(intent="refresh_file_index", raw_text="files refresh karo", target=None, params={})
    reply = router_module.route(intent, ConversationContext(), confirm_prompt=lambda p: "y")
    assert "1234" in reply
