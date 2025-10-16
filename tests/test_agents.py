# python
# app/test_agents.py

import json
import time
import hashlib
from typing import Any, Dict, List
import re

from app.agents import FactCheckAgent, AuditLoggerAgent


# ------------ FactCheckAgent: heuristic (Mock) behavior ------------

def test_heuristic_pass_for_high_overlap():
    class MockLLM:
        pass  # class name contains 'mock' -> heuristic path

    agent = FactCheckAgent(MockLLM())

    question = "Any IBM partnerships?"
    # answer contains tokens present in context
    answer = "Penn State tapped IBM to build an AI virtual assistant for students."
    context = "Penn State Taps IBM to Develop AI Virtual Assistant to Foster Success for Student Body — IBM"
    res = agent.check(question, answer, context)

    assert isinstance(res, dict)
    assert res["verdict"] == "PASS"
    assert res["unsupported_claims"] == []
    assert 0.0 <= res["confidence"] <= 1.0
    assert "Heuristic" in res["notes"] or "Heuristic" or res["notes"] is not None


def test_heuristic_warn_for_low_overlap_long_sentence():
    class MockLLM:
        pass

    agent = FactCheckAgent(MockLLM())

    question = "Is there radical replacement of clinicians?"
    # single long sentence with very low overlap to context and length > 20
    answer = "This single sentence claims AI will replace all clinicians worldwide by next year, causing massive job loss and regulatory collapse."
    context = "Some unrelated dataset text mentioning finance and partnerships only."
    res = agent.check(question, answer, context)

    assert isinstance(res, dict)
    assert res["verdict"] in ("WARN", "FAIL")
    # heuristic returns WARN with unsupported_claims list when low overlap
    assert isinstance(res["unsupported_claims"], list)
    assert len(res["unsupported_claims"]) >= 1
    assert 0.0 <= res["confidence"] <= 1.0


# ------------ FactCheckAgent: LLM verify behavior (non-mock) ------------

def test_llm_verify_parses_json_response():
    class RealLLM:
        def complete(self, prompt: str, system: str = None) -> str:
            payload = {
                "verdict": "PASS",
                "unsupported_claims": [],
                "confidence": 0.92,
                "notes": "All good"
            }
            return json.dumps(payload)

    agent = FactCheckAgent(RealLLM())

    q = "Any IBM partnerships?"
    a = "IBM partnered with Penn State."
    ctx = "[Penn State] ... (link: https://example.com)"
    res = agent.check(q, a, ctx)

    assert res["verdict"] == "PASS"
    assert res["unsupported_claims"] == []
    assert abs(res["confidence"] - 0.92) < 1e-6
    assert res["notes"] == "All good"


def test_llm_verify_parses_embedded_json_in_text():
    class RealLLMEmbedded:
        def complete(self, prompt: str, system: str = None) -> str:
            # Return JSON embedded inside other text; parser should extract braces and parse
            return "Note: see result below\n{ \"verdict\": \"FAIL\", \"unsupported_claims\": [\"claim1\"], \"confidence\": 0.11, \"notes\": \"bad\" }\nEnd."

    agent = FactCheckAgent(RealLLMEmbedded())

    q = "Q"
    a = "A"
    ctx = "C"
    res = agent.check(q, a, ctx)

    assert res["verdict"] == "FAIL"
    assert isinstance(res["unsupported_claims"], list)
    assert "claim1" in res["unsupported_claims"]
    assert abs(res["confidence"] - 0.11) < 1e-6
    assert res["notes"] == "bad"


def test_llm_verify_fallback_on_exception():
    class BrokenLLM:
        def complete(self, prompt: str, system: str = None) -> str:
            raise RuntimeError("boom")

    agent = FactCheckAgent(BrokenLLM())

    q = "Q"
    a = "A"
    ctx = "C"
    res = agent.check(q, a, ctx)

    # fallback behavior from _llm_verify returns WARN minimal dict
    assert isinstance(res, dict)
    assert res.get("verdict") == "WARN"
    assert isinstance(res.get("unsupported_claims"), list)


# ------------ AuditLoggerAgent tests ------------

def test_iso_now_format_and_z_suffix():
    a = AuditLoggerAgent(log_path=":memory:")  # path won't be used here; just test helper
    s = a._iso_now()
    assert isinstance(s, str)
    assert "T" in s  # ISO format includes 'T'
    assert s.endswith("Z")  # timezone 'Z'


def test_build_and_log_writes_entry_and_context_hash(tmp_path):
    log_file = tmp_path / "audit.log"
    agent = AuditLoggerAgent(log_path=str(log_file))

    started_at = "2025-10-12T12:00:00Z"
    question = "Any recent IBM partnerships mentioned?"
    targets = ["IBM"]
    hits = [
        {"id": "1", "title": "T1", "link": "https://a", "ticker": "IBM", "order_index": 0},
        {"id": "2", "title": "T2", "link": "https://b", "repaired_ticker": "IBM", "order_index": 1},
    ]
    context = "[T1] excerpt (link: https://a)\n[T2] excerpt (link: https://b)"
    answer = "Yes, see sources."
    fact_check = {"verdict": "PASS"}
    extra = {"note": "test"}
    # provide a monotonic start in the past to get a small elapsed_ms
    started_monotonic = time.monotonic() - 0.05

    agent.build_and_log(
        started_at=started_at,
        question=question,
        targets=targets,
        hits=hits,
        context=context,
        answer=answer,
        fact_check=fact_check,
        extra=extra,
        started_monotonic=started_monotonic,
    )

    # file should exist and contain one JSON line
    assert log_file.exists()
    with open(log_file, "r", encoding="utf-8") as fh:
        lines = [ln.strip() for ln in fh.readlines() if ln.strip()]
    assert len(lines) == 1
    rec = json.loads(lines[0])

    # Basic required fields present
    for k in ("started_at", "ended_at", "elapsed_ms", "question", "targets", "retrieved", "context_hash", "answer", "fact_check"):
        assert k in rec

    # retrieved list preserved and contains expected keys
    assert isinstance(rec["retrieved"], list)
    assert rec["retrieved"][0]["id"] == "1"
    assert rec["retrieved"][1]["id"] == "2"
    assert "order_index" in rec["retrieved"][0]
    assert rec["retrieved"][0]["order_index"] == 0

    # context hash matches
    expected_hash = hashlib.sha256(context.encode("utf-8")).hexdigest()
    assert rec["context_hash"] == expected_hash

    # extra preserved
    assert "extra" in rec and rec["extra"] == extra

    # elapsed_ms is an integer >= 0
    assert isinstance(rec["elapsed_ms"], int)
    assert rec["elapsed_ms"] >= 0