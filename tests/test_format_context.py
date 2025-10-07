import os
import sys

# Ensure the project root is on sys.path so tests can import the `app` package
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.main import _format_context


def test_format_context_fills_up_to_max_items_even_with_duplicates():
    hits = [
        {"title": "Jim Cramer Says International Business Machines Corporation (IBM) ‘Is Doing Quite Well’", "text": "...", "link": "https://example.com/1"},
        {"title": "Jim Cramer Says International Business Machines Corporation (IBM) ‘Is Doing Quite Well’", "text": "...", "link": "https://example.com/1"},  # duplicate
        {"title": "Penn State Taps IBM to Develop AI Virtual Assistant to Foster Success for Student Body", "text": "...", "link": "https://finance.yahoo.com/news/penn-state-taps-ibm-develop-130000681.html"},
        {"title": "Clinical Data Analytics Market to Reach $614.7 Billion by 2034", "text": "...", "link": "https://example.com/3"},
    ]

    ctx = _format_context(hits, max_items=3)
    lines = [l for l in ctx.splitlines() if l.strip()]
    assert len(lines) == 4
    assert "Jim Cramer" in ctx
    assert "Penn State" in ctx
    assert "Clinical Data Analytics" in ctx
