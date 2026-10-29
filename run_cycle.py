"""Backward-compatible entry point: run a single monitoring cycle (same as `python main.py run-once`)."""
import sys

from main import main

if __name__ == "__main__":
    sys.exit(main(["run-once"]))
