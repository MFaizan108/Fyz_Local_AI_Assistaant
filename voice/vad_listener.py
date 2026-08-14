import re
import time
from typing import Iterator, Optional

import numpy as np
import sounddevice as sd

from core.config import VAD_ENERGY_THRESHOLD
from voice.recorder import SAMPLE_RATE

CHUNK_MS = 100
SILENCE_DURATION_S = 1.2
MIN_SPEECH_DURATION_S = 0.3
ENERGY_THRESHOLD = VAD_ENERGY_THRESHOLD

_EXIT_WORD_SETS = [{"exit"}, {"quit"}, {"band", "karo"}, {"bye"}, {"stop"}, {"ruk", "jao"}]


def is_exit_phrase(text: str) -> bool:
    """True if the transcribed text is (or contains) a phrase meaning "stop
    listening" - checked as a word subset so a full natural sentence like
    "ok Fyz band karo" still matches, not just the bare phrase alone."""
    words = set(re.findall(r"[a-z]+", text.lower()))
    return any(exit_words <= words for exit_words in _EXIT_WORD_SETS)


def _rms(chunk: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(chunk)))) if chunk.size else 0.0


def print_mic_check(duration_s: float = 12.0, sample_rate: int = SAMPLE_RATE) -> None:
    """Diagnostic: prints the mic device sounddevice will actually use, then
    live RMS energy levels for `duration_s` seconds so you can see whether
    the mic is picking up your voice at all, and what VAD_ENERGY_THRESHOLD
    should be. Run this before assuming always-listening mode is broken -
    if the numbers never move while you talk, it's a device/OS-permission
    issue, not a Fyz bug; if they move but never cross the threshold line,
    lower VAD_ENERGY_THRESHOLD in .env to just under your speaking level."""
    try:
        device_info = sd.query_devices(kind="input")
        print(f"Default input device: {device_info['name']!r}")
    except Exception as e:
        print(f"Couldn't query the default input device: {e}")

    chunk_samples = int(sample_rate * CHUNK_MS / 1000)
    print(f"Current VAD_ENERGY_THRESHOLD = {ENERGY_THRESHOLD}")
    print(f"Bolo, {duration_s:.0f}s tak live energy level dikhega (Ctrl+C to stop early):")

    start = time.monotonic()
    try:
        with sd.InputStream(samplerate=sample_rate, channels=1, dtype="float32") as stream:
            while time.monotonic() - start < duration_s:
                chunk, _ = stream.read(chunk_samples)
                energy = _rms(chunk.flatten())
                bar = "#" * min(int(energy * 500), 50)
                marker = "  <-- ABOVE THRESHOLD (would trigger)" if energy >= ENERGY_THRESHOLD else ""
                print(f"{energy:.4f}  {bar}{marker}")
    except KeyboardInterrupt:
        pass


class ContinuousListener:
    """Always-on mic listening: automatically detects when the user starts
    and stops speaking (simple RMS-energy voice activity detection) instead
    of requiring a manual start/stop for every turn - the "Jarvis" style
    push-to-talk was replacing. ENERGY_THRESHOLD is a rough default and will
    likely need tuning per mic/room - it's the one thing this session can't
    calibrate without actually hearing the real audio levels live."""

    def __init__(
        self,
        sample_rate: int = SAMPLE_RATE,
        energy_threshold: float = ENERGY_THRESHOLD,
        silence_duration: float = SILENCE_DURATION_S,
        min_speech_duration: float = MIN_SPEECH_DURATION_S,
    ):
        self.sample_rate = sample_rate
        self.energy_threshold = energy_threshold
        self.silence_duration = silence_duration
        self.min_speech_duration = min_speech_duration
        self._stop_flag = False

    def stop(self) -> None:
        self._stop_flag = True

    def listen_for_utterances(self) -> Iterator[np.ndarray]:
        """Yields one array of audio per detected utterance, forever, until
        stop() is called."""
        self._stop_flag = False
        while not self._stop_flag:
            audio = self._capture_one_utterance()
            if audio is not None:
                yield audio

    def _capture_one_utterance(self) -> Optional[np.ndarray]:
        chunk_samples = int(self.sample_rate * CHUNK_MS / 1000)
        buffer = []
        speaking = False
        silence_start: Optional[float] = None
        speech_start: Optional[float] = None

        with sd.InputStream(samplerate=self.sample_rate, channels=1, dtype="float32") as stream:
            while not self._stop_flag:
                chunk, _ = stream.read(chunk_samples)
                chunk = chunk.flatten()
                energy = _rms(chunk)

                if energy >= self.energy_threshold:
                    if not speaking:
                        speaking = True
                        speech_start = time.monotonic()
                    buffer.append(chunk)
                    silence_start = None
                elif speaking:
                    buffer.append(chunk)
                    if silence_start is None:
                        silence_start = time.monotonic()
                    elif time.monotonic() - silence_start >= self.silence_duration:
                        duration = time.monotonic() - speech_start
                        if duration >= self.min_speech_duration:
                            return np.concatenate(buffer)
                        return None

        return None
