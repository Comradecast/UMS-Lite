import argparse
import sys
import json
from importlib.metadata import version, PackageNotFoundError
import datetime

from transparencyx.ranges import parse_range
from transparencyx.sources.registry import get_registered_sources
from transparencyx.sources.downloader import Downloader

def main():
    parser = argparse.ArgumentParser(
        description="TransparencyX: A Python civic-data project that consolidates U.S. congressional financial disclosure information."
    )

    parser.add_argument(
        "--version",
        action="store_true",
        help="Show the version and exit."
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # "sources" command and its subcommands
    sources_parser = subparsers.add_parser("sources", help="Manage data sources")
    sources_subparsers = sources_parser.add_subparsers(dest="sources_command", help="Source operations")

    # "sources list"
    sources_subparsers.add_parser("list", help="List supported sources")

    # "sources fetch"
    fetch_parser = sources_subparsers.add_parser("fetch", help="Simulate fetching source disclosures")
    fetch_group = fetch_parser.add_mutually_exclusive_group(required=True)
    fetch_group.add_argument("--all", action="store_true", help="Fetch from all available sources")
    fetch_group.add_argument("--chamber", choices=["house", "senate"], help="Fetch for a specific chamber")

    # We add year here but make it default to previous year if not supplied for convenience,
    # though it wasn't strictly requested, it makes the command usable.
    fetch_parser.add_argument("--year", type=int, default=datetime.datetime.now().year - 1, help="The disclosure year to fetch")

    # "parse-range" command
    parse_parser = subparsers.add_parser("parse-range", help="Parse a financial disclosure range label")
    parse_parser.add_argument(
        "label",
        type=str,
        help="The range label to parse (e.g., '$1,001 - $15,000')"
    )

    args = parser.parse_args()

    if args.version:
        try:
            pkg_version = version("transparencyx")
            print(f"transparencyx version {pkg_version}")
        except PackageNotFoundError:
            print("transparencyx version unknown (not installed)")
        sys.exit(0)

    if args.command == "sources":
        if args.sources_command == "list":
            sources = get_registered_sources()
            for chamber in sources.keys():
                print(chamber)
        elif args.sources_command == "fetch":
            downloader = Downloader()
            paths = []
            if args.all:
                paths = downloader.fetch_all(args.year)
            elif args.chamber:
                paths = downloader.fetch_chamber(args.chamber, args.year)

            for path in paths:
                print(f"Fetched (placeholder): {path}")
        else:
            sources_parser.print_help()

    elif args.command == "parse-range":
        parsed = parse_range(args.label)

        output = {
            "label": parsed.original_label,
            "minimum": parsed.minimum,
            "maximum": parsed.maximum,
            "midpoint": parsed.midpoint,
        }

        print(json.dumps(output, indent=2))
    elif args.command is None:
        parser.print_help()

if __name__ == "__main__":
    main()
