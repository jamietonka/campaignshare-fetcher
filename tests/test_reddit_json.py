from __future__ import annotations
import json
from pathlib import Path

import campaignshare_fetcher.adapters.reddit_json as reddit

FIXTURE = Path(__file__).parent / "fixtures" / "reddit_new.json"


class _Resp:
    def __init__(self, payload: dict):
        self._payload = payload
        self.status_code = 200

    def raise_for_status(self):  # pragma: no cover
        return

    def json(self):
        return self._payload


def test_fetch_normalizes(monkeypatch):
    payload = json.loads(FIXTURE.read_text())

    def fake_get(url, headers=None, timeout=0):
        assert "reddit.com" in url
        assert "User-Agent" in headers
        return _Resp(payload)

    monkeypatch.setattr("campaignshare.adapters.reddit_json.requests.get", fake_get)

    url = "https://www.reddit.com/r/CityBuildPorn/new.json?limit=2"
    items = reddit.fetch(url=url, name="citybuilding")

    assert len(items) == 2
    for it in items:
        assert set(it.keys()) >= {
            "id",
            "title",
            "url",
            "summary",
            "created_at",
            "tags",
            "source",
        }
        assert it["tags"][0] == "reddit"
        assert it["tags"][1].startswith("r/")

    ids = [i["id"] for i in items]
    assert ids == ["reddit:abc123", "reddit:def456"]
    assert items[0]["created_at"].endswith("+00:00")
    assert "line 1 line 2" in items[0]["summary"]
    assert items[1]["summary"] == ""


def test_summary_truncation():
    s = reddit._summary("x" * 400, limit=50)
    assert len(s) == 50
    assert s.endswith("…")
