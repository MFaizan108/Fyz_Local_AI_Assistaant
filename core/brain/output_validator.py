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


# Concrete broken/artificial phrases seen in real production output (Brain
# v3 bug report) - not grammatically Urdu, just a stiff word-for-word
# translation pattern the model falls into. Cheap substring check, not a
# grammar checker - deliberately narrow so it only catches known bad
# patterns rather than second-guessing normal replies.
_KNOWN_BAD_PHRASES = (
    "faida karta ja sakta",
    "mazboot din hogaya",
    "mazboot din ho gaya",
    "aasmaan bana deta",
    "kis prakar sahayata",
    "aapki seva mein",
    # Leaks from the propose_improvement clarification flow into ordinary
    # conversation (e.g. a project-idea request) - the model occasionally
    # leads with this before self-correcting into an actual answer. Caught
    # here so the retry regenerates a clean reply instead of keeping the
    # confused preamble.
    "kya improve karna hai",
)


def has_known_bad_phrase(text: str) -> bool:
    norm = text.lower()
    return any(p in norm for p in _KNOWN_BAD_PHRASES)


def has_excessive_repetition(text: str) -> bool:
    """True if the same 3-word phrase repeats 3+ times - a cheap signal for
    a generation that's gotten stuck looping rather than actually
    replying. Short replies (Fyz's normal case) never trigger this."""
    words = text.lower().split()
    if len(words) < 9:
        return False
    seen = {}
    for i in range(len(words) - 2):
        trigram = " ".join(words[i:i + 3])
        seen[trigram] = seen.get(trigram, 0) + 1
        if seen[trigram] >= 3:
            return True
    return False


def needs_regeneration(text: str) -> bool:
    """Umbrella check used by the chat pipeline to decide whether a raw
    reply should be retried: wrong script, a known broken/artificial
    phrase, or the model looping on itself. Deliberately NOT an attempt at
    a full grammar/quality checker - lightweight heuristics only, backed by
    the same one-retry-then-fallback flow either way."""
    return has_unexpected_script(text) or has_known_bad_phrase(text) or has_excessive_repetition(text)
