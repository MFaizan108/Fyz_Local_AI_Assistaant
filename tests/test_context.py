from core.brain.context import ConversationContext


def test_recent_messages_excludes_corrupted_assistant_turns():
    context = ConversationContext()
    context.add_user_turn("hello")
    # Simulate a corrupted entry that slipped into history some other way -
    # recent_messages() must still filter it out before it reaches the model.
    context.history.append({"role": "assistant", "content": "筒پा गलत जवाب"})
    context.add_user_turn("kya haal hai")

    messages = context.recent_messages()

    assert not any(m["role"] == "assistant" and "筒" in m["content"] for m in messages)
    assert any(m["content"] == "hello" for m in messages)
    assert any(m["content"] == "kya haal hai" for m in messages)


def test_recent_messages_keeps_clean_assistant_turns():
    context = ConversationContext()
    context.add_user_turn("hello")
    context.add_assistant_turn("Hello bhai! Kya haal hai?")

    messages = context.recent_messages()

    assert any(m["role"] == "assistant" and m["content"] == "Hello bhai! Kya haal hai?" for m in messages)


def test_original_history_is_not_mutated_by_filtering():
    context = ConversationContext()
    context.history.append({"role": "assistant", "content": "筒پा गलत जवाब"})

    context.recent_messages()

    assert len(context.history) == 1  # filtering recent_messages() must not delete from history
