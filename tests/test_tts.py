import os
import tempfile

from voice.tts import speak_to_file


def test_speak_to_file_produces_nonempty_audio():
    path = os.path.join(tempfile.gettempdir(), "fyz_test_tts_output.wav")
    speak_to_file("Fyz test phrase.", path)
    assert os.path.getsize(path) > 1000
