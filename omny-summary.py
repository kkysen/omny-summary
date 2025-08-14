#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "pandas",
#     "typer",
# ]
# ///

from pathlib import Path
import typer


def main(trip_history_path: Path):
    print(trip_history_path)

if __name__ == "__main__":
    typer.run(main)
