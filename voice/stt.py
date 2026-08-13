from functools import lru_cache

import numpy as np
from faster_whisper import WhisperModel

from core.config import WHISPER_LANGUAGE, WHISPER_MODEL_SIZE


@lru_cache(maxsize=1)
def _get_model() -> WhisperModel:
    return WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")


def transcribe(audio: np.ndarray, language: str = WHISPER_LANGUAGE) -> str:
    """Defaults to a fixed language (Urdu) rather than auto-detection.
    Auto-detect is unreliable on short clips and was frequently
    misdetecting Faizan's Urdu as a related language, garbling the
    transcription. Pass language=None explicitly to fall back to
    auto-detect for a specific call if needed."""
    if audio.size == 0:
        return ""

    model = _get_model()
    segments, _ = model.transcribe(audio, language=language)
    return " ".join(segment.text.strip() for segment in segments).strip()
