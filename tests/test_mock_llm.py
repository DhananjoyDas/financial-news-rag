"""Unit test for the deterministic MockLLM behavior."""

from app.llm import MockLLM
from app.prompts import build_answer_prompt


def test_mock_llm_returns_string():
    q = "What happened with Apple earnings?"
    ctx = "[Apple] Apple posted higher revenue this quarter (link: https://example.com)"
    prompt = build_answer_prompt(q, ctx)
    out = MockLLM().complete(prompt, system=None)
    assert isinstance(out, str)
    assert "Sources:" in out or "Dataset" in out
