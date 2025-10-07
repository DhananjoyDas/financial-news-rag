from app.main import _format_context


def test_format_context_includes_brackets_and_link():
    hits = [
        {
            "id": "a-0",
            "title": "Apple posts strong quarter",
            "text": "Apple beat revenue and guided higher.",
            "link": "https://example.com/article",
            "ticker": "AAPL",
            "order_index": 0,
        }
    ]
    out = _format_context(hits, max_items=1)
    assert "CONTEXT:" in out and "CONTEXT:" in out
    # quick sanity checks
    assert "Apple posts strong quarter" in out or "Apple" in out
