from dataclasses import dataclass, field
from typing import List, Optional

from core.brain.output_validator import has_unexpected_script


@dataclass
class ConversationContext:
    """Short-term memory for the current session: recent chat turns plus a
    small set of structured "active state" slots - which project was last
    opened/discussed, which browser profile was last opened - used for
    pronoun/follow-up resolution ("iska", "isko", "iske tests chalao")
    without relying on the LLM to re-derive it from raw history every turn."""

    history: List[dict] = field(default_factory=list)
    last_project: Optional[str] = None
    active_browser_profile: Optional[str] = None
    max_turns: int = 10

    def add_user_turn(self, text: str) -> None:
        self._append("user", text)

    def add_assistant_turn(self, text: str) -> None:
        self._append("assistant", text)

    def _append(self, role: str, content: str) -> None:
        self.history.append({"role": role, "content": content})
        self.history = self.history[-(self.max_turns * 2):]

    def recent_messages(self) -> List[dict]:
        """Recent turns, with any assistant turn that somehow ended up
        containing an unexpected script (e.g. a corrupted reply that slipped
        past validation) excluded - corrupted output must never get fed back
        into the model as context, since that risks reinforcing the same
        drift on the next turn. Nothing is deleted from `self.history`
        itself, only filtered out of what gets sent to the model."""
        return [
            m for m in self.history
            if not (m["role"] == "assistant" and has_unexpected_script(m["content"]))
        ]
