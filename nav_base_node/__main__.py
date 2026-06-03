"""Dora entry point — `python -m nav_base_node`."""
from __future__ import annotations

import os
import sys


def main() -> int:
    robot_id = os.environ.get("ROBOT_ID")
    if not robot_id:
        sys.stderr.write("ROBOT_ID env var is required\n")
        return 2
    sys.stdout.write(f"nav_base_node starting for {robot_id}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
