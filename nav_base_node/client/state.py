"""Mode C state types — mirror what the dora `state` topic emits."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class NavState:
    robot_id: str
    pose: dict[str, Any] | None
    nav_status: str | None
    obstacles_count: int
    estopped: bool
    estop_reason: str | None
    controller_holder: str | None

    @classmethod
    def from_snapshot(cls, snap: dict[str, Any]) -> "NavState":
        return cls(
            robot_id=snap["robot_id"],
            pose=snap.get("pose"),
            nav_status=snap.get("nav_status"),
            obstacles_count=int(snap.get("obstacles_count", 0)),
            estopped=bool(snap["estopped"]),
            estop_reason=snap.get("estop_reason"),
            controller_holder=snap.get("controller_holder"),
        )
