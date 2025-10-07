"""Ensure the prompt builder includes SYSTEM, question and context sections."""

from app.prompts import build_answer_prompt


def test_build_prompt_contains_sections():
    q = "What happened with Apple earnings?"
    ctx = "[Apple] Some headline (link: https://example.com)"
    p = build_answer_prompt(q, ctx)
    assert "SYSTEM:" in p
    assert "USER QUESTION:" in p
    assert "CONTEXT (snippets" in p
