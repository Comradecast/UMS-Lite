import argparse
import sys
import json
from importlib.metadata import version, PackageNotFoundError

from transparencyx.ranges import parse_range
from transparencyx.sources.house import HouseDownloader
from transparencyx.sources.senate import SenateDownloader

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

    # "sources" command
    sources_parser = subparsers.add_parser("sources", help="List supported sources")

    # "parse-range" command
    parse_parser = subparsers.add_parser("parse-range", help="Parse a financial disclosure range label")
    parse_parser.add_argument(
        "label",
        type=str,
        help="The range label to parse (e.g., '$1,001 - $15,000')"
    )

    # "download" command
    download_parser = subparsers.add_parser("download", help="Simulate downloading source disclosures")
    download_parser.add_argument(
        "chamber",
        choices=["house", "senate"],
        help="The chamber to download disclosures for"
    )
    download_parser.add_argument(
        "year",
        type=int,
        help="The disclosure year to download"
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
        print("house")
        print("senate")
    elif args.command == "parse-range":
        parsed = parse_range(args.label)

        output = {
            "label": parsed.original_label,
            "minimum": parsed.minimum,
            "maximum": parsed.maximum,
            "midpoint": parsed.midpoint,
        }

        print(json.dumps(output, indent=2))
    elif args.command == "download":
        if args.chamber == "house":
            downloader = HouseDownloader()
        else:
            downloader = SenateDownloader()

        paths = downloader.download(args.year)
        for path in paths:
            print(f"Simulated download to: {path}")
    elif args.command is None:
        parser.print_help()

if __name__ == "__main__":
    main()
