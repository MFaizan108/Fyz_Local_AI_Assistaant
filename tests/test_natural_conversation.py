from core.brain.context import ConversationContext
from core.brain.conversation import get_chat_reply
from core.brain.output_validator import has_known_bad_phrase, has_unexpected_script

# Live-Ollama integration tests, same convention as test_conversation_routing.py.
# These check objective quality signals (no wrong script, no known-broken
# phrasing, non-empty, relevant) rather than asserting exact wording, since
# natural-language phrasing legitimately varies between runs.


def test_greeting_reply_is_clean():
    reply = get_chat_reply("hello", ConversationContext())
    assert not has_unexpected_script(reply)
    assert not has_known_bad_phrase(reply)
    assert len(reply) > 0


def test_mood_question_reply_is_clean():
    reply = get_chat_reply("main thk hoon aap ka kia hal hai", ConversationContext())
    assert not has_unexpected_script(reply)
    assert not has_known_bad_phrase(reply)


def test_no_mood_for_coding_reply_is_clean_and_relevant():
    reply = get_chat_reply("yr aaj coding karne ka mood nahi hai", ConversationContext())
    assert not has_unexpected_script(reply)
    assert not has_known_bad_phrase(reply)


def test_project_idea_request_gives_a_relevant_reply_not_a_clarification_question():
    reply = get_chat_reply(
        "mujhay koi realistic life problem k solution k liay project batao", ConversationContext()
    )
    assert not has_unexpected_script(reply)
    assert "kya improve karna hai" not in reply.lower()
    assert len(reply) > 20  # a real idea, not a one-word deflection
