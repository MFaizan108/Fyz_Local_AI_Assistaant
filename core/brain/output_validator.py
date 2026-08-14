"""Guards against Fyz's chat replies drifting into an unexpected script.
Fyz's persona is Roman Urdu only (Latin alphabet) - qwen2.5:7b is a
multilingual model and occasionally drifts into Devanagari, CJK, Hangul,
Cyrillic, or real Arabic/Urdu script mid-reply, especially on longer
generations. This is checked, not assumed away by prompting alone."""

_DISALLOWED_RANGES = (
    (0x0600, 0x06FF),  # Arabic (includes real Urdu script)
    (0x0750, 0x077F),  # Arabic Supplement
    (0xFB50, 0xFDFF),  # Arabic Presentation Forms-A
    (0xFE70, 0xFEFF),  # Arabic Presentation Forms-B
    (0x0900, 0x097F),  # Devanagari
    (0x3040, 0x309F),  # Hiragana
    (0x30A0, 0x30FF),  # Katakana
    (0x3400, 0x4DBF),  # CJK Unified Ideographs Extension A
    (0x4E00, 0x9FFF),  # CJK Unified Ideographs
    (0xAC00, 0xD7A3),  # Hangul syllables
    (0x1100, 0x11FF),  # Hangul Jamo
    (0x0400, 0x04FF),  # Cyrillic
)


def has_unexpected_script(text: str) -> bool:
    """True if `text` contains any character from a script other than Latin
    (Roman Urdu/English), digits, punctuation, or emoji."""
    for ch in text:
        cp = ord(ch)
        for start, end in _DISALLOWED_RANGES:
            if start <= cp <= end:
                return True
    return False
