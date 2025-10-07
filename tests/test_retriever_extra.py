from app.main import _format_context as format_context
from app.retriever import build_index, retrieve


def test_retrieve_basic():
    docs = [
        {
            "id": "a-0",
            "title": "Apple earnings beat",
            "text": "Apple beat earnings and guided higher.",
            "link": "u",
            "order_index": 1,
            "ticker": "AAPL",
        },
        {
            "id": "b-0",
            "title": "Market update",
            "text": "Stocks mixed.",
            "link": "u2",
            "order_index": 0,
            "ticker": "SPY",
        },
    ]
    idx = build_index(docs)
    hits = retrieve(idx, "Apple earnings", k=2)
    assert len(hits) >= 1
    assert any("Apple" in h["title"] or "Apple" in h["text"] for h in hits)


def test_format_context_contains_title_and_link():
    hits = [
        {
            "id": "a-0",
            "title": "Apple earnings beat",
            "text": "Apple beat earnings and guided higher.",
            "link": "https://example.com/a",
            "order_index": 1,
            "ticker": "AAPL",
        }
    ]
    out = format_context(hits)
    assert "[" in out and "]" in out
    assert "CONTEXT:" in out and "https://example.com/a" in out
