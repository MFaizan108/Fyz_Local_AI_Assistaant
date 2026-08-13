import os

from dotenv import load_dotenv

load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")
