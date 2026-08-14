from core.action_executor.dispatch import handle_utterance
from core.brain.context import ConversationContext

# Live-Ollama integration test, same convention as test_conversation_routing.py.
# Exercises the exact "healthcare project kholo" -> "iske tests chalao"
# follow-up scenario from the acceptance criteria.


def test_pronoun_resolves_to_previously_opened_project():
    context = ConversationContext()
    handle_utterance("healthcare project kholo", context, confirm_prompt=lambda p: "y")

    assert context.last_project is not None

    reply = handle_utterance("iske tests chalao", context, confirm_prompt=lambda p: "y")

    assert "which project" not in reply.lower()
    assert "konsa project" not in reply.lower()
    assert "konsi project" not in reply.lower()
