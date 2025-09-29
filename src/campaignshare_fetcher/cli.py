import argparse
import logging


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
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level))
    logging.debug("parsed args: %s", args)

    if args.dry_run:
        print(f"[dry-run] would fetch from: {args.source}")
    else:
        print(f"campaignshare-fetcher: ready to fetch from {args.source} (stub)")


if __name__ == "__main__":
    main()
