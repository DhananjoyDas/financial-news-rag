#!/usr/bin/env python3
"""Utilities to clean and normalize a raw stock-news JSON dataset.

This script detects company mentions, repairs tickers, assigns a simple
confidence label, and outputs cleaned/filtered JSON plus a CSV report.
"""

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

# -------- Alias map (extend as needed) --------
ALIAS_TO_TICKER = {
    # Big Tech
    "apple": "AAPL",
    "apple inc": "AAPL",
    "microsoft": "MSFT",
    "msft": "MSFT",
    "amazon": "AMZN",
    "amazon.com": "AMZN",
    "alphabet": "GOOGL",
    "google": "GOOGL",
    "meta": "META",
    "meta platforms": "META",
    "facebook": "META",
    "tesla": "TSLA",
    "ibm": "IBM",
    "international business machines": "IBM",
    "cisco": "CSCO",
    "netflix": "NFLX",
    "nvidia": "NVDA",
    # Finance
    "jpmorgan": "JPM",
    "jp morgan": "JPM",
    "bank of america": "BAC",
    "wells fargo": "WFC",
    # Retail
    "walmart": "WMT",
    "target": "TGT",
    # Pharma
    "pfizer": "PFE",
    # Industrials
    "boeing": "BA",
}

# Regex to catch inline tickers like (AAPL), AAPL:, or [AAPL]
TICKER_CANDIDATE_RE = re.compile(r"[\(\[\s,:\-](?P<tic>[A-Z]{2,5})[\)\]\s,:\-]")
IGNORE_TOKENS = {
    "USD",
    "CEO",
    "AI",
    "ETF",
    "ETFs",
    "IPO",
    "GDP",
    "FOMC",
    "PMI",
    "EPS",
    "PE",
    "EV",
    "ADP",
    "CPI",
}

PERSONAL_FINANCE_HINTS = [
    "personal finance",
    "credit card",
    "credit cards",
    "mortgage",
    "savings",
    "retirement",
    "social security",
    "budget",
    "bank account",
    "checking account",
    "how to save",
    "tips to save",
    "financial advice",
    "loan rates",
    "refinance",
]

NEWS_TERMS = [
    "earnings",
    "revenue",
    "guidance",
    "outlook",
    "forecast",
    "quarter",
    "q1",
    "q2",
    "q3",
    "q4",
    "price target",
    "upgrade",
    "downgrade",
    "sales",
    "shipments",
    "regulatory",
    "antitrust",
    "lawsuit",
    "investigation",
    "acquisition",
    "partnership",
    "launch",
    "unveil",
    "dividend",
    "buyback",
    "services",
    "iphone",
    "ipad",
    "mac",
    "watch",
    "vision pro",
    "android",
    "cloud",
    "ai",
    "genai",
    "ml",
    "hiring",
    "layoffs",
    "deal",
    "merger",
]


def looks_personal_finance(title: str, text: str) -> bool:
    blob = f"{title} {text}".lower()
    return any(h in blob for h in PERSONAL_FINANCE_HINTS)


def looks_company_news(title: str, text: str) -> bool:
    blob = f"{title} {text}".lower()
    return any(term in blob for term in NEWS_TERMS)


def alias_hits(text_lower: str):
    """Return set of tickers whose aliases appear in the provided lowercased text.

    `text_lower` should already be lowercase; alias keys are lowercase as well.
    """
    hits = set()
    for alias, ticker in ALIAS_TO_TICKER.items():
        # word-boundary-ish match against the already-lowercased blob
        if re.search(rf"\b{re.escape(alias)}\b", text_lower):
            hits.add(ticker)
    return hits


def detect_tickers_from_text(text: str, known_tickers=None):
    """Return explicit inline ticker-like tokens found in text.

    If `known_tickers` is provided, only return tickers present in that set.
    The returned tickers are uppercase as matched by the regex.
    """
    found = set()
    # normalize known tickers to uppercase for comparison
    kt = {t.upper() for t in (known_tickers or [])}
    for m in TICKER_CANDIDATE_RE.finditer(f" {text} "):
        tic = m.group("tic")
        if tic in IGNORE_TOKENS:
            continue
        if kt and tic not in kt:
            continue
        found.add(tic)
    return found


