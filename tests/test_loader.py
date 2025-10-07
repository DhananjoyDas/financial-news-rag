# tests/test_loader.py
import json
import os
import tempfile

from app.data_loader import load_news


def test_load_cleaned_schema(tmp_path):
    data = {
        "AAPL": [
            {
                "id": "AAPL-1",
                "orig_ticker": "AAPL",
                "repaired_ticker": "AAPL",
                "label_confidence": "HIGH",
                "detected_tickers": ["AAPL"],
                "reason": "original_matches_text",
                "title": "Apple ships record iPhones",
                "full_text": "Apple (AAPL) guided Q4 revenue ...",
                "link": "https://example.com/aapl",
                "order_index": 1,
            }
        ]
    }
    p = tmp_path / "cleaned.json"
    p.write_text(json.dumps(data))
    docs = load_news(str(p))
    assert len(docs) == 1
    d = docs[0]
    assert d["ticker"] == "AAPL"
    assert d["title"].startswith("Apple ships")
    assert "label_confidence" in d and d["label_confidence"] == "HIGH"


def test_load_original_schema(tmp_path):
    data = {
        "AAPL": [
            {
                "title": "Old style Apple story",
                "full_text": "Some text",
                "link": "https://example.com/old",
            }
        ]
    }
    p = tmp_path / "orig.json"
    p.write_text(json.dumps(data))
    docs = load_news(str(p))
    assert docs[0]["ticker"] == "AAPL"
    assert docs[0]["text"] == "Some text"
