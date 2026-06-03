#!/usr/bin/env python3
"""Mode C — typed Python types for nav-base state (no dora required).

Real nav-base motion needs the full dora-nav stack; this example just exercises
the typed surface.
"""
from __future__ import annotations

from nav_base_node.client import NavBaseClient, NavConfig
from nav_base_node.client.state import NavState


def main() -> None:
    cfg = NavConfig(robot_id="nav-base-001")
    client = NavBaseClient(config=cfg)
    print(f"client configured for {client.config.robot_id}")

    fake_snap = {
        "robot_id": "nav-base-001",
        "pose": {"x": 1.0, "y": 2.0, "theta": 0.0},
        "nav_status": "idle",
        "obstacles_count": 3,
        "estopped": False,
        "estop_reason": None,
        "controller_holder": None,
    }
    state = NavState.from_snapshot(fake_snap)
    print(f"state: {state}")


if __name__ == "__main__":
    main()
