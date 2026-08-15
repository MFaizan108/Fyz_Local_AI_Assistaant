import pytest

import memory.db as db_module
from tools.file_manager.file_index import refresh_file_index, smart_search_files


@pytest.fixture()
def sample_tree(tmp_path, monkeypatch):
    """A small, disposable directory tree with a name that's genuinely
    tricky to fuzzy-match (long, multi-word, unrelated first word) - built
    fresh per test so this suite never depends on this machine's real
    Desktop contents. Also points the index at a throwaway SQLite file
    instead of the real memory/fyz.db - refresh_file_index() does a full
    DELETE+rebuild, which would otherwise wipe out this machine's real,
    already-built file index (thousands of real entries) every test run."""
    monkeypatch.setattr(db_module, "DB_PATH", tmp_path / "test_fyz.db")

    root = tmp_path / "Desktop"
    root.mkdir()
    (root / "AI-Powered Healthcare Triage & Appointment System").mkdir()
    (root / "FaizanMart").mkdir()
    (root / "random_notes.txt").write_text("x")
    (root / "ar").mkdir()  # short, locale-code-style name - the false-positive case found live
    (root / "ca").mkdir()

    monkeypatch.setattr("tools.file_manager.file_index.default_roots", lambda: [root])
    refresh_file_index()
    return root


def test_exact_name_matches(sample_tree):
    matches = smart_search_files("FaizanMart")
    assert any(m.name == "FaizanMart" for m in matches)


@pytest.mark.parametrize("query", [
    "healthcare",
    "healtcare",
    "helthcare",
    "health care",
    "healthcare proect",
])
def test_typo_tolerant_matches_still_find_the_healthcare_project(sample_tree, query):
    matches = smart_search_files(query, top_k=5)
    names = [m.name for m in matches]
    assert "AI-Powered Healthcare Triage & Appointment System" in names


def test_short_junk_names_do_not_spuriously_outrank_real_matches(sample_tree):
    """Regression: a 2-letter directory name ("ar") scored 90+ against a
    typo'd query via rapidfuzz's WRatio partial-match bias, found by
    actually running this against a real Desktop before the length filter
    was added - this locks that fix in."""
    matches = smart_search_files("healtcare", top_k=5)
    names = [m.name for m in matches]
    assert "ar" not in names
    assert "ca" not in names


def test_no_match_returns_empty_list(sample_tree):
    matches = smart_search_files("zzzznonexistentqueryzzzz")
    assert matches == []


def test_empty_query_returns_empty_list(sample_tree):
    assert smart_search_files("") == []
    assert smart_search_files("   ") == []


def test_index_persists_across_calls_without_rescanning(sample_tree, monkeypatch):
    calls = {"n": 0}
    from tools.file_manager import file_index as fi_module

    original_scan = fi_module._scan

    def _counting_scan(roots):
        calls["n"] += 1
        return original_scan(roots)

    monkeypatch.setattr(fi_module, "_scan", _counting_scan)

    smart_search_files("FaizanMart")
    smart_search_files("healthcare")
    smart_search_files("random")

    assert calls["n"] == 0  # index already built by the fixture, no rescan needed


def test_refresh_file_index_rebuilds_and_picks_up_new_files(sample_tree):
    (sample_tree / "BrandNewProject").mkdir()
    count = refresh_file_index()

    assert count > 0
    matches = smart_search_files("BrandNewProject")
    assert any(m.name == "BrandNewProject" for m in matches)


def test_refresh_file_index_returns_item_count(sample_tree):
    count = refresh_file_index()
    assert count >= 5  # the 5 real entries created by the fixture
