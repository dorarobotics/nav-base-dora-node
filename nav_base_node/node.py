"""NavBaseNode — dora node bridging SPEC-V1 verbs to dora-nav's topic surface."""
from __future__ import annotations

import logging
from typing import Any, Callable

from nav_base_node._watchdog import HeartbeatWatchdog
from nav_base_node.controller_guard import ControllerGuard

logger = logging.getLogger(__name__)


class NavBaseNode:
    """Spec-conforming dora node. Verbs are dispatched by name in `dispatch`."""

    def __init__(
        self,
        *,
        robot_id: str,
        waypoints_path: str = "load_path.yml",
        heartbeat_timeout_ms: int = 1000,
    ) -> None:
        self.robot_id = robot_id
        self.waypoints_path = waypoints_path
        self.heartbeat_timeout_ms = heartbeat_timeout_ms
        self._verbs: dict[str, Callable[..., Any]] = {}
        self.is_estopped: bool = False
        self.estop_reason: str | None = None
        self._guard = ControllerGuard()

    def register_verb(self, name: str, handler: Callable[..., Any]) -> None:
        if name in self._verbs:
            raise ValueError(f"verb already registered: {name}")
        self._verbs[name] = handler

    def dispatch(self, verb: str, args: dict[str, Any]) -> dict[str, Any]:
        if verb not in self._verbs:
            return {"ok": False, "code": "INVALID_PARAMS", "msg": f"unknown verb: {verb}"}
        return self._verbs[verb](**args)

    def install_common_verbs(self) -> None:
        """Register the four SPEC-V1 §8.1 common verbs."""
        self._watchdog = HeartbeatWatchdog(
            timeout_s=self.heartbeat_timeout_ms / 1000.0,
            on_timeout=self._on_heartbeat_timeout,
        )
        self.register_verb("robot.heartbeat", self._verb_heartbeat)
        self.register_verb("robot.estop", self._verb_estop)
        self.register_verb("robot.release_control", self._verb_release_control)

    def _verb_heartbeat(self) -> dict[str, Any]:
        self._watchdog.heartbeat()
        return {"ok": True, "code": "0"}

    def _on_heartbeat_timeout(self, _t: float) -> None:
        logger.warning("heartbeat timeout on %s", self.robot_id)

    def _verb_estop(self, *, reason: str = "unspecified") -> dict[str, Any]:
        self.is_estopped = True
        self.estop_reason = reason
        return {"ok": True, "code": "0"}

    def _verb_release_control(self, *, control_source: str = "") -> dict[str, Any]:
        self._guard.release(control_source)
        return {"ok": True, "code": "0"}
