# app/alias_map.py
ALIASES = {
    "AAPL": {"apple", "apple inc", "aapl", "iphone", "mac", "ipad", "watch", "vision pro"},
    "AMZN": {"amazon", "amazon.com", "amzn", "aws"},
    "MSFT": {"microsoft", "msft", "azure", "windows", "office", "copilot"},
    "GOOGL": {"alphabet", "google", "googl", "android", "gemini"},
    "META": {"meta", "facebook", "instagram", "whatsapp", "threads"},
    "NVDA": {"nvidia", "nvda"},
    "IBM": {"ibm", "international business machines"},
    "CSCO": {"cisco", "csco"},
    # add more as needed
}

def detect_tickers_from_query(q: str) -> set[str]:
    ql = q.lower()
    hits = set()
    for tkr, names in ALIASES.items():
        if any(a in ql for a in names):
            hits.add(tkr)
    return hits
