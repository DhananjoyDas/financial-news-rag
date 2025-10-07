"""
Retriever helpers: small deterministic ranking used for tests.

This module contains simple, easily-auditable scoring logic used by the
test-suite and as a baseline for later replacement with BM25/FAISS.
"""

import re
from typing import Dict, List, Tuple

from .alias_map import ALIASES, detect_tickers_from_query


def _alias_hit(title: str, text: str, target: str) -> Tuple[bool, bool]:
    """Returns (in_title, in_text) alias hits for a target ticker."""
    names = ALIASES.get(target, set())
    ttl = title.lower()
    txt = text.lower()
    in_title = any(n in ttl for n in names)
    in_text = any(n in txt for n in names)
    return in_title, in_text


def _bm25_topk(index, docs: List[Dict], query: str, k: int) -> Dict[int, float]:
    # TODO: replace with real BM25/TF-IDF. For now, simple keyword count.
    q_terms = {w for w in re.findall(r"[A-Za-z0-9']+", query.lower()) if len(w) > 2}
    scores = {}
    for i, d in enumerate(docs):
        blob = (d["title"] + " " + d["text"]).lower()
        score = sum(1 for t in q_terms if t in blob)
        if score > 0:
            scores[i] = float(score)
    return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True)[:k])


def _embed_topk(emb, docs: List[Dict], query: str, k: int) -> Dict[int, float]:
    # TODO: replace with real embeddings/FAISS. For now, stub matches title tokens.
    q_terms = set(re.findall(r"[A-Za-z0-9']+", query.lower()))
    scores = {}
    for i, d in enumerate(docs):
        ttl_terms = set(re.findall(r"[A-Za-z0-9']+", d["title"].lower()))
        inter = len(q_terms & ttl_terms)
        if inter:
            scores[i] = float(inter)
    return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True)[:k])


def build_index(docs: List[Dict]):
    """Builds and returns a simple in-memory index structure."""
    # Replace with real index builders (FAISS/BM25) and stash them here.
    return {"docs": docs, "bm25": None, "emb": None}


def retrieve(index, query: str, k: int = 8) -> List[Dict]:
    """Retrieve top-k relevant docs for a query from the index."""
    docs = index["docs"]
    targets = detect_tickers_from_query(query)  # e.g., {"AAPL"}
    # 1) Broad candidate pool
    cands = []
    if targets:
        for d in docs:
            if d.get("repaired_ticker") in targets or any(
                t in targets for t in (d.get("detected_tickers") or [])
            ):
                cands.append(d)
            else:
                # textual alias backstop
                if any(_alias_hit(d["title"], d["text"], t)[1] for t in targets):
                    cands.append(d)
    if not cands:
        # fallback to all docs (global search)
        cands = docs

    # 2) Base scores (hybrid)
    bm = _bm25_topk(index["bm25"], cands, query, k=50)
    em = _embed_topk(index["emb"], cands, query, k=50)

    # Normalize to [0,1]
    def norm_map(m):
        if not m:
            return {}
        mx = max(m.values())
        return {i: (s / mx) for i, s in m.items()} if mx > 0 else {}

    bm, em = norm_map(bm), norm_map(em)
    base = {}
    for i in set(list(bm.keys()) + list(em.keys())):
        base[i] = 0.55 * bm.get(i, 0.0) + 0.35 * em.get(i, 0.0)

    # 3) Soft boosts/penalties
    scored = []
    for i, d in enumerate(cands):
        s = base.get(i, 0.0)
        conf = (d.get("label_confidence") or "LOW").upper()
        conf_w = 1.0 if conf == "HIGH" else (0.9 if conf == "MEDIUM" else 0.8)
        s *= conf_w

        if targets:
            if d.get("repaired_ticker") in targets:
                s *= 1.25
            if any(t in targets for t in (d.get("detected_tickers") or [])):
                s *= 1.10
            in_title, in_text = _alias_hit(d["title"], d["text"], list(targets)[0])
            if in_title:
                s *= 1.10
            elif in_text:
                s *= 1.05

        # Penalize MISC unless query is clearly general-market
        rt = (d.get("repaired_ticker") or "").upper()
        if rt == "MISC" and targets:
            s *= 0.85
        if (
            rt == "MULTI"
            and targets
            and not any(t in targets for t in (d.get("detected_tickers") or []))
        ):
            s *= 0.9

        # optional: mild recency by order_index (newer = higher)
        if "order_index" in d and len(docs) > 1:
            r = 1.0 - (d["order_index"] / max(len(docs) - 1, 1))
            s *= 1.0 + 0.05 * r

        if s > 0:
            scored.append((s, d))

    scored.sort(key=lambda x: x[0], reverse=True)

    # 4) Ensure variety across doc ids/titles (dedupe)
    seen_ids, out = set(), []
    for s, d in scored:
        if d["id"] in seen_ids:
            continue
        out.append(d)
        seen_ids.add(d["id"])
        if len(out) >= k:
            break
    return out
