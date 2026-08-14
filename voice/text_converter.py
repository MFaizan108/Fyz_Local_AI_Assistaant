"""Prepares Fyz's Roman Urdu chat replies for speech.

Two independent jobs live here:

1. `normalize_for_speech()` - strip emoji/decorative symbols and collapse
   whitespace. Used on the GUI-visible text as-is; never changes what's
   shown on screen, only what gets handed to the TTS engine.
2. `roman_urdu_to_urdu_script()` - convert the (already Roman Urdu) reply
   into Urdu (Perso-Arabic) script so Piper's `ur` voice pronounces it as
   real Urdu instead of an English voice sounding out Roman letters.

Roman Urdu has no single standard spelling, so this is deliberately NOT a
lookup table for every possible sentence (that doesn't scale and breaks on
the first unseen phrase). Instead it's a hybrid:

  - a dictionary of the ~100 highest-frequency conversational words (the
    ones Fyz's own persona actually uses constantly - pronouns, verbs,
    question words) get their known-correct Urdu spelling.
  - a small curated whitelist of technical/brand terms (app names, tool
    names, project names Fyz actually manages) are left in Latin script
    rather than guessed into nonsense Urdu spellings - Piper's voice card
    documents mixed Urdu+English input as an explicitly supported (if
    imperfect) case.
  - anything else falls through to a rule-based phonetic transliteration
    (consonant-cluster + vowel mapping) that produces a reasonable, if not
    orthographically perfect, Urdu spelling - good enough for eSpeak's `ur`
    phonemizer to pronounce approximately correctly, which is the actual
    goal (natural pronunciation), not publishable Urdu spelling.
"""

import re
from typing import List

# ---------------------------------------------------------------------------
# 1. Preprocessing shared by every TTS backend
# ---------------------------------------------------------------------------

# Covers the common emoji blocks (emoticons, symbols/pictographs, transport,
# supplemental symbols, dingbats, variation selectors) plus the zero-width
# joiner used in compound emoji. Emojis are for visual emotion in chat/GUI
# text, not meant to be read aloud.
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "\U00002190-\U000021FF"
    "\U00002B00-\U00002BFF"
    "\U0000FE0F"
    "\U0000200D"
    "]+",
    flags=re.UNICODE,
)


def strip_emoji(text: str) -> str:
    return _EMOJI_RE.sub("", text)


def normalize_for_speech(text: str) -> str:
    """GUI-visible text is never touched - this only affects what's handed
    to the TTS engine, called on a copy of the reply, not the displayed
    string itself."""
    text = strip_emoji(text)
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------------------
# 2. Roman Urdu -> Urdu script
# ---------------------------------------------------------------------------

