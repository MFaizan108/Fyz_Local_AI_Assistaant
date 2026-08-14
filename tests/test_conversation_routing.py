from core.brain.brain import get_intent

# Live-Ollama integration tests, same convention as test_ollama_connection.py -
# checks that casual conversation and real commands land on the correct side
# of the conversation/command split.


def test_greeting_routes_to_chat():
    intent = get_intent("hello")
    assert intent.intent == "chat"


def test_casual_question_routes_to_chat():
    intent = get_intent("kya haal hai?")
    assert intent.intent == "chat"


def test_known_app_command_routes_to_open_app():
    intent = get_intent("Chrome kholo")
    assert intent.intent == "open_app"
    assert intent.target == "chrome"
