from core.brain.normalize import normalize_text


def test_corrects_near_miss_app_name():
    assert normalize_text("crome kholo") == "chrome kholo"


def test_corrects_case_of_known_project_name():
    assert "FaizanMart" in normalize_text("faizanmart kholo")


def test_leaves_unrelated_words_untouched():
    assert normalize_text("kya haal hai") == "kya haal hai"


def test_collapses_whitespace():
    assert normalize_text("  chrome   kholo  ") == "chrome kholo"


def test_empty_string_stays_empty():
    assert normalize_text("") == ""
