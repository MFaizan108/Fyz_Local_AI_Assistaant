from memory.long_term import MemoryCategory, save_memory, search_memories, semantic_search_memories


def test_semantic_recall_finds_memory_with_no_literal_word_overlap():
    save_memory(
        MemoryCategory.CONTEXT,
        "Ollama took 40 seconds to respond the first time on the healthcare project before the model was warm",
    )
    save_memory(MemoryCategory.PREFERENCE, "User prefers dark mode in VS Code")

    query = "the assistant that was slow to respond"

    assert search_memories(query) == [], "test setup should have zero literal word overlap"

    results = semantic_search_memories(query, top_k=3)
    assert results
    assert "40 seconds" in results[0].content
