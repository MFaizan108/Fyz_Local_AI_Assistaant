import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000


class Recorder:
    """Explicit start()/stop() mic capture, for callers that can't block on
    stdin to know when to stop (e.g. a GUI mic button toggle)."""

    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate
        self._frames = []
        self._stream = None

    def start(self) -> None:
        self._frames = []

        def callback(indata, frame_count, time_info, status):
            self._frames.append(indata.copy())

        self._stream = sd.InputStream(
            samplerate=self.sample_rate, channels=1, dtype="float32", callback=callback
        )
        self._stream.start()

    def stop(self) -> np.ndarray:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        if not self._frames:
            return np.zeros((0,), dtype="float32")

        return np.concatenate(self._frames, axis=0).flatten()


def record_until_enter(sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Push-to-talk capture for the CLI: recording starts immediately and
    runs until the user presses Enter."""
    recorder = Recorder(sample_rate)
    recorder.start()
    input()
    return recorder.stop()
