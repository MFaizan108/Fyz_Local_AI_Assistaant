from dataclasses import dataclass
from typing import List, Optional

from memory.db import get_connection, init_db


@dataclass
class ActionLogEntry:
    id: int
    intent: str
    target: Optional[str]
    level: str
    result: str
    executed: bool
    created_at: str

    @classmethod
    def from_row(cls, row) -> "ActionLogEntry":
        return cls(
            id=row["id"],
            intent=row["intent"],
            target=row["target"],
            level=row["level"],
            result=row["result"],
            executed=bool(row["executed"]),
            created_at=row["created_at"],
        )


def log_action(intent: str, target: Optional[str], level: str, result: str, executed: bool) -> None:
    init_db()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO actions_history (intent, target, level, result, executed) "
            "VALUES (?, ?, ?, ?, ?)",
            (intent, target, level, result, int(executed)),
        )


def recent_actions(limit: int = 20) -> List[ActionLogEntry]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM actions_history ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [ActionLogEntry.from_row(row) for row in rows]