def repair_and_flag(orig_ticker: str, title: str, full_text: str, known_tickers=None):
    blob = f"{title}\n{full_text}".strip()
    low = blob.lower()

    alias_set = alias_hits(low)
    inline_set = detect_tickers_from_text(blob, known_tickers=known_tickers)

    pf = looks_personal_finance(title, full_text)
    news = looks_company_news(title, full_text)

    # Decision policy
    # 1) Prefer single explicit company alias
    if orig_ticker and orig_ticker in alias_set and len(alias_set) == 1 and news:
        repaired, conf = orig_ticker, "HIGH"
    elif len(alias_set) == 1:
        chosen = list(alias_set)[0]
        if news:
            repaired, conf = chosen, "HIGH"
        else:
            repaired, conf = ("MISC", "LOW") if pf else (chosen, "MEDIUM")
    elif len(alias_set) > 1:
        repaired, conf = ("MISC", "LOW") if pf else ("MULTI", "LOW")
    else:
        # No explicit company alias; consider inline cautiously
        if pf:
            repaired, conf = "MISC", "LOW"
        elif len(inline_set) == 1:
            repaired, conf = list(inline_set)[0], "MEDIUM"
        elif len(inline_set) > 1:
            repaired, conf = "MULTI", "LOW"
        else:
            repaired, conf = "UNASSIGNED", "LOW"

    detected = sorted(set(alias_set) | set(inline_set))

    if repaired == orig_ticker and conf == "HIGH":
        reason = "original_matches_text"
    elif repaired == orig_ticker and conf != "HIGH":
        reason = "original_but_weak_evidence"
    elif repaired == "MULTI":
        reason = f"multiple_detected:{detected}"
    elif repaired == "MISC":
        reason = "personal_finance_no_company_alias"
    elif repaired == "UNASSIGNED":
        reason = "no_company_match"
    else:
        reason = f"repaired_from_{orig_ticker}_to_{repaired}"

    return repaired, conf, detected, reason


def process(in_path: str, out_clean: str, out_filtered: str, report_csv: str):
    raw = json.loads(Path(in_path).read_text())
    cleaned = defaultdict(list)
    report_rows = []
    order_index = 0

    # Build a set of known tickers (normalize to uppercase for matching inline tokens)
    known_tickers = {k.upper() for k in set(raw.keys())} | {
        v.upper() for v in set(ALIAS_TO_TICKER.values())
    }

    for orig_ticker, items in raw.items():
        for it in items:
            title = (it.get("title") or "").strip()
            text = (it.get("full_text") or "").strip()
            link = (it.get("link") or "").strip()

            repaired_ticker, conf, detected, reason = repair_and_flag(
                orig_ticker, title, text, known_tickers=known_tickers
            )

            rec = {
                "id": f"{repaired_ticker}-{order_index}",
                "orig_ticker": orig_ticker,
                "repaired_ticker": repaired_ticker,
                "label_confidence": conf,
                "detected_tickers": detected,
                "reason": reason,
                "title": title,
                "full_text": text,
                "link": link,
                "order_index": order_index,
            }
            cleaned[repaired_ticker].append(rec)
            report_rows.append(rec | {"detected_tickers": ",".join(detected)})
            order_index += 1

    Path(out_clean).write_text(json.dumps(cleaned, ensure_ascii=False, indent=2))

    filtered = {
        k: [
            d
            for d in v
            if d["label_confidence"] in {"HIGH", "MEDIUM"}
            and d["repaired_ticker"] not in {"UNASSIGNED", "MISC"}
        ]
        for k, v in cleaned.items()
    }
    Path(out_filtered).write_text(json.dumps(filtered, ensure_ascii=False, indent=2))

    # CSV report (only write if we have rows)
    import csv

    if report_rows:
        with open(report_csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(report_rows[0].keys()))
            w.writeheader()
            w.writerows(report_rows)
    else:
        # Avoid raising if input dataset was empty
        Path(report_csv).write_text("")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--in", dest="inp", required=True, help="Path to original stock_news.json"
    )
    ap.add_argument(
        "--out-clean",
        dest="out_clean",
        required=True,
        help="Path to write cleaned JSON",
    )
    ap.add_argument(
        "--out-filtered",
        dest="out_filtered",
        required=True,
        help="Path to write filtered JSON for indexing",
    )
    ap.add_argument(
        "--report", dest="report_csv", required=True, help="Path to write CSV report"
    )
    args = ap.parse_args()

    process(args.inp, args.out_clean, args.out_filtered, args.report_csv)


if __name__ == "__main__":
    main()
