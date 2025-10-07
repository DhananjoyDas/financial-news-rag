import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.main import _format_context
from app.prompts import build_answer_prompt


def test_build_answer_prompt_includes_numbered_context():
    hits = [
        {"title": "T1", "text": "first text", "link": "http://u1"},
        {"title": "T2", "text": "second text", "link": "http://u2"},
        {"title": "T3", "text": "third text", "link": "http://u3"},
    ]
    ctx = _format_context(hits, max_items=3)
    prompt = build_answer_prompt("Any recent IBM partnerships mentioned?", ctx)
    assert "CONTEXT:" in prompt
    assert "1) [T1]" in prompt
    assert "2) [T2]" in prompt
    assert "3) [T3]" in prompt
