import argparse
import logging
from .config import load_config


def build_parser():
    p = argparse.ArgumentParser(
        prog="campaignshare", description="Fetch sources for CampaignShare (stub)."
    )
    p.add_argument("--source", "-s", default="demo", help="Source name or URL (stub).")
    p.add_argument("--dry-run", action="store_true", help="Show what would happen.")
    p.add_argument(
        "--log-level",
        default="INFO",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        help="Logging verbosity.",
    )
    p.add_argument("--config", "-c", help="Path to a TOML config file.")
    p.add_argument(
        "--run", action="store_true", help="Execute the plan (fetch + write outputs)."
    )
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level))
    logging.debug("parsed args: %s", args)

    if args.config:
        cfg = load_config(args.config)
        if not args.run:
            for s in cfg.sources:
                print(
                    f"plan: {s.type}:{s.name} -> {s.options.get('output', '(no output)')}"
                )
            return
        # execute sources
        from .adapters import rss

        for s in cfg.sources:
            stype = s.type.lower()
            if stype == "rss":
                url = s.options.get("url")
                out = s.options.get("output", "data/output.jsonl")
                if not url:
                    print(f"skip {s.name}: missing 'url'")
                    continue
                res = rss.run(s.name, url, out)
                if res.get("ok"):
                    print(
                        f"ok  {s.name}: {res['new']}/{res['total']} new → {res['path']}"
                    )
                else:
                    print(f"err {s.name}: {res.get('error')}")
            else:
                print(f"skip {s.name}: unknown type '{s.type}'")
        return

    if args.dry_run:
        print(f"[dry-run] would fetch from: {args.source}")
    else:
        print(f"campaignshare-fetcher: ready to fetch from {args.source} (stub)")


if __name__ == "__main__":
    main()
