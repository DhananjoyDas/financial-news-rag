from app.prompts import ANSWER_SYSTEM_PROMPT, build_answer_prompt


def test_build_answer_prompt_contains_context_and_question():
    ctx = "[Apple] Apple posted higher revenue this quarter (link: https://example.com)"
    q = "What happened with Apple earnings?"
    prompt = build_answer_prompt(q, ctx)
    assert "CONTEXT" in prompt
    assert q in prompt


def test_answer_system_prompt_non_empty():
    assert isinstance(ANSWER_SYSTEM_PROMPT, str)
    assert ANSWER_SYSTEM_PROMPT.strip() != ""
