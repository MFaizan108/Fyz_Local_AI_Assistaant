import json
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

import numpy as np

from llm.ollama_client import embed
from memory.db import get_connection, init_db

MIN_SIMILARITY = 0.5


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

    embedding_json = None
    try:
        embedding_json = json.dumps(embed(content))
    except Exception:
        # Embedding is a nice-to-have for semantic recall; the memory is
        # still worth saving (and still findable via substring search) even
        # if Ollama/the embedding model is unavailable right now.
        pass

    with get_connection() as conn:
        conn.execute(
            "INSERT INTO memories (category, content, embedding) VALUES (?, ?, ?)",
            (category.value, content, embedding_json),
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
    """Plain substring search across saved memory content, most recent first."""
    query_lower = query.lower().strip()
    if not query_lower:
        return list_memories()
    return [m for m in list_memories() if query_lower in m.content.lower()]


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def semantic_search_memories(query: str, top_k: int = 5) -> List[Memory]:
    """Retrieve memories by meaning rather than shared words, e.g. "the
    assistant that was slow" should be able to match a memory that literally
    says "Ollama took 40 seconds to respond" even with no words in common.
    Falls back to substring search if embeddings aren't available (either
    the embedding model is down, or older rows were saved before this
    feature existed and have no stored embedding)."""
    init_db()

    try:
        query_vec = np.array(embed(query))
    except Exception:
        return search_memories(query)[:top_k]

    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM memories ORDER BY id DESC").fetchall()

    scored = []
    for row in rows:
        embedding_json = row["embedding"]
        if not embedding_json:
            continue

        memory_vec = np.array(json.loads(embedding_json))
        similarity = _cosine_similarity(query_vec, memory_vec)
        if similarity >= MIN_SIMILARITY:
            scored.append((similarity, Memory.from_row(row)))

    if not scored:
        return search_memories(query)[:top_k]

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [memory for _similarity, memory in scored[:top_k]]
