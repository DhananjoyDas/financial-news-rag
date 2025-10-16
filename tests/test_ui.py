from types import SimpleNamespace

import requests

from ui.app import ask_news


class DummyResp:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text

    def json(self):
        return self._json


def test_ask_news_success(monkeypatch):
    def fake_post(url, json, timeout):
        assert url.endswith("/chat")
        return DummyResp(
            200,
            {
                "answer": "Test answer",
                "citations": [{"title": "T1", "link": "https://u", "ticker": "AAPL"}],
            },
        )

    monkeypatch.setattr("ui.app.requests.post", fake_post)
    answer, citations_md, fact_md  = ask_news("What’s new with Apple this quarter?")
    assert "Test answer" in answer
    assert "[T1](https://u)" in citations_md
    assert "— AAPL" in citations_md
    # assert "Fact-check:" in fact_md


def test_ask_news_http_error(monkeypatch):
    def fake_post(url, json, timeout):
        return DummyResp(500, None, "internal error")

    monkeypatch.setattr("ui.app.requests.post", fake_post)
    answer, _, fact_md= ask_news("Some question")
    assert answer.startswith("Error: 500")


def test_ask_news_network_exception(monkeypatch):
    def fake_post(url, json, timeout):
        raise requests.RequestException("conn failed")

    monkeypatch.setattr("ui.app.requests.post", fake_post)
    answer, _ = ask_news("Some question")
    assert answer.startswith("Network error calling")
