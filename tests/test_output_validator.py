from core.brain.output_validator import (
    has_excessive_repetition,
    has_known_bad_phrase,
    has_unexpected_script,
    needs_regeneration,
)


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


def test_flags_known_bad_phrase_from_real_bug_report():
    assert has_known_bad_phrase("Kya main aapki faida karta ja sakta hoo?")
    assert has_known_bad_phrase("Mere pass bhi ek mazboot din hogaya!")


def test_flags_propose_improvement_leak_into_conversation():
    assert has_known_bad_phrase('"Kya improve karna hai bata do?" Kuch achi ideas hain...')


def test_allows_natural_phrasing():
    assert not has_known_bad_phrase("Main bhi theek hoon bhai 😄")


def test_flags_excessive_repetition():
    looping = "chalo bhai chalo bhai chalo bhai chalo bhai chalo bhai"
    assert has_excessive_repetition(looping)


def test_allows_normal_length_natural_reply():
    assert not has_excessive_repetition("Hello bhai kya haal hai tum batao aaj kya scene hai")


def test_needs_regeneration_covers_all_signals():
    assert needs_regeneration("你好")
    assert needs_regeneration("Kya main aapki faida karta ja sakta hoo?")
    assert not needs_regeneration("Hello bhai 😄 kya haal hai?")
