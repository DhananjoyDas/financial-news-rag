"""Smoke test for the data loader using the configured NEWS_JSON_PATH or default file."""

import os

from app.data_loader import load_news


def test_load_news_smoke():
    path = os.getenv("NEWS_JSON_PATH", "stock_news.cleaned.json")
    docs = load_news(path)
    assert isinstance(docs, list)
    # if dataset is non-empty, validate the first doc shape
    if docs:
        d = docs[0]
        assert "id" in d and "title" in d and "text" in d
