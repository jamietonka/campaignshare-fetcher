from __future__ import annotations

import datetime as dt
from typing import Any, Dict, Iterable, List

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
    """
    Fetch and normalize a Reddit listing JSON payload into a list[dict].
    NOTE: Tests monkeypatch requests.get; no network is used during tests.
    """
    resp = requests.get(url, headers={"User-Agent": UA}, timeout=20)
    resp.raise_for_status()
    payload = resp.json()
    children: Iterable[Dict[str, Any]] = payload.get("data", {}).get("children", [])
    out: List[Dict[str, Any]] = []
    for child in children:
        d = child.get("data", {})
        subreddit = d.get("subreddit") or name
        url_out = d.get("url") or f"https://www.reddit.com{d.get('permalink', '')}"
        out.append(
            {
                "id": f"reddit:{d.get('id')}",
                "title": d.get("title") or "",
                "url": url_out,
                "summary": _summary(d.get("selftext")),
                # normalized ISO8601; useful for human inspection
                "created_at": _to_iso_utc(d.get("created_utc", 0)),
                "tags": ["reddit", f"r/{subreddit}"],
                "source": {"type": "reddit_json", "name": name, "url": url},
                # keep original epoch when present; useful for filtering
                "created_utc": d.get("created_utc"),
                "permalink": d.get("permalink"),
            }
        )
    return out


def run(name: str, url: str, out_path: str, since: Any | None = None) -> Dict[str, Any]:
    """
    Stateful JSONL writer using fetch(url, name).

    Returns:
      {'ok': True/False, 'new': n_new, 'total': n_total, 'path'|'error'}.
    """
    import json
    from pathlib import Path as _P

    try:
        items = fetch(url, name)
    except Exception as e:  # defensive: normalize failure into result dict
        return {"ok": False, "error": str(e)}

    def _parse_since(s: Any | None) -> float | None:
        if s is None:
            return None
        if isinstance(s, (int, float)):
            return float(s)
        st = str(s).strip()
        # numeric string (epoch seconds)
        try:
            return float(st)
        except Exception:
            pass
        # YYYY-MM-DD
        try:
            y, m, d = map(int, st.split("-"))
            return dt.datetime(y, m, d, tzinfo=dt.timezone.utc).timestamp()
        except Exception:
            return None

    cut = _parse_since(since)

    if cut is not None:

        def _ts(it: Dict[str, Any]) -> float | None:
            # prefer explicit epoch fields when available
            for k in ("created_utc", "created", "timestamp"):
                if k in it and it[k] is not None:
                    try:
                        return float(it[k])
                    except Exception:
                        pass
            # try ISO8601 fields
            for k in ("created_at", "published", "date"):
                v = it.get(k)
                if isinstance(v, str):
                    try:
                        iso = v.replace("Z", "+00:00")
                        dtt = dt.datetime.fromisoformat(iso)
                        if dtt.tzinfo is None:
                            dtt = dtt.replace(tzinfo=dt.timezone.utc)
                        return dtt.timestamp()
                    except Exception:
                        pass
            return None

        items = [it for it in items if (_ts(it) is None or _ts(it) >= cut)]

    outp = _P(out_path)
    outp.parent.mkdir(parents=True, exist_ok=True)
    state_p = outp.with_suffix(outp.suffix + ".state")

    # load seen IDs
    seen: set[str] = set()
    if state_p.exists():
        try:
            seen = {ln.strip() for ln in state_p.read_text().splitlines() if ln.strip()}
        except Exception:
            seen = set()

    def _id(it: Dict[str, Any]) -> str:
        for k in ("id", "permalink", "url", "guid", "link"):
            v = it.get(k)
            if v:
                return str(v)
        # fallback: stable hash on (title, url)
        return str(hash((it.get("title", ""), it.get("url", ""))))

    new_items = [it for it in items if _id(it) not in seen]

    if new_items:
        mode = "a" if outp.exists() else "w"
        with outp.open(mode, encoding="utf-8") as f:
            for it in new_items:
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
        # update state
        seen.update(_id(it) for it in new_items)
        try:
            state_p.write_text("\n".join(sorted(seen)))
        except Exception:
            # non-fatal: output was written successfully
            pass

    return {"ok": True, "new": len(new_items), "total": len(items), "path": str(outp)}
