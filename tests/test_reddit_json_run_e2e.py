from __future__ import annotations
import json
from pathlib import Path

import campaignshare_fetcher.adapters.reddit_json as reddit


def test_reddit_json_run_end_to_end(tmp_path, monkeypatch):
    # deterministic fixture (no network)
    items = [
        {"id": "a", "title": "A", "url": "u1", "created_utc": 1000},
        {"id": "b", "title": "B", "url": "u2", "created_utc": 2000},
        {"id": "c", "title": "C", "url": "u3", "created_utc": 3000},
    ]
    monkeypatch.setattr(reddit, "fetch", lambda url, name: items)

    out1 = tmp_path / "out.jsonl"
    # 1st run: writes all 3; state recorded
    r1 = reddit.run("name", "http://example", str(out1))
    assert r1 == {"ok": True, "new": 3, "total": 3, "path": str(out1)}
    assert out1.exists()
    lines = out1.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    # spot-check a line is valid json
    assert json.loads(lines[0])["id"] in {"a", "b", "c"}

    # state file exists and contains ids
    state1 = Path(str(out1) + ".state")
    assert state1.exists()
    state_ids = set(state1.read_text().split())
    assert {"a", "b", "c"} <= state_ids
    # 2nd run: no new writes (dedupe)
    r2 = reddit.run("name", "http://example", str(out1))
    assert r2 == {"ok": True, "new": 0, "total": 3, "path": str(out1)}

    # fresh path + since filter: only items >= 2500 (just "c")
    out2 = tmp_path / "out_since.jsonl"
    r3 = reddit.run("name", "http://example", str(out2), since=2500)
    assert r3 == {"ok": True, "new": 1, "total": 1, "path": str(out2)}
    assert out2.read_text(encoding="utf-8").count("\n") == 1
