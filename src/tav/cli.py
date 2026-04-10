# ABOUTME: CLI entry point for tav, handling argument parsing and data loading.
# ABOUTME: Reads JSONL from a file or stdin, builds a RecordStore, and launches the TUI.
import argparse
import os
import sys
from importlib.metadata import version
from pathlib import Path

from tav.loader import KIND_OBJECT, load_lines
from tav.store import RecordStore
from tav.time_detect import detect_time_field


def _launch_app(
    store: RecordStore,
    time_field: str | None,
    time_parser,
    source_name: str,
    start_stats: bool,
) -> None:
    if os.environ.get("TAV_NO_UI"):
        return
    from tav.app import TavApp  # noqa: PLC0415
    TavApp(
        store=store,
        time_field=time_field,
        time_parser=time_parser,
        source_name=source_name,
        start_stats=start_stats,
    ).run()


def main() -> None:
    """Entry point registered in pyproject.toml as 'tav'."""
    parser = argparse.ArgumentParser(
        prog="tav",
        description="Terminal viewer for JSONL time-series data",
    )
    parser.add_argument(
        "input",
        nargs="?",
        default="-",
        metavar="INPUT",
        help="Path to input JSONL file, or '-' for stdin (default: stdin)",
    )
    parser.add_argument(
        "--time-field",
        metavar="JSONPATH",
        help="JSONPath pointing to the timestamp field (e.g. timestamp or $.timestamp)",
    )
    parser.add_argument(
        "--timezone",
        metavar="TZ",
        default="UTC",
        help="Timezone for naive timestamps without TZ info (default: UTC)",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Start in the stats view",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=version("tav"),
    )

    args = parser.parse_args()

    # ------------------------------------------------------------------
    # Resolve input source
    # ------------------------------------------------------------------
    if args.input == "-":
        print("Reading from stdin...", file=sys.stderr)
        result = load_lines(sys.stdin)
        source_name = "<stdin>"
    else:
        path = Path(args.input)
        if not path.exists():
            print(f"Error: file not found: {args.input}", file=sys.stderr)
            sys.exit(1)
        if not path.is_file():
            print(f"Error: not a file: {args.input}", file=sys.stderr)
            sys.exit(1)
        with path.open() as fh:
            result = load_lines(fh)
        source_name = path.name

    # ------------------------------------------------------------------
    # Warn on empty file
    # ------------------------------------------------------------------
    if not result.records:
        print("Warning: no records loaded (file is empty or contains no valid lines)", file=sys.stderr)
        sys.exit(0)

    # ------------------------------------------------------------------
    # Build store
    # ------------------------------------------------------------------
    store = RecordStore(result.records)

    # ------------------------------------------------------------------
    # Resolve time field
    # ------------------------------------------------------------------
    time_field: str | None = args.time_field

    if time_field is not None:
        # Validate: check if the path resolves on at least one loaded object record.
        objects = [r.value for r in result.records if r.kind == KIND_OBJECT]
        # Strip leading "$." for plain-field lookup so both "ts" and "$.ts" work.
        plain = time_field.removeprefix("$.")
        found = any(plain in rec for rec in objects)
        if not found:
            print(
                f"Warning: --time-field '{time_field}' did not match any record in the data",
                file=sys.stderr,
            )
        time_field = plain
    else:
        objects = [r.value for r in result.records if r.kind == KIND_OBJECT]
        time_field = detect_time_field(objects)

    # ------------------------------------------------------------------
    # Build time parser
    # ------------------------------------------------------------------
    from zoneinfo import ZoneInfo
    from tav.time_parse import create_time_parser

    try:
        tz = ZoneInfo(args.timezone)
    except KeyError:
        print(f"Error: unknown timezone: {args.timezone}", file=sys.stderr)
        sys.exit(1)
    time_parser = create_time_parser(assume_tz=tz)

    # ------------------------------------------------------------------
    # Launch TUI
    # ------------------------------------------------------------------
    _launch_app(
        store=store,
        time_field=time_field,
        time_parser=time_parser,
        source_name=source_name,
        start_stats=args.stats,
    )
