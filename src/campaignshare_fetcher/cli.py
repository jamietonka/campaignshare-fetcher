import argparse


def build_parser():
    p = argparse.ArgumentParser(
        prog="campaignshare", description="Fetch sources for CampaignShare (stub)."
    )
    p.add_argument("--source", "-s", default="demo", help="Source name or URL (stub).")
    p.add_argument("--dry-run", action="store_true", help="Show what would happen.")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.dry_run:
        print(f"[dry-run] would fetch from: {args.source}")
    else:
        print(f"campaignshare-fetcher: ready to fetch from {args.source} (stub)")


if __name__ == "__main__":
    main()
