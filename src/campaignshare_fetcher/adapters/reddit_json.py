from __future__ import annotations
import datetime as dt
from typing import Dict, Any, Iterable, List
import requests

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124 Safari/537.36"
)


def _to_iso_utc(created_utc: float | int) -> str:
    return dt.datetime.fromtimestamp(float(created_utc), dt.timezone.utc).isoformat()


def _summary(text: str | None, limit: int = 280) -> str:
    if not text:
        return ""
    s = text.strip().replace("\r", " ").replace("\n", " ")
    return (s[: limit - 1] + "…") if len(s) > limit else s


def fetch(url: str, name: str) -> List[Dict[str, Any]]:
    resp = requests.get(url, headers={"User-Agent": UA}, timeout=20)
    resp.raise_for_status()
    payload = resp.json()
    children: Iterable[Dict[str, Any]] = payload.get("data", {}).get("children", [])
    out: List[Dict[str, Any]] = []
    for child in children:
        d = child.get("data", {})
        subreddit = d.get("subreddit") or name
        url_out = d.get("url") or f"https://www.reddit.com{d.get('permalink','')}"
        out.append(
            {
                "id": f"reddit:{d.get('id')}",
                "title": d.get("title") or "",
                "url": url_out,
                "summary": _summary(d.get("selftext")),
                "created_at": _to_iso_utc(d.get("created_utc", 0)),
                "tags": ["reddit", f"r/{subreddit}"],
                "source": {"type": "reddit_json", "name": name, "url": url},
            }
        )
    return out
