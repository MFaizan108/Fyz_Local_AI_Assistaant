from functools import lru_cache

import pyttsx3


@lru_cache(maxsize=1)
def _get_engine() -> pyttsx3.Engine:
    return pyttsx3.init()


def speak(text: str) -> None:
    text = text.strip()
    if not text:
        return

    engine = _get_engine()
    engine.say(text)
    engine.runAndWait()


def speak_to_file(text: str, path: str) -> None:
    engine = _get_engine()
    engine.save_to_file(text, path)
    engine.runAndWait()
