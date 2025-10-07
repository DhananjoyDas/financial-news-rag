# app/main.py
"""Main FastAPI app for the Finance News RAG Chat service."""

from typing import Dict, List, Set
from fastapi import FastAPI
import json
import logging

logger = logging.getLogger(__name__)

from .alias_map import detect_tickers_from_query
from .deps import get_docs, get_index, get_llm

# Project imports
from .models import ChatRequest, ChatResponse, Citation, Healthz
from .prompts import ANSWER_SYSTEM_PROMPT, build_answer_prompt
from .retriever import retrieve

app = FastAPI(title="Finance News RAG Chat")


@app.get("/healthz", response_model=Healthz)
def healthz():
    """Health check endpoint."""
    docs = get_docs()
    return Healthz(ok=True, docs=len(docs))


def _format_context(hits: List[Dict], max_items: int = 3) -> str:
    """
    Turn top documents into the bracketed context the LLM expects:
    [Title] short excerpt (link: URL)
    """
    lines = []
    seen = set()
    count = 0
    for d in hits:
        key = (d.get("title"), d.get("link"))
        if key in seen:
            continue
        seen.add(key)
        count += 1
        title = d.get("title") or "Untitled"
        body = (d.get("text") or d.get("title") or "")[:220].replace("\n", " ")
        link = d.get("link") or "#"
        # Numbered, machine-friendly entries
        lines.append(f"{count}) [{title}] {body} (LINK: {link})")
        if count >= max_items:
            break

    if not lines:
        return ""

    # Prepend an explicit CONTEXT header to make parsing unambiguous
    return "CONTEXT:\n" + "\n".join(lines)


def _build_citations(
    hits: List[Dict],
    targets: Set[str],
    max_items: int = 3,
    max_non_target: int = 1,
) -> List[Dict]:
    """
    Build the citations list with this policy:
      1) Prefer docs whose repaired_ticker or detected_tickers.
      2) Allow up to max_non_target backfill citations if we don't have enough target hits.
      3) De-duplicate by (title, link).
    """
    citations: List[Dict] = []
    seen = set()
    non_target_used = 0

    def is_target_doc(d: Dict) -> bool:
        if not targets:
            return False
        rt = (d.get("repaired_ticker") or d.get("ticker") or "").upper()
        if rt in targets:
            return True
        det = set((d.get("detected_tickers") or []))
        return bool(det & targets)

    # First pass: take target-matching docs
    for d in hits:
        if len(citations) >= max_items:
            break
        if is_target_doc(d):
            key = (d["title"], d["link"])
            if key in seen:
                continue
            citations.append(
                {
                    "title": d["title"],
                    "link": d["link"],
                    "ticker": d.get("repaired_ticker") or d.get("ticker"),
                }
            )
            seen.add(key)

    # Second pass: allow limited non-target backfill to reach max_items
    if len(citations) < max_items:
        for d in hits:
            if len(citations) >= max_items:
                break
            key = (d["title"], d["link"])
            if key in seen:
                continue
            if not targets or non_target_used < max_non_target:
                citations.append(
                    {
                        "title": d["title"],
                        "link": d["link"],
                        "ticker": d.get("repaired_ticker") or d.get("ticker"),
                    }
                )
                seen.add(key)
                if targets:
                    non_target_used += 1

    return citations


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """Chat endpoint: answer a question about the news dataset."""
    q = (req.question or "").strip()
    if not q:
        return ChatResponse(
            answer="Please enter a question about the provided news dataset.",
            citations=[],
        )

    # Detect target tickers from the query (e.g., {"AAPL"})
    targets = detect_tickers_from_query(q)

    # Retrieve candidate documents (broad pool + soft scoring in retriever)
    idx = get_index()
    hits = retrieve(idx, q, k=8)

    # Debug: dump simplified hits (id, title, link) so we can inspect what was
    # retrieved at runtime. Do not write sensitive data.
    try:
        simple = [
            {"id": h.get("id"), "title": h.get("title"), "link": h.get("link")}
            for h in hits
        ]
        open("/tmp/last_hits.json", "w", encoding="utf-8").write(json.dumps(simple, ensure_ascii=False, indent=2))
    except Exception:
        logger.exception("failed writing /tmp/last_hits.json")

    if not hits:
        return ChatResponse(
            answer="I don’t know based on the provided news (cleaned) dataset.",
            citations=[],
        )

    # Build LLM context
    context = _format_context(hits, max_items=3)

    # Debug: persist the exact context string sent to the LLM for troubleshooting
    try:
        open("/tmp/last_context.txt", "w", encoding="utf-8").write(context or "")
    except Exception:
        logger.exception("failed writing /tmp/last_context.txt")

    # (Optional but recommended) Emphasize the target in the system prompt
    system_prompt = ANSWER_SYSTEM_PROMPT
    if targets:
        tickers_str = ", ".join(sorted(targets))
        system_prompt = (
            ANSWER_SYSTEM_PROMPT
            + f"\n\nFocus on: {tickers_str}. Only cite items clearly related to these tickers."
        )

    # Ask the LLM for an answer
    llm = get_llm()
    answer = llm.complete(build_answer_prompt(q, context), system=system_prompt)

    # Build citations with the “prefer target, allow one related” policy
    cite_dicts = _build_citations(hits, targets, max_items=3, max_non_target=1)

    # Return typed response
    return ChatResponse(answer=answer, citations=[Citation(**c) for c in cite_dicts])
