import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
# How long Ollama keeps the model loaded in memory after a request. This
# machine runs tight on RAM and Ollama's own default (5m) evicts qwen2.5:7b
# between normal conversational pauses, forcing a ~20-90s cold reload on the
# next message that can exceed the client timeout entirely. 30m keeps it warm
# through a normal session.
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "30m")
# Generation stability. Brain v3 picked 0.4 from a 1-sample-per-temperature
# sweep. Brain v3.1 re-tested 0.6/0.4/0.3 against the CURRENT system prompt
# with 3 samples each on the discriminating case (a "give me a new project
# idea" request) and got a much clearer, reproducible signal than v3's
# single-sample result:
#   - 0.4 reused an EXISTING registered project name ("FaizanMart") in 3/3
#     runs instead of generating a genuinely new idea - not noise, a
#     consistent reasoning slip at this temperature with the current prompt.
#   - 0.6 and 0.3 were both clean (a real new idea) in 3/3 runs each.
#   - Between those two, 0.3 produced one reply with excessive emoji
#     ("🚀🚀🚀") on an unrelated prompt - the exact overuse the persona is
#     explicitly told to avoid - while 0.6 didn't show that failure mode.
# 0.6 is the chosen default. This supersedes v3's 0.4 choice - the earlier
# result didn't hold up under a larger, controlled re-test on the same
# prompt version, which is a useful reminder that a 1-sample sweep is noisy
# enough to reverse on a proper re-test.
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.6"))
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "220"))
# Intent classification only needs a short JSON object, even for a
# multi-step plan (2-3 steps is realistically ~100-150 tokens) - the old
# blanket 350 was more headroom than needed and made every command take
# longer to classify (and therefore more likely to hit a slow/cold-loaded
# read timeout) for no real benefit. 200 stays comfortably above what a
# real multi-step plan needs while cutting typical generation time.
OLLAMA_NUM_PREDICT_INTENT = int(os.getenv("OLLAMA_NUM_PREDICT_INTENT", "200"))
# Split connect vs read timeout instead of one blanket value: connecting to
# a local Ollama instance should be near-instant (a slow/failed connect
# means Ollama isn't running at all, worth failing fast on), while the read
# timeout has to cover a real cold-model-load + generation, which is the
# actual slow part. Previously a single 180s covered both, which meant a
# hung/refused connection took just as long to fail as a legitimate slow
# generation.
OLLAMA_CONNECT_TIMEOUT = float(os.getenv("OLLAMA_CONNECT_TIMEOUT", "10"))
OLLAMA_READ_TIMEOUT = float(os.getenv("OLLAMA_READ_TIMEOUT", "90"))
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")
WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "ur")
# RMS energy level (0.0-1.0 range for float32 audio) above which
# ContinuousListener considers the mic to be picking up speech. This is a
# guess, not calibrated against any specific mic/room - run
# `python voice_main.py --mic-check` to see live levels and tune this if
# always-listening mode isn't detecting speech (raise it) or is triggering
# on background noise (lower it... though usually the fix is to raise it).
VAD_ENERGY_THRESHOLD = float(os.getenv("VAD_ENERGY_THRESHOLD", "0.015"))

# --- TTS (Brain v3.2: Piper Urdu neural voice) ---------------------------
# Master switch - lets voice mode/GUI disable spoken replies entirely
# (e.g. on a machine with no working audio device) without touching the
# rest of the pipeline.
TTS_ENABLED = os.getenv("TTS_ENABLED", "true").lower() == "true"
# Piper gives natural Urdu pronunciation (vs. pyttsx3's English voice
# reading Roman Urdu phonetically, which was the whole reason for this
# migration). Model files are ~64MB and kept out of git (voice/models/ is
# gitignored) - default path assumes the documented download location, but
# both are overridable since the exact install location is a machine/user
# choice, not something to hardcode blindly.
PIPER_ENABLED = os.getenv("PIPER_ENABLED", "true").lower() == "true"
# `or` (not a getenv default) because .env.example ships these blank -
# os.getenv would return "" for a blank-but-present var, which is truthy
# enough to skip the default and break the path.
PIPER_VOICE_PATH = os.getenv("PIPER_VOICE_PATH") or str(
    _PROJECT_ROOT / "voice" / "models" / "piper" / "ur_PK-fasih-medium.onnx"
)
PIPER_CONFIG_PATH = os.getenv("PIPER_CONFIG_PATH") or str(
    _PROJECT_ROOT / "voice" / "models" / "piper" / "ur_PK-fasih-medium.onnx.json"
)
# Explicit opt-in only: if Piper is unavailable (model missing, synthesis
# error) the fallback is silence + a logged error, NOT the old pyttsx3
# English voice - an English voice reading Roman Urdu phonetically is the
# exact bad experience this migration exists to remove, so it must never
# come back silently. Someone can still opt into it deliberately (e.g. for
# a machine where Piper can't run at all) by setting this true.
TTS_FALLBACK_TO_PYTTSX3 = os.getenv("TTS_FALLBACK_TO_PYTTSX3", "false").lower() == "true"

# --- Smart file search (Brain v3.3) ---------------------------------------
# Comma-separated absolute paths. Empty (the default) means "use the
# built-in defaults" (Desktop/Documents/Downloads/OneDrive Desktop) computed
# in tools/file_manager/file_index.py - kept configurable per Part 7's
# requirement without forcing every user to set this just to get sane
# defaults. Deliberately does NOT default to scanning the whole drive.
FILE_INDEX_ROOTS = [p.strip() for p in os.getenv("FILE_INDEX_ROOTS", "").split(",") if p.strip()]
