"""NavBaseClient — typed Mode C surface. Currently a thin holder for config + state.

Driving the base from Python requires standing up the dora dataflow (with dora-nav).
There's no in-process navigation library to call directly. Mode C usefulness here
is mainly: state holder, type-safe `Pose2D` serialization, future RPC client.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NavConfig:
    robot_id: str
    waypoints_path: str = "load_path.yml"


class NavBaseClient:
    def __init__(self, *, config: NavConfig) -> None:
        self.config = config
