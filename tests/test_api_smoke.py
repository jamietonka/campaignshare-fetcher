from campaignshare_fetcher import api


def test_plan_smoke(tmp_path):
    cfg = {
        "sources": [
            {
                "name": "x",
                "type": "reddit_json",
                "url": "u",
                "output": str(tmp_path / "o.jsonl"),
            }
        ]
    }
    out = api.plan(cfg, since="2024-01-01")
    assert out and out[0].startswith("plan: reddit_json:x ->")


def test_run_fetch_only(monkeypatch, tmp_path):
    from campaignshare_fetcher.adapters import reddit_json as rj

    # simulate fetch-only by disabling run
    if hasattr(rj, "run"):
        monkeypatch.setattr(rj, "run", None, raising=False)
    monkeypatch.setattr(rj, "fetch", lambda url, name: [{"id": "1"}], raising=True)
    cfg = {
        "sources": [
            {
                "name": "x",
                "type": "reddit_json",
                "url": "u",
                "output": str(tmp_path / "o.jsonl"),
            }
        ]
    }
    res = api.run(cfg)
    assert res and res[0]["ok"] and res[0]["total"] == 1
