"""NavBridge — state holder + intent queue between SPEC verbs and dora topics.

NavBaseNode's verb handlers call the `NavBridge` Protocol methods (request_goal,
request_cmd_vel, cancel) and read the latest inbound state (latest_pose,
current_status, latest_obstacles). The dora runtime drains the queued outbound
intents onto dora-nav's input topics (dora_nav_goal / dora_nav_cancel /
dora_nav_cmd_vel) and pushes dora-nav's outputs back in via the on_*_update
methods. This is the topic-level integration described in the design spec §6.0 —
there is no in-process import of dora-nav.
"""
from __future__ import annotations

from collections import deque
from typing import Any, Protocol


class NavBridge(Protocol):
    def request_goal(self, pose: dict[str, Any]) -> None: ...
    def request_cmd_vel(self, cmd: dict[str, float]) -> None: ...
    def cancel(self) -> None: ...
    def latest_pose(self) -> dict[str, Any] | None: ...
    def current_status(self) -> str | None: ...
    def latest_obstacles(self) -> list[dict[str, Any]]: ...
    def on_pose_update(self, pose: dict[str, Any]) -> None: ...
    def on_status_update(self, status: str) -> None: ...
    def on_obstacles_update(self, obs: list[dict[str, Any]]) -> None: ...


class LocalNavBridge:
    """Concrete NavBridge used by the dora runtime.

    Outbound verb intents are appended to a single ordered buffer of
    ``(output_id, payload)`` pairs so causal order (e.g. cancel-then-cmd_vel for
    ``set_velocity``/``stop``) is preserved when the runtime drains them.
    Inbound dora-nav state is stored for the read methods.
    """

    def __init__(self) -> None:
        self._intents: deque[tuple[str, dict[str, Any]]] = deque()
        self._pose: dict[str, Any] | None = None
        self._status: str | None = None
        self._obstacles: list[dict[str, Any]] = []

    # ---- outbound intents (verbs call these) ----
    def request_goal(self, pose: dict[str, Any]) -> None:
        self._intents.append(("dora_nav_goal", dict(pose)))

    def request_cmd_vel(self, cmd: dict[str, float]) -> None:
        self._intents.append(("dora_nav_cmd_vel", dict(cmd)))

    def cancel(self) -> None:
        self._intents.append(("dora_nav_cancel", {}))

    def drain_intents(self) -> list[tuple[str, dict[str, Any]]]:
        """Return queued (output_id, payload) intents in order and clear them.
        Called by the runtime to publish onto the dora-nav input topics."""
        out = list(self._intents)
        self._intents.clear()
        return out

    # ---- inbound state (read by verbs) ----
    def latest_pose(self) -> dict[str, Any] | None:
        return self._pose

    def current_status(self) -> str | None:
        return self._status

    def latest_obstacles(self) -> list[dict[str, Any]]:
        return list(self._obstacles)

    # ---- inbound updates (runtime pushes these from dora inputs) ----
    def on_pose_update(self, pose: dict[str, Any]) -> None:
        self._pose = dict(pose)

    def on_status_update(self, status: str) -> None:
        self._status = status

    def on_obstacles_update(self, obs: list[dict[str, Any]]) -> None:
        self._obstacles = list(obs)
