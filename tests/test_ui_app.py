from types import SimpleNamespace

import requests


class DummyResp:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text

    def json(self):
        return self._json


def test_ask_news_success(monkeypatch):
    from ui.app import ask_news

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
    answer, citations_md, fact_md = ask_news("What’s new with Apple this quarter?")
    assert "Test answer" in answer
    assert "Sources" in citations_md or "T1" in citations_md
    assert "Fact-check verdict" in fact_md


def test_ask_news_http_error(monkeypatch):
    from ui.app import ask_news

    def fake_post(url, json, timeout):
        return DummyResp(500, None, "internal error")

    monkeypatch.setattr("ui.app.requests.post", fake_post)
    answer, _, fact_md = ask_news("Some question")
    assert answer.startswith("Error: 500")


def test_ask_news_network_exception(monkeypatch):
    from ui.app import ask_news

    def fake_post(url, json, timeout):
        raise requests.RequestException("conn failed")

    monkeypatch.setattr("ui.app.requests.post", fake_post)
    answer, _ = ask_news("Some question")
    assert answer.startswith("Network error calling")
