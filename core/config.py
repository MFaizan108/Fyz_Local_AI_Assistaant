import os

from dotenv import load_dotenv

load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
# How long Ollama keeps the model loaded in memory after a request. This
# machine runs tight on RAM and Ollama's own default (5m) evicts qwen2.5:7b
# between normal conversational pauses, forcing a ~20-90s cold reload on the
# next message that can exceed the client timeout entirely. 30m keeps it warm
# through a normal session.
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "30m")
# Generation stability. Brain v3 experimented with 0.6/0.4/0.3/0.2 against
# the same set of realistic Roman Urdu prompts (greeting, mood exchange,
# humor, a project-idea request) before picking a default:
#   - 0.6 and 0.3 both reused an EXISTING registered project name
#     ("FaizanMart") when asked for a NEW project idea, instead of actually
#     generating one - a subtle reasoning slip, not a script/grammar issue.
#   - 0.4 and 0.2 both generated a genuinely new idea each time; 0.2 was the
#     tightest/cleanest but risks over-fitting to the system prompt's own
#     few-shot examples (near-verbatim phrasing) over many turns, and cuts
#     down the natural variation a dost-like persona should have.
# 0.4 is the chosen default: as stable as 0.2 on the hardest test case
# (project ideas) without going as low as 0.2 and losing natural variety.
# Not an exhaustive study (one sample per temperature) - if a future session
# has time, re-run scratchpad/temp_experiment-style sweeps with more samples
# per temperature before changing this again.
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.4"))
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "220"))
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
