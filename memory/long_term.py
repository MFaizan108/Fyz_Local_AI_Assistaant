from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from memory.db import get_connection, init_db


class MemoryCategory(str, Enum):
    PREFERENCE = "preference"
    DECISION = "decision"
    FREQUENT_APP = "frequent_app"
    CONTEXT = "context"


@dataclass
class Memory:
    id: int
    category: str
    content: str
    created_at: str

    @classmethod
    def from_row(cls, row) -> "Memory":
        return cls(
            id=row["id"],
            category=row["category"],
            content=row["content"],
            created_at=row["created_at"],
        )


def save_memory(category: MemoryCategory, content: str) -> None:
    init_db()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO memories (category, content) VALUES (?, ?)",
            (category.value, content),
        )


def list_memories(category: Optional[MemoryCategory] = None) -> List[Memory]:
    init_db()
    with get_connection() as conn:
        if category:
            rows = conn.execute(
                "SELECT * FROM memories WHERE category = ? ORDER BY id DESC",
                (category.value,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM memories ORDER BY id DESC").fetchall()
    return [Memory.from_row(row) for row in rows]


def search_memories(query: str) -> List[Memory]:
    """Simple substring search across saved memory content, most recent first."""
    query_lower = query.lower().strip()
    if not query_lower:
        return list_memories()
    return [m for m in list_memories() if query_lower in m.content.lower()]
