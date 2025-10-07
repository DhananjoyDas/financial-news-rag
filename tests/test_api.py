from fastapi.testclient import TestClient

from app.deps import get_llm
from app.llm import MockLLM
from app.main import app

client = TestClient(app)


def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    js = r.json()
    assert js["ok"] is True
    assert js["docs"] >= 0


def test_chat_empty():
    r = client.post("/chat", json={"question": ""})
    assert r.status_code == 200
    assert "Please enter a question" in r.json()["answer"]


def test_chat_with_mock_llm(monkeypatch):
    # Force MockLLM to guarantee offline determinism
    monkeypatch.setenv("LLM_PROVIDER", "mock")

    # Ask about a common finance term to hit some documents
    r = client.post("/chat", json={"question": "What happened with Apple earnings?"})
    assert r.status_code == 200
    js = r.json()
    assert "Sources:" in js["answer"] or "dataset" in js["answer"]
    assert "citations" in js and isinstance(js["citations"], list)
