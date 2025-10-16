# app/agents.py
import json
import os
import time
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

class FactCheckAgent:
    """
    Verifies that the generated answer is supported by the provided RAG context.
    Strategy:
      - If an LLM client is available and not 'mock', use a verification prompt.
      - Otherwise (mock/offline), fall back to a lexical-overlap heuristic.
    Returns a dict:
      {
        "verdict": "PASS" | "WARN" | "FAIL",
        "unsupported_claims": [ ... ],
        "confidence": float in [0,1],
        "notes": str
      }
    """
    def __init__(self, llm_client):
        self.llm = llm_client

    def _llm_verify(self, question: str, answer: str, context: str) -> Dict[str, Any]:
        prompt = f"""
You are a rigorous fact-checker.

Task: Given the user question, an assistant's answer, and the exact context snippets used (from a news dataset), identify any specific claims in the answer that are NOT explicitly supported by the provided context.

Return a compact JSON with fields:
- verdict: "PASS" (all supported), "WARN" (minor unsupported phrasing), or "FAIL" (one or more factual claims unsupported)
- unsupported_claims: array of short strings, each an unsupported claim as it appears or paraphrased
- confidence: number [0,1]
- notes: single short line rationale

QUESTION:
{question}

ANSWER:
{answer}

CONTEXT:
{context}
"""
        try:
            raw = self.llm.complete(prompt, system="Be strict, concise, and only judge based on the context. Output JSON only.")
            # Try to parse JSON; if the model returned plain text, wrap minimally
            parsed = None
            try:
                parsed = json.loads(raw)
            except Exception:
                # Best-effort extraction: look for JSON braces
                start = raw.find("{")
                end = raw.rfind("}")
                if start != -1 and end != -1 and end > start:
                    parsed = json.loads(raw[start:end+1])
            if isinstance(parsed, dict):
                # normalization
                verdict = parsed.get("verdict", "WARN")
                uc = parsed.get("unsupported_claims") or []
                if not isinstance(uc, list): uc = [str(uc)]
                conf = float(parsed.get("confidence", 0.6))
                notes = parsed.get("notes", "")
                return {"verdict": verdict, "unsupported_claims": uc, "confidence": conf, "notes": notes}
        except Exception:
            pass
        # fallthrough
        return {"verdict": "WARN", "unsupported_claims": [], "confidence": 0.5, "notes": "LLM verify fallback."}

    def _heuristic_verify(self, answer: str, context: str) -> Dict[str, Any]:
        # Very light check: sentences with very low token overlap are flagged.
        import re
        sent_split = re.split(r'(?<=[.!?])\s+', (answer or "").strip())
        ctx = (context or "").lower()
        bad: List[str] = []
        for s in sent_split:
            tokens = [t.lower() for t in re.findall(r"[A-Za-z0-9']+", s)]
            if not tokens:
                continue
            overlap = sum(1 for t in tokens if t in ctx)
            ratio = overlap / max(len(tokens), 1)
            if ratio < 0.08 and len(s) > 20:
                bad.append(s.strip())
        if not bad:
            return {"verdict": "PASS", "unsupported_claims": [], "confidence": 0.7, "notes": "Heuristic overlap OK."}
        # minor issues → WARN (not FAIL) because heuristic is conservative
        return {"verdict": "WARN", "unsupported_claims": bad[:5], "confidence": 0.55, "notes": "Heuristic overlap low on some sentences."}

    def check(self, question: str, answer: str, context: str) -> Dict[str, Any]:
        # If llm client string contains "MockLLM" or lacks real API, use heuristic
        cls = self.llm.__class__.__name__.lower()
        if "mock" in cls:
            return self._heuristic_verify(answer, context)
        return self._llm_verify(question, answer, context)


class AuditLoggerAgent:
    """
    JSONL logger: records each interaction with timestamps, RAG details, fact-check results.
    Fields written:
      - started_at, ended_at, elapsed_ms
      - question
      - targets (detected tickers)
      - retrieved: [{id,title,link,ticker,score?}]  (score optional if available)
      - context_hash (sha256 of string sent to LLM)
      - answer
      - fact_check: {...}
    """
    def __init__(self, log_path: Optional[str] = None):
        # Allow disabling file logging by passing an empty string or a special in-memory token
        env_path = os.getenv("NEWS_AUDIT_LOG", "")
        default_path = "logs/interactions.log"
        chosen = log_path if log_path is not None else (env_path or default_path)
        # Treat empty string or ':memory:' as a signal to disable on-disk logging
        if chosen in ("", ":memory:"):
            self.log_path = ""  # empty -> no file writes
        else:
            self.log_path = chosen
            # create parent dir only when dirname is non-empty
            parent = os.path.dirname(self.log_path)
            if parent:
                os.makedirs(parent, exist_ok=True)

    @staticmethod
    def _iso_now() -> str:
        # timezone-aware UTC; ISO-8601 with milliseconds + 'Z'
        return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

    def log(self, payload: Dict[str, Any]) -> None:
        try:
            # If log_path is empty, this instance is configured as in-memory / disabled logging
            if not self.log_path:
                return
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception:
            # soft-fail logging
            pass

    def build_and_log(
        self,
        started_at: str,
        question: str,
        targets: List[str],
        hits: List[Dict[str, Any]],
        context: str,
        answer: str,
        fact_check: Dict[str, Any],
        extra: Optional[Dict[str, Any]] = None,
        started_monotonic: Optional[float] = None
    ) -> None:
        ended_at = self._iso_now()
        elapsed_ms = None
        if started_monotonic is not None:
            elapsed_ms = int((time.monotonic() - started_monotonic) * 1000)

        # Hash the exact context we sent to the LLM
        ctx_hash = hashlib.sha256(context.encode("utf-8")).hexdigest()

        rec = {
            "started_at": started_at,
            "ended_at": ended_at,
            "elapsed_ms": elapsed_ms,
            "question": question,
            "targets": targets,
            "retrieved": [
                {
                    "id": d.get("id"),
                    "title": d.get("title"),
                    "link": d.get("link"),
                    "ticker": d.get("repaired_ticker") or d.get("ticker"),
                    "order_index": d.get("order_index"),
                } for d in hits
            ],
            "context_hash": ctx_hash,
            "answer": answer,
            "fact_check": fact_check,
        }
        if extra:
            rec["extra"] = extra
        self.log(rec)
