from functools import lru_cache

import numpy as np
from faster_whisper import WhisperModel

from core.config import WHISPER_MODEL_SIZE


@lru_cache(maxsize=1)
def _get_model() -> WhisperModel:
    return WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")


def transcribe(audio: np.ndarray) -> str:
    if audio.size == 0:
        return ""

    model = _get_model()
    segments, _ = model.transcribe(audio, language=None)
    return " ".join(segment.text.strip() for segment in segments).strip()