# High-frequency conversational vocabulary - deliberately NOT exhaustive.
# Longer/rarer words fall through to the phonetic engine below.
_WORD_MAP = {
    # pronouns
    "main": "میں", "mein": "میں", "mai": "میں",
    "tum": "تم", "tumhara": "تمہارا", "tumhari": "تمہاری", "tumhare": "تمہارے",
    "tumhe": "تمہیں", "tumhein": "تمہیں",
    "aap": "آپ", "aapka": "آپ کا", "aapki": "آپ کی", "aapke": "آپ کے",
    "mera": "میرا", "meri": "میری", "mere": "میرے", "mujhe": "مجھے",
    "hum": "ہم", "hamara": "ہمارا", "hamari": "ہماری",
    "wo": "وہ", "woh": "وہ", "ye": "یہ", "yeh": "یہ",
    "is": "اس", "us": "اس", "isko": "اسے", "usko": "اسے", "unko": "انہیں",
    "iske": "اس کے", "uske": "اس کے", "inke": "ان کے",
    # question words
    "kya": "کیا", "kia": "کیا", "kyun": "کیوں", "kyu": "کیوں", "kyon": "کیوں",
    "kaise": "کیسے", "kese": "کیسے", "kahan": "کہاں", "kab": "کب",
    "kaun": "کون", "kon": "کون", "konsa": "کونسا", "kitna": "کتنا",
    # verbs / being
    "hai": "ہے", "hain": "ہیں", "hoon": "ہوں", "hun": "ہوں", "ho": "ہو",
    "tha": "تھا", "thi": "تھی", "the": "تھے", "hoga": "ہوگا", "hogi": "ہوگی",
    "karo": "کرو", "karna": "کرنا", "kiya": "کیا", "kholo": "کھولو", "khol": "کھول",
    "batao": "بتاؤ", "bata": "بتا", "chalo": "چلو", "chal": "چل",
    "ruko": "رکو", "ruk": "رک", "dekho": "دیکھو", "dekh": "دیکھ",
    "suno": "سنو", "sun": "سن", "bolo": "بولو", "bol": "بول",
    "likho": "لکھو", "padho": "پڑھو", "samajh": "سمجھ", "pata": "پتا",
    # answers/connectors
    "haan": "ہاں", "ji": "جی", "nahi": "نہیں", "nahin": "نہیں",
    "bhai": "بھائی", "dost": "دوست", "yaar": "یار",
    "theek": "ٹھیک", "thik": "ٹھیک", "acha": "اچھا", "accha": "اچھا", "achha": "اچھا",
    "kaam": "کام", "aur": "اور", "ya": "یا", "lekin": "لیکن", "magar": "مگر",
    "par": "پر", "se": "سے", "ka": "کا", "ke": "کے", "ki": "کی", "ko": "کو",
    "pe": "پہ", "sath": "ساتھ", "saath": "ساتھ", "liye": "لیے", "bhi": "بھی",
    "sab": "سب", "kuch": "کچھ", "kuchh": "کچھ", "sirf": "صرف",
    # time
    "aaj": "آج", "kal": "کل", "abhi": "ابھی", "ab": "اب", "phir": "پھر",
    "waqt": "وقت",
    # place
    "ghar": "گھر", "yahan": "یہاں", "wahan": "وہاں", "idhar": "ادھر", "udhar": "ادھر",
    # misc common
    "haal": "حال", "shukriya": "شکریہ", "maaf": "معاف", "scene": "سین",
    "bara": "بڑا", "bari": "بڑی", "chota": "چھوٹا", "naya": "نیا", "purana": "پرانا",
    "project": "پراجیکٹ", "projects": "پراجیکٹس",
    # common English loanwords Fyz's own fixed reply templates use
    # (core/brain/identity.py's gender reply, general chit-chat) - said
    # often enough in casual Urdu that a Latinized/Urdu-ized loan spelling
    # sounds more natural than either raw phonetic guessing or leaving them
    # in Latin mid-sentence.
    "technically": "ٹیکنیکلی", "biological": "بائیولوجیکل", "gender": "جینڈر",
    "male": "میل", "female": "فی میل", "persona": "پرسونا",
    "check": "چیک", "status": "اسٹیٹس", "test": "ٹیسٹ", "tests": "ٹیسٹس",
    # Faizan's own name + words that show up in nearly every identity/
    # introduction reply (core/brain/identity.py, core/brain/introduction.py)
    # - these are said constantly, so they're worth an exact spelling
    # instead of leaving it to the phonetic fallback's guesswork. Found by
    # actually listening to a live acceptance run and reading the
    # converted output, not guessed in advance.
    "muhammad": "محمد", "faizan": "فیضان", "rahman": "رحمٰن", "ur": "اُر",
    "personal": "پرسنل", "companion": "ساتھی", "local": "لوکل", "hello": "ہیلو",
    "jawab": "جواب", "shamil": "شامل", "kehte": "کہتے",
    "inhein": "انہیں", "unhein": "انہیں",
    "raha": "رہا", "rahi": "رہی", "rahe": "رہے",
    "developer": "ڈویلپر", "software": "سافٹ ویئر", "build": "بلڈ",
    "student": "طالب علم", "enthusiast": "شوقین",
}

# Technical/brand terms left in Latin script rather than guessed into a
# nonsense Urdu spelling - the actual apps/tools/languages Fyz manages
# (tools/app_control/apps.py, tools/project_tools/registry.py tech stacks)
# plus Fyz's own identity terms. Matched case-insensitively.
_TECHNICAL_TERMS = {
    "chrome", "vscode", "vs", "code", "explorer", "notepad",
    "git", "github", "python", "django", "drf", "ollama", "qwen",
    "redis", "elasticsearch", "postgresql", "playwright", "gunicorn",
    "cloudinary", "html", "css", "javascript", "sql", "api", "json",
    "fyz", "faizansoft", "faizanmart", "taskflow", "gsms", "midasbuy",
    "healthcare", "triage", "ai",
    # Words that recur across registered project names/descriptions
    # (tools/project_tools/registry.py) - left in Latin for the same reason
    # as the app/language names above, found from an actual acceptance run
    # where e.g. "Appointment System" got phonetically mangled.
    "backend", "artificial", "intelligence", "appointment", "system",
    "management", "automation", "portfolio", "website", "quiz",
    "generator", "redesign", "practice", "social", "media", "platform",
    "store", "general", "quote", "random", "flashcard", "dental",
    "church", "lane", "birchfields",
}


