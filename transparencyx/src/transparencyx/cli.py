import argparse
import sys
import json
from importlib.metadata import version, PackageNotFoundError
import datetime
from pathlib import Path

from transparencyx.ranges import parse_range
from transparencyx.sources.registry import get_registered_sources
from transparencyx.sources.downloader import Downloader
from transparencyx.extract.registry import get_extractor_for_source
from transparencyx.config import RAW_DATA_DIR


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

    # "extract" command
    extract_parser = subparsers.add_parser("extract", help="Extract text from downloaded disclosures")
    extract_group = extract_parser.add_mutually_exclusive_group(required=True)
    extract_group.add_argument("--all", action="store_true", help="Extract all downloaded files")
    extract_group.add_argument("--chamber", choices=["house", "senate"], help="Extract for a specific chamber")


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

    elif args.command == "extract":
        search_dir = RAW_DATA_DIR

        # Determine the target directory based on the chamber argument
        if args.chamber:
            search_dir = RAW_DATA_DIR / args.chamber.lower()

        if not search_dir.exists():
            print(f"No raw data directory found at {search_dir}")
            sys.exit(0)

        # Iterate over files in the target directory (recursive)
        results = []
        for file_path in search_dir.rglob("*"):
            if file_path.is_file():
                # Derive file type from extension without the leading dot
                file_ext = file_path.suffix.lstrip(".")

                # We need a source identifier. In real usage, this might be embedded in DB or path.
                # Here we can derive it from the path components (e.g. "house" or "senate").
                # This assumes data/raw/{chamber}/...
                chamber_source = "unknown"
                try:
                    # search_dir could be data/raw or data/raw/house
                    # RAW_DATA_DIR is .../data/raw
                    rel_path = file_path.relative_to(RAW_DATA_DIR)
                    chamber_source = rel_path.parts[0]
                except ValueError:
                    pass

                extractor = get_extractor_for_source(file_ext)
                if extractor:
                    result = extractor.extract(file_path, chamber_source)
                    results.append({
                        "source": result.source,
                        "file_path": str(result.file_path),
                        "success": result.success,
                        "extracted_text": result.extracted_text,
                        "error": result.error
                    })
                else:
                    results.append({
                        "source": chamber_source,
                        "file_path": str(file_path),
                        "success": False,
                        "extracted_text": None,
                        "error": f"No extractor found for file type: {file_ext}"
                    })

        print(json.dumps(results, indent=2))

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
