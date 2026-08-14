import time
from dataclasses import dataclass, field

import numpy as np

import voice.tts as tts_module


@dataclass
class _FakeChunk:
    audio_float_array: np.ndarray
    sample_rate: int = 22050


class _FakeVoice:
    """Stands in for a loaded piper.PiperVoice - never touches the real
    ONNX model or audio hardware, so this suite can verify the queue/worker
    mechanics deterministically and fast."""

    def __init__(self):
        self.synthesized = []

    def synthesize(self, text):
        self.synthesized.append(text)
        yield _FakeChunk(audio_float_array=np.zeros(10, dtype=np.float32))


def _use_fake_voice(monkeypatch, voice=None):
    voice = voice or _FakeVoice()
    monkeypatch.setattr(tts_module, "_get_piper_voice", lambda: voice)
    monkeypatch.setattr(tts_module, "_play_audio", lambda audio, sample_rate: None)
    return voice


def test_multiple_consecutive_replies_are_all_queued_and_spoken_in_order(monkeypatch):
    voice = _use_fake_voice(monkeypatch)

    worker = tts_module._TTSWorker()
    texts = [
        "hello", "tum kon ho?", "mera naam kya hai?", "kya haal hai?",
        "tum male ho?", "mujhe ek project idea do", "Chrome kholo",
        "healthcare project kholo", "iske tests chalao", "acha theek hai",
    ]
    done_order = []
    for t in texts:
        worker.enqueue(t, on_done=lambda t=t: done_order.append(t))

    worker._queue.join()

    # This is the concrete regression check for "only the first reply gets
    # spoken" - every one of 10 consecutive replies must reach synthesis,
    # not just the first.
    assert done_order == texts
    assert len(voice.synthesized) == len(texts)


def test_a_failed_utterance_does_not_block_the_rest_of_the_queue(monkeypatch):
    calls = {"n": 0}

    class _FlakyVoice(_FakeVoice):
        def synthesize(self, text):
            calls["n"] += 1
            if calls["n"] == 2:
                raise RuntimeError("simulated synthesis failure")
            return super().synthesize(text)

    _use_fake_voice(monkeypatch, _FlakyVoice())

    worker = tts_module._TTSWorker()
    done_order = []
    for t in ["first", "second (fails)", "third"]:
        worker.enqueue(t, on_done=lambda t=t: done_order.append(t))

    worker._queue.join()

    # All three on_done callbacks still fire, including the one whose
    # synthesis raised - a TTS failure must not silently swallow later
    # queued replies.
    assert done_order == ["first", "second (fails)", "third"]


def test_speak_enqueues_without_blocking_the_caller(monkeypatch):
    _use_fake_voice(monkeypatch)
    monkeypatch.setattr(tts_module, "_worker", None)

    start = time.monotonic()
    tts_module.speak("this should not block")
    elapsed = time.monotonic() - start

    assert elapsed < 0.1  # speak() returns immediately, the slow part happens on the worker thread


def test_empty_text_still_calls_on_done_without_enqueueing(monkeypatch):
    monkeypatch.setattr(tts_module, "_worker", None)
    called = []
    tts_module.speak("   ", on_done=lambda: called.append(True))
    assert called == [True]


def test_on_done_not_called_before_playback_completes(monkeypatch):
    play_finished_at = {}
    on_done_at = {}

    def slow_play(audio, sample_rate):
        time.sleep(0.05)
        play_finished_at["t"] = time.monotonic()

    voice = _FakeVoice()
    monkeypatch.setattr(tts_module, "_get_piper_voice", lambda: voice)
    monkeypatch.setattr(tts_module, "_play_audio", slow_play)

    worker = tts_module._TTSWorker()
    worker.enqueue("hello", on_done=lambda: on_done_at.setdefault("t", time.monotonic()))
    worker._queue.join()

    assert "t" in play_finished_at and "t" in on_done_at
    assert on_done_at["t"] >= play_finished_at["t"]


def test_piper_unavailable_does_not_crash_and_still_calls_on_done(monkeypatch):
    monkeypatch.setattr(tts_module, "_get_piper_voice", lambda: None)
    monkeypatch.setattr(tts_module, "PIPER_ENABLED", True)
    monkeypatch.setattr(tts_module, "TTS_FALLBACK_TO_PYTTSX3", False)

    worker = tts_module._TTSWorker()
    done = []
    worker.enqueue("hello", on_done=lambda: done.append(True))
    worker._queue.join()

    assert done == [True]  # no exception propagated, queue kept moving


def test_synthesis_exception_does_not_crash_worker(monkeypatch):
    class _CrashingVoice(_FakeVoice):
        def synthesize(self, text):
            raise RuntimeError("boom")

    _use_fake_voice(monkeypatch, _CrashingVoice())

    worker = tts_module._TTSWorker()
    done = []
    worker.enqueue("hello", on_done=lambda: done.append(True))
    worker._queue.join()

    assert done == [True]


def test_pyttsx3_fallback_only_used_when_explicitly_enabled(monkeypatch):
    monkeypatch.setattr(tts_module, "_get_piper_voice", lambda: None)
    monkeypatch.setattr(tts_module, "PIPER_ENABLED", True)

    fallback_calls = []
    monkeypatch.setattr(tts_module, "_speak_with_pyttsx3", lambda text: fallback_calls.append(text))

    monkeypatch.setattr(tts_module, "TTS_FALLBACK_TO_PYTTSX3", False)
    worker = tts_module._TTSWorker()
    worker.enqueue("hello", on_done=None)
    worker._queue.join()
    assert fallback_calls == []  # disabled by default - no silent English-voice fallback

    monkeypatch.setattr(tts_module, "TTS_FALLBACK_TO_PYTTSX3", True)
    worker2 = tts_module._TTSWorker()
    worker2.enqueue("hello", on_done=None)
    worker2._queue.join()
    assert fallback_calls == ["hello"]  # explicit opt-in works


def test_stop_speaking_rejects_new_jobs_after_stop(monkeypatch):
    _use_fake_voice(monkeypatch)

    worker = tts_module._TTSWorker()
    worker.stop()

    done = []
    worker.enqueue("should not be spoken", on_done=lambda: done.append(True))
    # enqueue() after stop() must not hang or silently drop the callback.
    assert done == [True]
