"""NavBaseNode — dora node bridging SPEC-V1 verbs to dora-nav's topic surface."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable, cast

from nav_base_node._watchdog import HeartbeatWatchdog
from nav_base_node.controller_guard import ControllerGuard

if TYPE_CHECKING:
    from nav_base_node.nav_bridge import NavBridge
    from nav_base_node.waypoints import Waypoints

logger = logging.getLogger(__name__)


class NavBaseNode:
    """Spec-conforming dora node. Verbs are dispatched by name in `dispatch`."""

    def __init__(
        self,
        *,
        robot_id: str,
        waypoints_path: str = "load_path.yml",
        heartbeat_timeout_ms: int = 1000,
        nav_bridge: NavBridge | None = None,
    ) -> None:
        self.robot_id = robot_id
        self.waypoints_path = waypoints_path
        self.heartbeat_timeout_ms = heartbeat_timeout_ms
        self._verbs: dict[str, Callable[..., Any]] = {}
        self.is_estopped: bool = False
        self.estop_reason: str | None = None
        self._guard = ControllerGuard()
        self._bridge = nav_bridge

    def register_verb(self, name: str, handler: Callable[..., Any]) -> None:
        if name in self._verbs:
            raise ValueError(f"verb already registered: {name}")
        self._verbs[name] = handler

    def dispatch(self, verb: str, args: dict[str, Any]) -> dict[str, Any]:
        if verb not in self._verbs:
            return {"ok": False, "code": "INVALID_PARAMS", "msg": f"unknown verb: {verb}"}
        return cast(dict[str, Any], self._verbs[verb](**args))

    def install_common_verbs(self) -> None:
        """Register the four SPEC-V1 §8.1 common verbs."""
        self._watchdog = HeartbeatWatchdog(
            timeout_s=self.heartbeat_timeout_ms / 1000.0,
            on_timeout=self._on_heartbeat_timeout,
        )
        self.register_verb("robot.heartbeat", self._verb_heartbeat)
        self.register_verb("robot.estop", self._verb_estop)
        self.register_verb("robot.release_control", self._verb_release_control)
        self.register_verb("robot.get_capabilities", self._verb_get_capabilities)

    def install_motion_verbs(self) -> None:
        """Register vendor.dora_nav.base motion verbs."""
        if self._bridge is None:
            raise ValueError("nav_bridge required to install motion verbs")
        self.register_verb("vendor.dora_nav.base.go_to_pose", self._verb_go_to_pose)
        self.register_verb("vendor.dora_nav.base.go_to_named", self._verb_go_to_named)
        self.register_verb("vendor.dora_nav.base.set_velocity", self._verb_set_velocity)
        self.register_verb("vendor.dora_nav.base.stop", self._verb_stop)

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

    def _verb_get_capabilities(self) -> dict[str, Any]:
        return {
            "ok": True,
            "code": "0",
            "data": {
                "spec_version": "1.0.0",
                "vendor": "dora_nav",
                "model": "base",
                "robot_id": self.robot_id,
                "heartbeat_timeout_ms": self.heartbeat_timeout_ms,
                "verbs": sorted(self._verbs.keys()),
                "streams": ["state", "capabilities", "safety_event"],
            },
        }

    def _verb_go_to_pose(
        self, *, pose: dict[str, Any], control_source: str = ""
    ) -> dict[str, Any]:
        if self.is_estopped:
            return {
                "ok": False,
                "code": "VENDOR_ERROR",
                "msg": f"node is estopped: {self.estop_reason}",
            }
        if not isinstance(pose, dict) or "position" not in pose or "orientation" not in pose:
            return {
                "ok": False,
                "code": "INVALID_PARAMS",
                "msg": "pose must include `position` (xyz) and `orientation` (xyzw)",
            }
        position = pose["position"]
        if not isinstance(position, list) or len(position) != 3:
            return {
                "ok": False,
                "code": "INVALID_PARAMS",
                "msg": "position must be a length-3 list",
            }
        try:
            self._guard.acquire(control_source)
        except Exception as e:
            return {"ok": False, "code": "CONTROLLER_BUSY", "msg": str(e)}
        assert self._bridge is not None
        self._bridge.request_goal(pose)
        return {"ok": True, "code": "0"}

    def _load_waypoints(self) -> Waypoints | None:
        from nav_base_node.waypoints import load_waypoints  # noqa: PLC0415

        try:
            return load_waypoints(self.waypoints_path)
        except FileNotFoundError:
            return None

    def _verb_go_to_named(
        self, *, name: str, control_source: str = ""
    ) -> dict[str, Any]:
        if self.is_estopped:
            return {
                "ok": False,
                "code": "VENDOR_ERROR",
                "msg": f"node is estopped: {self.estop_reason}",
            }
        wp = self._load_waypoints()
        if wp is None:
            return {
                "ok": False,
                "code": "INVALID_PARAMS",
                "msg": f"waypoints file not found: {self.waypoints_path}",
            }
        try:
            pose = wp.lookup(name)
        except KeyError as e:
            return {"ok": False, "code": "INVALID_PARAMS", "msg": str(e)}
        try:
            self._guard.acquire(control_source)
        except Exception as e:
            return {"ok": False, "code": "CONTROLLER_BUSY", "msg": str(e)}
        assert self._bridge is not None
        self._bridge.request_goal(pose)
        return {"ok": True, "code": "0"}

    def _verb_set_velocity(
        self, *, linear: float, angular: float, control_source: str = ""
    ) -> dict[str, Any]:
        if self.is_estopped:
            return {
                "ok": False,
                "code": "VENDOR_ERROR",
                "msg": f"node is estopped: {self.estop_reason}",
            }
        try:
            self._guard.acquire(control_source)
        except Exception as e:
            return {"ok": False, "code": "CONTROLLER_BUSY", "msg": str(e)}
        assert self._bridge is not None
        self._bridge.cancel()
        self._bridge.request_cmd_vel(
            {"linear": float(linear), "angular": float(angular)}
        )
        return {"ok": True, "code": "0"}

    def _verb_stop(self) -> dict[str, Any]:
        # stop is privileged: works even during estop, ignores controller lock.
        assert self._bridge is not None
        self._bridge.cancel()
        self._bridge.request_cmd_vel({"linear": 0.0, "angular": 0.0})
        return {"ok": True, "code": "0"}
