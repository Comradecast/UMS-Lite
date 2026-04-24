import argparse
import sys
import json
from importlib.metadata import version, PackageNotFoundError

from transparencyx.ranges import parse_range


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
    elif args.command is None:
        parser.print_help()

if __name__ == "__main__":
    main()
