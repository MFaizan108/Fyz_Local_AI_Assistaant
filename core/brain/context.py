from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ConversationContext:
    """Short-term memory for the current session: recent chat turns plus a
    couple of quick-reference slots for pronoun resolution ("iska", "isko")."""

    history: List[dict] = field(default_factory=list)
    last_project: Optional[str] = None
    max_turns: int = 10

    def add_user_turn(self, text: str) -> None:
        self._append("user", text)

    def add_assistant_turn(self, text: str) -> None:
        self._append("assistant", text)

    def _append(self, role: str, content: str) -> None:
        self.history.append({"role": role, "content": content})
        self.history = self.history[-(self.max_turns * 2):]

    def recent_messages(self) -> List[dict]:
        return list(self.history)
