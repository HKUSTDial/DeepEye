"""CLI entry point for the optional, offline-by-default acceptance harness."""

import argparse
from pathlib import Path

from app.knowledge.acceptance import run

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--live", action="store_true", help="Make up to 24 configured-model calls, without retries")
    args = parser.parse_args()
    run(args.output, args.live)
