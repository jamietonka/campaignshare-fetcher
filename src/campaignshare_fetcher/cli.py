# src/campaignshare_fetcher/cli.py
from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone
from typing import Any, Iterable

from .config import load_config

# Optional imports (adapters registry is preferred; fall back gracefully)
try:
    from .adapters import (
        ADAPTERS,
    )  # expected to contain {"rss": rss, "reddit_json": reddit_json, ...}
except Exception:  # pragma: no cover - tolerate partial installs during bootstrap
    ADAPTERS = {}

LOG = logging.getLogger("campaignshare.cli")


# ----------------------------
# Parsing / CLI surface
# ----------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="campaignshare",
        description="Fetch + normalize sources for CampaignShare.",
    )
    p.add_argument(
        "--log-level",
        default="INFO",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        help="Logging verbosity (default: INFO).",
    )

    sub = p.add_subparsers(dest="cmd")

    # plan (dry-run)
    pp = sub.add_parser("plan", help="Show what would be fetched (no writes).")
    _add_common_source_flags(pp)

    # run (fetch + write/dedupe)
    pr = sub.add_parser("run", help="Fetch and write outputs (with dedupe).")
    _add_common_source_flags(pr)

    # export (merge recent items into one JSON list)
    pe = sub.add_parser("export", help="Merge recent items across data/*.jsonl.")
    pe.add_argument("--config", "-c", required=True, help="Path to TOML config file.")
    pe.add_argument("--limit", type=int, default=200, help="Max items in export.")
    pe.add_argument("--out", required=True, help="Output JSON file path.")

    # Legacy (no subcommand): keep old behavior
    p.add_argument("--config", "-c", help="(legacy) Path to TOML config file.")
    p.add_argument(
        "--run",
        action="store_true",
        help="(legacy) Execute fetch/writes; without it, behaves like plan.",
    )
    p.add_argument(
        "--since",
        help="(legacy) ISO-8601 datetime filter (UTC assumed if no offset).",
    )

    return p


def _add_common_source_flags(ap: argparse.ArgumentParser) -> None:
    ap.add_argument("--config", "-c", required=True, help="Path to TOML config file.")
    ap.add_argument(
        "--since",
        help="ISO-8601 datetime filter (UTC assumed if no offset).",
    )


# ----------------------------
# Helpers
# ----------------------------
def _parse_since(s: str | None) -> datetime | None:
    if not s:
        return None
    # Accept ISO-8601 with or without timezone offset
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        raise SystemExit(f"--since must be ISO-8601, got: {s!r}")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _adapter_for(type_name: str):
    key = (type_name or "").lower().strip()
    mod = ADAPTERS.get(key)
    if not mod:
        raise SystemExit(f"unknown source type: {type_name!r} (no adapter registered)")
    return mod


def _supports(mod: Any, fn: str) -> bool:
    return hasattr(mod, fn) and callable(getattr(mod, fn))


# ----------------------------
# Commands
# ----------------------------
def cmd_plan(config_path: str, since: str | None) -> int:
    cfg = load_config(config_path)
    since_dt = _parse_since(since)

    for s in cfg.sources:
        out = s.options.get("output", "(no output)")
        extra = f" since={since_dt.isoformat()}" if since_dt else ""
        print(f"plan: {s.type}:{s.name} -> {out}{extra}")
    return 0


def cmd_run(config_path: str, since: str | None) -> int:
    cfg = load_config(config_path)
    since_dt = _parse_since(since)

    for s in cfg.sources:
        try:
            mod = _adapter_for(s.type)
        except SystemExit as e:
            print(f"skip {s.name}: {e}")
            continue

        url = s.options.get("url")
        out_path = s.options.get("output", "data/output.jsonl")
        if not url:
            print(f"skip {s.name}: missing 'url'")
            continue

        # Preferred adapter contract: run(name, url, out_path, since: datetime|None) -> dict
        if _supports(mod, "run"):
            try:
                res: dict[str, Any] = mod.run(s.name, url, out_path, since_dt)  # type: ignore[attr-defined]
            except TypeError:
                # Older signature without since
                res = mod.run(s.name, url, out_path)  # type: ignore[attr-defined]
        # Fallback: fetch(url, name) -> Iterable[dict]; we handle writing/dedupe nowhere (plan-only info)
        elif _supports(mod, "fetch"):
            try:
                items: Iterable[dict[str, Any]] = mod.fetch(url=url, name=s.name)  # type: ignore[attr-defined]
            except Exception as exc:  # runtime fetch failure
                print(f"err {s.name}: {exc}")
                continue
            count = 0
            cutoff = since_dt.timestamp() if since_dt else None
            for it in items:
                count += 1 if (not cutoff or _passes_since(it, cutoff)) else 0
            print(f"ok  {s.name}: {count} items (fetch-only; no write path wired)")
            continue
        else:
            print(f"skip {s.name}: adapter lacks run()/fetch()")
            continue

        if res.get("ok"):
            new = res.get("new", "?")
            total = res.get("total", "?")
            path = res.get("path", out_path)
            print(f"ok  {s.name}: {new}/{total} new → {path}")
        else:
            print(f"err {s.name}: {res.get('error')}")
    return 0


def _passes_since(item: dict[str, Any], cutoff_ts: float) -> bool:
    ts = item.get("created_at")
    if not ts:
        return False
    try:
        dt = datetime.fromisoformat(str(ts))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp() >= cutoff_ts
    except Exception:
        return False


def cmd_export(config_path: str, limit: int, out_path: str) -> int:
    # Import lazily to avoid circulars; modules expected in project already
    from .export import merge_recent_to_json  # your existing util (expected)

    return merge_recent_to_json(config_path, limit, out_path)  # should print/log itself


# ----------------------------
# Entry
# ----------------------------
def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(levelname)s %(name)s: %(message)s",
    )

    # Subcommand path
    if args.cmd == "plan":
        return cmd_plan(args.config, args.since)
    if args.cmd == "run":
        return cmd_run(args.config, args.since)
    if args.cmd == "export":
        return cmd_export(args.config, args.limit, args.out)

    # Legacy path (no subcommand)
    if args.config:
        return (
            cmd_run(args.config, args.since)
            if args.run
            else cmd_plan(args.config, args.since)
        )

    # No config, no subcommand: keep a minimal friendly message
    print(
        "campaignshare: provide a subcommand (plan/run/export) or --config with optional --run"
    )
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
