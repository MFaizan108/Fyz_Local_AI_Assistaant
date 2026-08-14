from voice.text_converter import normalize_for_speech, prepare_for_piper, roman_urdu_to_urdu_script, strip_emoji


def test_emoji_stripped_for_speech():
    assert strip_emoji("Main theek hoon bhai 😄") == "Main theek hoon bhai "


def test_normalize_for_speech_does_not_mutate_caller_string():
    # Sanity check that these are pure functions - the GUI's displayed
    # reply must never be affected by what gets sent to TTS.
    original = "Main theek hoon bhai 😄"
    result = normalize_for_speech(original)
    assert original == "Main theek hoon bhai 😄"
    assert result != original


def test_spec_example_matches_exactly():
    # The exact before/after pair given in the Brain v3.2 spec.
    text = "Main theek hoon bhai, batao kya scene hai?"
    assert prepare_for_piper(text) == "میں ٹھیک ہوں بھائی، بتاؤ کیا سین ہے؟"


def test_common_words_convert_to_expected_urdu():
    cases = {
        "main": "میں", "tum": "تم", "aap": "آپ", "bhai": "بھائی",
        "kya": "کیا", "kia": "کیا", "hai": "ہے", "haan": "ہاں",
        "nahi": "نہیں", "theek": "ٹھیک", "kaam": "کام", "karo": "کرو",
        "kholo": "کھولو", "batao": "بتاؤ", "mujhe": "مجھے",
        "tumhara": "تمہارا", "mera": "میرا", "aaj": "آج", "kal": "کل",
    }
    for roman, urdu in cases.items():
        assert roman_urdu_to_urdu_script(roman) == urdu, roman


def test_technical_terms_stay_in_latin_script():
    for phrase in ["Chrome kholo", "VS Code kholo", "git status check karo"]:
        converted = prepare_for_piper(phrase)
        assert any(word in converted for word in ["Chrome", "VS", "Code", "git"])


def test_project_name_stays_in_latin_not_transliterated():
    # "FaizanMart" is a brand name - transliterating it phonetically into
    # an invented Urdu spelling would be nonsense speech for a proper noun.
    converted = prepare_for_piper("FaizanMart kholo")
    assert "FaizanMart" in converted


def test_healthcare_project_kholo_produces_reasonable_output():
    converted = prepare_for_piper("Healthcare project kholo")
    assert "Healthcare" in converted
    assert "کھولو" in converted  # "kholo" converted correctly


def test_conversion_never_raises_on_arbitrary_input():
    edge_cases = ["", "   ", "???", "123 456", "already Urdu: بھائی", "a", "XYZ_weird-input!!"]
    for text in edge_cases:
        prepare_for_piper(text)  # must not raise


def test_conversion_produces_urdu_script_characters():
    converted = prepare_for_piper("Tum kon ho?")
    assert any("؀" <= ch <= "ۿ" for ch in converted)


def test_gender_persona_reply_converts_without_nonsense_crash():
    reply = (
        "Technically main AI hoon bhai, is liye mera biological gender nahi "
        "hai lekin tum mujhe male persona samajh sakte ho."
    )
    converted = prepare_for_piper(reply)
    assert converted  # non-empty
    assert "AI" in converted  # short acronym left as-is
