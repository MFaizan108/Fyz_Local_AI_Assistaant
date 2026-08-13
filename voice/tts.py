import re
from functools import lru_cache

import pyttsx3

# Covers the common emoji blocks (emoticons, symbols/pictographs, transport,
# supplemental symbols, dingbats, variation selectors) plus the zero-width
# joiner used in compound emoji. Emojis are for visual emotion in chat/GUI
# text, not meant to be read aloud - pyttsx3 otherwise spells out their
# Unicode names ("smiling face with smiling eyes"), which is worse than
# just skipping them.
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


@lru_cache(maxsize=1)
def _get_engine() -> pyttsx3.Engine:
    return pyttsx3.init()


def speak(text: str) -> None:
    text = strip_emoji(text).strip()
    if not text:
        return

    engine = _get_engine()
    engine.say(text)
    engine.runAndWait()


def speak_to_file(text: str, path: str) -> None:
    text = strip_emoji(text).strip()
    engine = _get_engine()
    engine.save_to_file(text, path)
    engine.runAndWait()
