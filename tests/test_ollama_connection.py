from llm.ollama_client import chat


def test_ollama_responds_to_hello():
    reply = chat("Hello")
    assert isinstance(reply, str)
    assert len(reply) > 0
