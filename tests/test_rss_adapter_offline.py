import json
from campaignshare_fetcher.adapters import rss

ATOM_SAMPLE = b"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Sample Atom</title>
  <entry>
    <id>tag:example.org,2025-09-29:/posts/1</id>
    <title>First</title>
    <updated>2025-09-29T12:00:00Z</updated>
    <link rel="alternate" href="https://example.org/posts/1"/>
  </entry>
  <entry>
    <id>tag:example.org,2025-09-29:/posts/2</id>
    <title>Second</title>
    <updated>2025-09-29T12:05:00Z</updated>
    <link rel="alternate" href="https://example.org/posts/2"/>
  </entry>
</feed>
"""
RSS_SAMPLE = b"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
  <channel>
    <title>Sample RSS</title>
    <item>
      <title>A</title>
      <link>https://example.org/a</link>
      <guid>guid-a</guid>
      <pubDate>Mon, 29 Sep 2025 12:00:00 +0000</pubDate>
    </item>
    <item>
      <title>B</title>
      <link>https://example.org/b</link>
      <guid>guid-b</guid>
      <pubDate>Mon, 29 Sep 2025 12:05:00 +0000</pubDate>
    </item>
  </channel>
</rss>
"""


def test_parse_atom_two_entries():
    items = list(rss.parse_feed(ATOM_SAMPLE))
    assert len(items) == 2
    assert items[0]["title"] == "First"
    assert items[0]["url"] == "https://example.org/posts/1"


def test_parse_rss_two_items():
    items = list(rss.parse_feed(RSS_SAMPLE))
    assert len(items) == 2
    assert items[1]["title"] == "B"
    assert items[1]["url"] == "https://example.org/b"


def test_run_dedup(monkeypatch, tmp_path):
    # stub network to return the ATOM sample
    monkeypatch.setattr(rss, "_http_get", lambda url, timeout=20.0: ATOM_SAMPLE)

    out = tmp_path / "out.jsonl"
    state_dir = tmp_path / "state"

    # first run writes 2 new
    res1 = rss.run(
        "sample", "http://feed.example/atom", str(out), state_dir=str(state_dir)
    )
    assert res1["ok"] and res1["total"] == 2 and res1["new"] == 2
    lines1 = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines1) == 2
    _ = [json.loads(s) for s in lines1]  # JSON sanity

    # second run adds 0 new (dedupe via state)
    res2 = rss.run(
        "sample", "http://feed.example/atom", str(out), state_dir=str(state_dir)
    )
    assert res2["ok"] and res2["total"] == 2 and res2["new"] == 0
    lines2 = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines2) == 2
