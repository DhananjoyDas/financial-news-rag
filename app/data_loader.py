"""Data loading utilities.

Normalize JSON news files into a flat list of document dicts consumed by the
retriever and API layers.
"""

import json
from pathlib import Path
from typing import List, Dict, Any

def _is_cleaned_item(it: Dict[str, Any]) -> bool:
    # cleaned/filtered items carry these fields
    return "repaired_ticker" in it or "label_confidence" in it or "orig_ticker" in it

def load_news(json_path: str) -> List[Dict[str, Any]]:
    """Load news and return a flat list of docs with normalized fields.
    Output fields:
      - id: stable string id
      - ticker: canonical per-item ticker (repaired if present, else bucket key, else original)
      - title, text (from full_text), link
      - order_index: int
      - orig_ticker, repaired_ticker, label_confidence, reason, detected_tickers (optional)
    """
    raw = json.loads(Path(json_path).read_text())
    docs: List[Dict[str, Any]] = []
    seq = 0

    for bucket_key, items in raw.items():
        for it in items:
            # Common fields
            title = (it.get("title") or "").strip()
            text  = (it.get("full_text") or "").strip()
            link  = (it.get("link") or "").strip()

            if _is_cleaned_item(it):
                # Cleaned/filtered schema
                repaired = it.get("repaired_ticker") or bucket_key
                orig     = it.get("orig_ticker") or bucket_key
                oi       = it.get("order_index")
                doc_id   = it.get("id") or f"{repaired}-{oi if oi is not None else seq}"

                docs.append({
                    "id": doc_id,
                    "ticker": repaired, # canonical ticker to use downstream
                    "title": title,
                    "text": text,
                    "link": link,
                    "order_index": int(oi) if oi is not None else seq,

                    # Pass-through metadata (useful for filtering/ranking/debug)
                    "orig_ticker": orig,
                    "repaired_ticker": repaired,
                    "label_confidence": it.get("label_confidence"),
                    "reason": it.get("reason"),
                    "detected_tickers": it.get("detected_tickers", []),
                })
            else:
                # Original schema fallback
                doc_id = f"{bucket_key}-{seq}"
                docs.append({
                    "id": doc_id,
                    "ticker": bucket_key,
                    "title": title,
                    "text": text,
                    "link": link,
                    "order_index": seq,
                })

            seq += 1

    return docs
