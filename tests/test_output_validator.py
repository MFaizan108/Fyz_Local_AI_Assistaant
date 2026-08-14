from core.brain.output_validator import has_unexpected_script


def test_flags_devanagari():
    assert has_unexpected_script("मुझे समझ नहीं आया")


def test_flags_chinese():
    assert has_unexpected_script("你好")


def test_flags_japanese():
    assert has_unexpected_script("こんにちは")


def test_flags_korean():
    assert has_unexpected_script("안녕하세요")


def test_flags_cyrillic():
    assert has_unexpected_script("Привет")


def test_flags_real_arabic_urdu_script():
    assert has_unexpected_script("کروم کھولو")


def test_flags_mixed_script_regression_case():
    # This exact pattern is what the user actually hit in production.
    assert has_unexpected_script("筒پا! मुमशीर फ़ाइज़ान उर रहमान")


def test_allows_roman_urdu_with_emoji():
    assert not has_unexpected_script("Sab theek hai bhai! 😄 Chalte hain 🚀")


def test_allows_english_technical_terms():
    assert not has_unexpected_script("VS Code mein Django ka error hai, API check karo.")


def test_allows_plain_punctuation_and_numbers():
    assert not has_unexpected_script("Step 1: chrome.exe - 2 tabs open hain, theek hai?")
