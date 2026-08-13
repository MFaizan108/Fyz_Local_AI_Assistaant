import numpy as np

from voice.stt import transcribe


def test_transcribe_empty_audio_returns_empty_string():
    assert transcribe(np.zeros((0,), dtype="float32")) == ""
