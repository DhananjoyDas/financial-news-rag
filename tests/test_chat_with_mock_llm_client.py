from fastapi.testclient import TestClient

from app.llm import MockLLM
from app.main import app

client = TestClient(app)


def test_chat_endpoint_monkeypatched_llm(monkeypatch):
    """
    Replace get_llm() with a factory that returns MockLLM so the /chat endpoint
    replies deterministically during the test.
    """
    # Patch the get_llm function in app.deps to return MockLLM()
    monkeypatch.setattr("app.deps.get_llm", lambda: MockLLM())

    # Call the endpoint with a realistic question to trigger retrieval + LLM
    r = client.post("/chat", json={"question": "What happened with Apple earnings?"})
    assert r.status_code == 200, r.text

    js = r.json()
    # Basic response shape
    assert "answer" in js and isinstance(js["answer"], str)
    assert "citations" in js and isinstance(js["citations"], list)

    # If citations present, ensure they contain expected keys
    if js["citations"]:
        c = js["citations"][0]
        assert "title" in c and "link" in c
