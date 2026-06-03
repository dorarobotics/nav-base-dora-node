"""Test doubles for NavBridge — let unit tests run without dora-nav."""
from __future__ import annotations

from typing import Any


class FakeNavBridge:
    """Records intents queued for emission; receives updates from tests directly."""

    def __init__(self) -> None:
        self.pending_goals: list[dict[str, Any]] = []
        self.pending_cmd_vels: list[dict[str, float]] = []
        self.pending_cancels: int = 0
        self._pose: dict[str, Any] | None = None
        self._status: str | None = None
        self._obstacles: list[dict[str, Any]] = []
        self.status_history: list[str] = []

    # Intent-emitter side (verbs call these)
    def request_goal(self, pose: dict[str, Any]) -> None:
        self.pending_goals.append(pose)

    def request_cmd_vel(self, cmd: dict[str, float]) -> None:
        self.pending_cmd_vels.append(cmd)

    def cancel(self) -> None:
        self.pending_cancels += 1

    # State-holder side (verbs read these)
    def latest_pose(self) -> dict[str, Any] | None:
        return self._pose

    def current_status(self) -> str | None:
        return self._status

    def latest_obstacles(self) -> list[dict[str, Any]]:
        return list(self._obstacles)

    # Inbound-from-dora side
    def on_pose_update(self, pose: dict[str, Any]) -> None:
        self._pose = dict(pose)

    def on_status_update(self, status: str) -> None:
        self._status = status
        self.status_history.append(status)

    def on_obstacles_update(self, obs: list[dict[str, Any]]) -> None:
        self._obstacles = list(obs)
