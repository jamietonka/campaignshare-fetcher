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


def run(name, url, out_path, since=None):
    import json
    import datetime as dt

    try:
        items = fetch(url, name)  # offline
    except Exception as e:
        return {"ok": False, "error": str(e)}

    def _parse_since(s):
        if s is None:
            return None
        try:
            return float(s)
        except Exception:
            pass
        try:
            y, m, d = map(int, str(s).split("-"))
            return dt.datetime(y, m, d, tzinfo=dt.timezone.utc).timestamp()
        except Exception:
            return None

    cut = _parse_since(since)
    if cut is not None:

        def _ts(it):
            for k in ("created_utc", "created", "timestamp"):
                v = it.get(k)
                try:
                    return float(v)
                except Exception:
                    pass
            return None

        items = [it for it in items if (_ts(it) is None or _ts(it) >= cut)]
    from pathlib import Path as _P

    outp = _P(out_path)
    outp.parent.mkdir(parents=True, exist_ok=True)
    state_p = outp.with_suffix(outp.suffix + ".state")
    seen = set()
    if state_p.exists():
        seen = {ln.strip() for ln in state_p.read_text().splitlines() if ln.strip()}

    def _id(it):
        for k in ("id", "permalink", "url", "guid", "link"):
            v = it.get(k)
            if v:
                return str(v)
        return str(hash((it.get("title", ""), it.get("url", ""))))

    new = [it for it in items if _id(it) not in seen]
    if new:
        with outp.open("a", encoding="utf-8") as f:
            for it in new:
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
        seen.update(_id(it) for it in new)
        state_p.write_text("\n".join(sorted(seen)))
    return {"ok": True, "new": len(new), "total": len(items), "path": str(outp)}
