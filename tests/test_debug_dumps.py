import os
import sys
import json

# Ensure project root on path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi.testclient import TestClient
from app.main import app


def test_debug_dumps_created(monkeypatch, tmp_path):
    # Monkeypatch retrieve to return deterministic hits
    def fake_retrieve(idx, q, k=8):
        return [
            {"id": "1", "title": "A", "link": "u1", "text": "t1"},
            {"id": "2", "title": "B", "link": "u2", "text": "t2"},
            {"id": "3", "title": "C", "link": "u3", "text": "t3"},
        ]

    monkeypatch.setattr("app.main.retrieve", fake_retrieve)

    # ensure /tmp paths point to tmp_path for safety in test environment
    monkeypatch.setenv("TMPDIR", str(tmp_path))

    client = TestClient(app)
    resp = client.post("/chat", json={"question": "Any recent IBM partnerships mentioned?"})
    assert resp.status_code == 200

    # Check files exist in /tmp (or TMPDIR)
    # Some environments map /tmp to TMPDIR, so check both
    candidates = [tmp_path / "last_hits.json", tmp_path / "last_context.txt"]
    # Also check /tmp in case the app wrote there directly
    candidates.extend([os.path.join('/tmp', 'last_hits.json'), os.path.join('/tmp', 'last_context.txt')])

    found = False
    for c in candidates:
        if os.path.exists(str(c)):
            found = True
            break

    assert found, f"Expected debug dump files to exist in {candidates}"
