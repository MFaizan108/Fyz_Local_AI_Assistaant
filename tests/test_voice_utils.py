from voice.tts import strip_emoji
from voice.vad_listener import is_exit_phrase


def test_strip_emoji_removes_emoji_keeps_text():
    result = strip_emoji("Sab theek hai bhai! 😄 Chalte hain 🚀")
    assert "😄" not in result
    assert "🚀" not in result
    assert "Sab theek hai bhai!" in result


def test_strip_emoji_leaves_plain_text_untouched():
    assert strip_emoji("Opening Chrome.") == "Opening Chrome."


def test_is_exit_phrase_matches_bare_word():
    assert is_exit_phrase("exit")
    assert is_exit_phrase("stop")


def test_is_exit_phrase_matches_within_a_sentence():
    assert is_exit_phrase("ok Fyz band karo ab")
    assert is_exit_phrase("theek hai bye")


def test_is_exit_phrase_does_not_match_unrelated_text():
    assert not is_exit_phrase("chrome kholo")
    assert not is_exit_phrase("kya haal hai")
