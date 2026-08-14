# Fyz

Fyz is a local, Roman-Urdu-speaking AI companion for your laptop — a Jarvis-style
assistant that runs entirely on-device (Ollama + Whisper), remembers things about
you and your projects, can open apps/projects, run tests, check git status, take
screenshots, manage files, and even propose changes to its own code in a sandboxed
git worktree.

No cloud APIs. No accounts. Everything — the LLM, the speech-to-text, the memory
database — runs locally.

## Features

- **Roman Urdu conversation** — chats like a dost (friend), not a formal assistant.
- **Voice mode** — always-listening (Jarvis-style, no wake word/button) or push-to-talk,
  with Urdu speech recognition (faster-whisper) and spoken replies (pyttsx3).
- **Desktop GUI** (PySide6) and a plain text CLI, both driven by the same backend.
- **Project registry** — knows your projects by name/alias; can open them in VS Code,
  run their test suite, or check `git status`, all in natural language.
- **Long-term + semantic memory** — remembers things you tell it to, and can recall
  them later by meaning, not just shared keywords (Ollama embeddings, SQLite).
- **Permission-tiered tools** — every action Fyz can take is tagged SAFE / CONFIRM /
  DANGEROUS; destructive actions (deleting files, killing processes) always ask first.
- **Self-improvement sandbox** — Fyz can propose a change to its own codebase, test it
  in an isolated git worktree/branch, and only merge it after you explicitly confirm.

## Requirements

- Windows (paths/console handling in this repo assume Windows; may need small tweaks
  elsewhere).
- Python 3.10+
- [Ollama](https://ollama.com) installed and running locally, with these models pulled:
  ```
  ollama pull qwen2.5:7b
  ollama pull nomic-embed-text
  ```
- A working microphone (for voice mode only — the CLI/GUI text chat works without one).

## Setup

```bash
# from the project root
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

copy .env.example .env
```

`.env` controls the model names, Ollama host, Whisper settings, and mic sensitivity —
see [Configuration](#configuration) below. Defaults work out of the box if Ollama is
running on `localhost:11434`.

Make sure Ollama is running before starting Fyz:

```bash
ollama serve
```

## Running Fyz

| Mode | Command | Notes |
|---|---|---|
| Text chat (CLI) | `python main.py` | Type `exit` to quit. No mic needed. |
| Desktop GUI | `python gui_main.py` | Text + voice, mic button or always-listening. |
| Voice (always-listening) | `python voice_main.py` | Default mode — no button, just talk. Say "band karo" / "stop" / "exit" / "bye" to end. |
| Voice (push-to-talk) | `python voice_main.py --push-to-talk` | Press Enter to talk, Enter again to stop. Use this if always-listening isn't detecting you reliably. |
| Mic diagnostic | `python voice_main.py --mic-check` | Prints your default input device and live mic energy levels for 12s — use this to tune `VAD_ENERGY_THRESHOLD` if voice mode isn't hearing you. |

## Configuration

All settings live in `.env` (copy from `.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `OLLAMA_HOST` | `http://localhost:11434` | Where Ollama is running. |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Chat/reasoning model. |
| `OLLAMA_KEEP_ALIVE` | `30m` | How long Ollama keeps the model loaded between requests. Raise this on low-RAM machines to avoid slow cold-reload timeouts between messages. |
| `EMBED_MODEL` | `nomic-embed-text` | Embedding model for semantic memory search. |
| `WHISPER_MODEL_SIZE` | `base` | faster-whisper model size (`tiny`/`base`/`small`/...). Larger = more accurate but slower/heavier; make sure the model fully downloads before switching. |
| `WHISPER_LANGUAGE` | `ur` | Language Whisper is forced to transcribe as. Change only if you'll be speaking mostly English. |
| `VAD_ENERGY_THRESHOLD` | `0.015` | Mic energy level above which always-listening mode considers you to be talking. Uncalibrated per-machine — run `--mic-check` and tune this if voice mode won't detect you. |

## Project layout

```
core/
  brain/            LLM prompts, intent-classification schema, conversation flow
  action_executor/  Router: maps parsed intents -> tool handlers; dispatch entry point
  permissions/       SAFE / CONFIRM / DANGEROUS permission levels
  security/          Protected-path checks (what self-improvement is not allowed to touch)
  self_improve/      Git-worktree sandbox for Fyz's self-modification proposals
llm/                 Ollama client (chat + embeddings)
voice/               Recording, speech-to-text, text-to-speech, voice-activity detection
tools/
  app_control/       Opening apps/projects
  file_manager/      Search, read, delete files
  project_tools/     Project registry, git status, run tests
  system_tools/      System info, screenshots, process list/kill
memory/              SQLite-backed long-term + semantic memory, action audit log
ui/                  PySide6 desktop GUI (main window, background workers, confirm dialogs)
tests/               pytest test suite
main.py              Text-only CLI entry point
gui_main.py          Desktop GUI entry point
voice_main.py        Voice CLI entry point (always-listening / push-to-talk / mic-check)
```

## How actions are permissioned

Every tool Fyz can call is registered with a permission level in
[`core/action_executor/router.py`](core/action_executor/router.py):

- **SAFE** — runs immediately (open app, read file, get system info, ...).
- **CONFIRM** — runs after a lightweight confirmation.
- **DANGEROUS** — always asks first, with details of what's about to happen (delete
  file, kill process, self-improvement merge). The self-improvement flow specifically
  asks twice: once to run the experiment, once more before merging it into the real
  codebase.

## Adding a project to the registry

Projects Fyz knows about (for "open X", "run tests in X", "git status of X") live in
[`tools/project_tools/registry.py`](tools/project_tools/registry.py). Add an entry
there with the project's name, path, and any aliases you want Fyz to recognize.

## Running the tests

```bash
pytest
```

Tests cover intent normalization, the dangerous-action confirmation gate, semantic
memory, the self-improvement sandbox, and voice utility functions (emoji stripping,
exit-phrase detection). A few tests talk to a live Ollama instance and will be skipped
or fail if it isn't running.

## Troubleshooting

- **Fyz isn't responding at all / times out** — Ollama likely evicted the model from
  memory between messages and is cold-reloading. Raise `OLLAMA_KEEP_ALIVE` in `.env`,
  and make sure `ollama serve` is actually running.
- **Voice mode isn't hearing you** — run `python voice_main.py --mic-check`. If the
  energy numbers never move while you talk, it's a mic/OS-permission/wrong-default-device
  issue (check Windows Sound settings), not a Fyz bug. If they move but stay under the
  threshold line, lower `VAD_ENERGY_THRESHOLD` in `.env`.
- **Replies come out in English instead of Roman Urdu** — this is a known LLM-drift
  edge case the chat prompt actively works against; if you see it happen, note the
  exact question that triggered it.
- **`WHISPER_MODEL_SIZE` hangs forever on first use** — the model weights may not have
  finished downloading. Check the HuggingFace cache for `.incomplete` files, or just
  switch back to `base`, which is verified working.