def _is_technical(word: str) -> bool:
    bare = re.sub(r"[^a-zA-Z0-9]", "", word)
    if not bare:
        return False
    if bare.lower() in _TECHNICAL_TERMS:
        return True
    if any(ch.isdigit() for ch in bare):
        return True
    # CamelCase/mixed-case brand names (e.g. "FaizanMart", "VSCode") - a
    # normal Roman Urdu sentence only ever capitalizes the first letter of
    # a word, so an uppercase letter past position 0 is a strong signal
    # this is a proper noun, not a Roman Urdu word.
    if len(bare) > 1 and any(ch.isupper() for ch in bare[1:]):
        return True
    return False


# Longest-match-first digraph/vowel-cluster rules, then single characters.
# Deliberately approximate (short vowels are mostly omitted mid-word, as
# real undiacritized Urdu text does) - the goal is a reasonable phonemizer
# input, not orthographically "correct" Urdu spelling.
_CLUSTER_RULES = [
    ("kh", "خ"), ("gh", "غ"), ("sh", "ش"), ("ch", "چ"),
    ("ph", "پھ"), ("th", "تھ"), ("dh", "دھ"), ("bh", "بھ"), ("jh", "جھ"),
    ("aa", "ا"), ("ee", "ی"), ("oo", "و"), ("ai", "ے"), ("au", "او"),
]

_SINGLE_MAP = {
    "b": "ب", "p": "پ", "t": "ت", "j": "ج", "d": "د", "r": "ر",
    "z": "ز", "s": "س", "f": "ف", "q": "ق", "k": "ک", "g": "گ",
    "l": "ل", "m": "م", "n": "ن", "w": "و", "v": "و", "h": "ہ",
    "y": "ی", "x": "کس", "c": "ک",
    "e": "ے", "o": "و",
}
_VOWELS = set("aeiou")


def _transliterate_word(word: str) -> str:
    lower = word.lower()
    out: List[str] = []
    i = 0
    n = len(lower)
    is_first = True
    while i < n:
        matched = False
        for cluster, urdu in _CLUSTER_RULES:
            if lower.startswith(cluster, i):
                out.append(urdu)
                i += len(cluster)
                matched = True
                is_first = False
                break
        if matched:
            continue

        ch = lower[i]
        if ch in _VOWELS:
            # Mid-word short vowels are conventionally unwritten in casual
            # Urdu; word-initial ones need an alif carrier so the word
            # doesn't start with an invisible sound.
            if is_first:
                out.append("ا")
            elif ch in ("e", "o"):
                out.append(_SINGLE_MAP[ch])
            # else: omit (short a/i/u mid-word)
        elif ch.isalpha():
            out.append(_SINGLE_MAP.get(ch, ch))
        else:
            out.append(ch)
        i += 1
        is_first = False

    return "".join(out) if out else word


_PUNCT_MAP = str.maketrans({"?": "؟", ",": "،", ";": "؛"})

# Splits on whitespace while keeping punctuation attached to its word, so
# original spacing is preserved when rejoining.
_TOKEN_RE = re.compile(r"\S+|\s+")


def roman_urdu_to_urdu_script(text: str) -> str:
    """Best-effort Roman Urdu -> Urdu script conversion for TTS input only.
    Never raises - falls back to returning the original word on any per-word
    surprise, since partial/imperfect conversion is far better than losing
    the whole utterance."""
    if not text:
        return text

    tokens = _TOKEN_RE.findall(text)
    out_parts: List[str] = []

    for token in tokens:
        if token.isspace():
            out_parts.append(token)
            continue

        leading = re.match(r"^[^\w]*", token).group(0)
        trailing = re.search(r"[^\w]*$", token).group(0)
        core = token[len(leading): len(token) - len(trailing)] if trailing else token[len(leading):]

        if not core:
            out_parts.append(token.translate(_PUNCT_MAP))
            continue

        try:
            if _is_technical(core):
                converted = core
            else:
                converted = _WORD_MAP.get(core.lower())
                if converted is None:
                    converted = _transliterate_word(core)
        except Exception:
            converted = core

        out_parts.append((leading + converted + trailing).translate(_PUNCT_MAP))

    return "".join(out_parts)


def prepare_for_piper(text: str) -> str:
    """Full pipeline from a raw Fyz reply to Piper-ready Urdu-script text:
    strip decorative symbols first (so they don't get mangled by the
    transliterator), then convert. Never affects the GUI-visible text -
    callers pass a copy of the reply, the original stays Roman Urdu."""
    return roman_urdu_to_urdu_script(normalize_for_speech(text))
