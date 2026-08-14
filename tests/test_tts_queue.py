import voice.tts as tts_module


class _FakeEngine:
    """Stands in for pyttsx3.init()'s real engine - never touches real
    audio hardware, so this test suite can verify the queue/worker
    mechanics without actually speaking."""

    def __init__(self):
        self.said = []

    def say(self, text):
        self.said.append(text)

    def runAndWait(self):
        pass

    def stop(self):
        pass


def test_multiple_consecutive_replies_are_all_queued_and_spoken_in_order(monkeypatch):
    engines = []

    def fake_init():
        engine = _FakeEngine()
        engines.append(engine)
        return engine

    monkeypatch.setattr(tts_module.pyttsx3, "init", fake_init)

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
    # spoken" - every one of 10 consecutive replies must reach a real
    # engine.say() call, not just the first.
    assert done_order == texts
    assert [e.said[0] for e in engines] == texts
    assert len(engines) == len(texts)  # a fresh engine per utterance, not one reused/shared instance


def test_a_failed_utterance_does_not_block_the_rest_of_the_queue(monkeypatch):
    calls = {"n": 0}

    def flaky_init():
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("simulated engine failure")
        return _FakeEngine()

    monkeypatch.setattr(tts_module.pyttsx3, "init", flaky_init)

    worker = tts_module._TTSWorker()
    done_order = []
    for t in ["first", "second (fails)", "third"]:
        worker.enqueue(t, on_done=lambda t=t: done_order.append(t))

    worker._queue.join()

    # All three on_done callbacks still fire, including the one whose
    # engine.init() raised - a TTS failure must not silently swallow later
    # queued replies.
    assert done_order == ["first", "second (fails)", "third"]


def test_speak_enqueues_without_blocking_the_caller(monkeypatch):
    import time

    class _SlowEngine(_FakeEngine):
        def runAndWait(self):
            time.sleep(0.3)

    monkeypatch.setattr(tts_module.pyttsx3, "init", lambda: _SlowEngine())
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
