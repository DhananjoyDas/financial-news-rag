# Data Cleanup Script Usage

```python
# generic example (replace <path_to_data> as needed)
python clean_news_dataset.py \
  --in <path_to_data>/stock_news.json \
  --out-clean <path_to_data>/stock_news.cleaned.json \
  --out-filtered <path_to_data>/stock_news.filtered.for_index.json \
  --report <path_to_data>/stock_news_label_report.csv
```

```python
# working example (copy/paste works)
python clean_news_dataset.py \
  --in ./stock_news.json \
  --out-clean ./stock_news.cleaned.json \
  --out-filtered ./stock_news.filtered.for_index.json \
  --report ./stock_news_label_report.csv
```

It produces:

- `stock_news.cleaned.json`– grouped by repaired_ticker, with label_confidence, detected_tickers, and reason.

- `stock_news.filtered.for_index.json` – only HIGH/MEDIUM items (excludes UNASSIGNED), ideal for indexing.

- `stock_news_label_report.csv` – flat audit log of every item and how it was labeled/repaired.


**NOTE:** For the project we only use file `stock_news.cleaned.json`