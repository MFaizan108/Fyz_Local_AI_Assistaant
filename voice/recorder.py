import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000


def record_until_enter(sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Push-to-talk capture: recording starts immediately and runs in the
    background until the user presses Enter. Returns mono float32 audio."""
    frames = []

    def callback(indata, frame_count, time_info, status):
        frames.append(indata.copy())

    with sd.InputStream(samplerate=sample_rate, channels=1, dtype="float32", callback=callback):
        input()

    if not frames:
        return np.zeros((0,), dtype="float32")

    return np.concatenate(frames, axis=0).flatten()
