from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .adapters import ADAPTERS


def load_config(path: str | Path) -> Dict[str, Any]:
    """Load a TOML config into a dict. Callers pass a file path."""
    import tomllib

    p = Path(path)
    return tomllib.loads(p.read_text(encoding="utf-8"))


def plan(cfg: Dict[str, Any], *, since: Optional[str | float] = None) -> List[str]:
    """Return human-readable plan lines (keeps CLI format stable)."""
    out: List[str] = []
    for src in cfg.get("sources", []):
        line = f"plan: {src['type']}:{src['name']} -> {src['output']}"
        if since is not None:
            line += f" [since={since}]"
        out.append(line)
    return out


def run(
    cfg: Dict[str, Any], *, since: Optional[str | float] = None
) -> List[Dict[str, Any]]:
    """Run all configured sources via adapters. No network in tests."""
    results: List[Dict[str, Any]] = []
    for src in cfg.get("sources", []):
        name = src["name"]
        typ = src["type"]
        url = src["url"]
        out_path = src["output"]
        adapter = ADAPTERS.get(typ)
        if not adapter:
            results.append(
                {
                    "name": name,
                    "type": typ,
                    "ok": False,
                    "new": 0,
                    "total": 0,
                    "path": None,
                    "error": "unknown adapter",
                }
            )
            continue
        run_fn = getattr(adapter, "run", None)
        if callable(run_fn):
            r = run_fn(name=name, url=url, out_path=out_path, since=since)
            # normalize error key presence
            results.append(
                {
                    "name": name,
                    "type": typ,
                    **r,
                    "error": r.get("error") if not r.get("ok") else None,
                }
            )
        elif hasattr(adapter, "fetch"):
            # fetch-only fallback: count items
            n = len(adapter.fetch(url, name))
            results.append(
                {
                    "name": name,
                    "type": typ,
                    "ok": True,
                    "new": n,
                    "total": n,
                    "path": None,
                }
            )
        else:
            results.append(
                {
                    "name": name,
                    "type": typ,
                    "ok": False,
                    "new": 0,
                    "total": 0,
                    "path": None,
                    "error": "no run/fetch",
                }
            )
    return results
