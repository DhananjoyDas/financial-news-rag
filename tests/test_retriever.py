from app.data_loader import load_news
from app.deps import get_index
from app.retriever import build_index, retrieve

docs = load_news("stock_news.json")
idx = build_index(docs)
q = "Apple earnings"
hits = retrieve(idx, q, k=3)
print("Hits:", len(hits))
for h in hits:
    print("-", h["title"], h["link"])


def test_retriever_prefers_target_but_allows_detected():
    idx = get_index()  # built over cleaned file
    out = retrieve(idx, "What’s new with Apple this quarter?", k=6)
    # mostly AAPL or detected_tickers containing AAPL
    primary = sum(1 for d in out if d["repaired_ticker"] == "AAPL")
    detected = sum(1 for d in out if "AAPL" in (d.get("detected_tickers") or []))
    assert primary + detected >= 4, "Too few Apple-centric docs returned"
