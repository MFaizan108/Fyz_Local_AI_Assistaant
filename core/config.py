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
# Generation stability: no temperature/num_predict were ever set before,
# meaning Ollama used the model's own (fairly high) default sampling - a
# contributing factor to replies occasionally drifting into an unrelated
# script (Devanagari/CJK/etc.) on longer generations. 0.6 keeps replies
# consistent without making them robotic/repetitive; num_predict caps reply
# length, which both matches the "short and natural" persona and reduces how
# much room a generation has to drift before it's cut off.
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.6"))
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
