"""Dora runtime for NavBaseNode — the piece that makes it a runnable dora node.

Kept separate from node.py so the verb logic stays import-light and unit-testable
without a dora runtime. The loop here is verifiable too: `handle_request`,
`on_event`, `publish_state_once`, and `tick_watchdog_once` all run against a
``DoraNodeLike`` fake plus the real ``LocalNavBridge``. Only `main()` touches the
real `dora.Node()` (needs a running dora daemon) and is the single
unverified-by-unit-test seam.

Topic-level dora-nav integration (spec §6.0): inbound dora inputs
``dora_nav_pose`` / ``dora_nav_status`` / ``dora_nav_obstacles`` are pushed into
the LocalNavBridge; outbound verb intents queued on the bridge (goals, cancels,
cmd_vels) are drained and published on ``dora_nav_goal`` / ``dora_nav_cancel`` /
``dora_nav_cmd_vel``. Threading mirrors the agibot-a2 reference: cmd_request
events arrive serially on the main thread; two daemon workers publish the
``state`` stream (5 Hz) and tick the watchdog (10 Hz).
"""
from __future__ import annotations

import json
import logging
import os
import threading
from typing import Any, Protocol

import pyarrow as pa

from nav_base_node._envelope import (
    InvalidEnvelope,
    build_cmd_response,
    error_response_for_raw,
    parse_cmd_request,
)
from nav_base_node.nav_bridge import LocalNavBridge
from nav_base_node.node import NavBaseNode

logger = logging.getLogger(__name__)

STATE_PERIOD_S = 0.2  # 5 Hz state stream
WATCHDOG_PERIOD_S = 0.1  # 10 Hz watchdog tick


class DoraNodeLike(Protocol):
    def send_output(self, output_id: str, data: Any) -> None: ...


def _decode_value(value: Any) -> Any:
    """Decode a dora INPUT value (pyarrow array of one JSON item) to a Python
    object (dict for envelopes/poses, str for status, list for obstacles)."""
    try:
        decoded = value.to_pylist() if hasattr(value, "to_pylist") else list(value)
    except Exception:  # noqa: BLE001
        logger.exception("failed to read dora input value")
        return None
    if not decoded:
        return None
    first = decoded[0]
    if isinstance(first, str):
        try:
            return json.loads(first)
        except (json.JSONDecodeError, ValueError):
            logger.exception("failed to decode JSON value")
            return None
    return first


def _emit(dora_node: DoraNodeLike, output_id: str, payload: Any) -> None:
    dora_node.send_output(output_id, pa.array([json.dumps(payload)]))


class NavBaseRuntime:
    """Binds a NavBaseNode + LocalNavBridge to a dora node: dispatches
    cmd_request → cmd_response, relays goals/cancels/cmd_vels to dora-nav, feeds
    dora-nav state back in, and streams state + safety events."""

    def __init__(self, node: NavBaseNode, bridge: LocalNavBridge) -> None:
        self._node = node
        self._bridge = bridge
        self._started = False
        self._stop_event = threading.Event()
        self._workers: list[threading.Thread] = []

    # ---- request handling (pure: dict in, dict out) ----

    def handle_request(self, envelope: dict[str, Any]) -> dict[str, Any]:
        try:
            req = parse_cmd_request(envelope)
        except InvalidEnvelope as exc:
            return error_response_for_raw(envelope, "INVALID_PARAMS", str(exc))
        result = self._node.dispatch(req.verb, req.params)
        return build_cmd_response(
            req,
            ok=bool(result.get("ok", False)),
            code=str(result.get("code", "0")),
            data=result.get("data"),
            msg=str(result.get("msg", "")),
        )

    # ---- dora event loop ----

    def on_event(self, event: dict[str, Any], dora_node: DoraNodeLike) -> bool:
        """Process one dora event. Returns False when the loop should stop."""
        etype = event.get("type")
        if etype == "STOP":
            return False
        if etype != "INPUT":
            return True
        input_id = event.get("id")
        if input_id == "cmd_request":
            envelope = _decode_value(event.get("value"))
            if not isinstance(envelope, dict):
                return True
            target = envelope.get("target")
            if target is not None and target != self._node.robot_id:
                return True
            _emit(dora_node, "cmd_response", self.handle_request(envelope))
            self._flush_intents(dora_node)
        elif input_id == "dora_nav_pose":
            pose = _decode_value(event.get("value"))
            if isinstance(pose, dict):
                self._bridge.on_pose_update(pose)
        elif input_id == "dora_nav_status":
            status = _decode_value(event.get("value"))
            if isinstance(status, str):
                self._bridge.on_status_update(status)
        elif input_id == "dora_nav_obstacles":
            obstacles = _decode_value(event.get("value"))
            if isinstance(obstacles, list):
                self._bridge.on_obstacles_update(obstacles)
        return True

    def _flush_intents(self, dora_node: DoraNodeLike) -> None:
        """Publish queued goal/cancel/cmd_vel intents onto the dora-nav topics,
        in causal order."""
        for output_id, payload in self._bridge.drain_intents():
            _emit(dora_node, output_id, payload)

    # ---- streams (one-shot; exposed for deterministic testing) ----

    def publish_state_once(self, dora_node: DoraNodeLike) -> None:
        _emit(dora_node, "state", self._node.state_snapshot())
        for ev in self._node.drain_safety_events():
            _emit(dora_node, "safety_event", ev)

    def tick_watchdog_once(self, dora_node: DoraNodeLike) -> None:
        watchdog = getattr(self._node, "_watchdog", None)
        if watchdog is not None:
            watchdog.tick()
        # A fired deadman estops + queues a safe-stop (cancel + zero cmd_vel) and a
        # safety event; relay both promptly.
        self._flush_intents(dora_node)
        for ev in self._node.drain_safety_events():
            _emit(dora_node, "safety_event", ev)

    # ---- lifecycle ----

    def start(self, dora_node: DoraNodeLike) -> None:
        if self._started:
            return
        _emit(dora_node, "capabilities", self._node.capabilities_advert())
        self._stop_event.clear()
        self._workers = [
            threading.Thread(
                target=self._state_loop, args=(dora_node,),
                name="nav-base-state-loop", daemon=True,
            ),
            threading.Thread(
                target=self._watchdog_loop, args=(dora_node,),
                name="nav-base-watchdog-loop", daemon=True,
            ),
        ]
        for t in self._workers:
            t.start()
        self._started = True

    def stop(self) -> None:
        self._stop_event.set()
        for t in self._workers:
            t.join(timeout=2.0)
        self._workers = []
        self._started = False

    def _state_loop(self, dora_node: DoraNodeLike) -> None:
        while not self._stop_event.wait(STATE_PERIOD_S):
            try:
                self.publish_state_once(dora_node)
            except Exception:  # noqa: BLE001
                logger.exception("state loop iteration failed")

    def _watchdog_loop(self, dora_node: DoraNodeLike) -> None:
        while not self._stop_event.wait(WATCHDOG_PERIOD_S):
            try:
                self.tick_watchdog_once(dora_node)
            except Exception:  # noqa: BLE001
                logger.exception("watchdog loop iteration failed")


def build_node_from_env() -> tuple[NavBaseNode, LocalNavBridge]:
    """Construct + fully install a NavBaseNode (with a LocalNavBridge) from env."""
    robot_id = os.environ.get("ROBOT_ID")
    if not robot_id:
        raise SystemExit("ROBOT_ID env var is required")
    bridge = LocalNavBridge()
    node = NavBaseNode(
        robot_id=robot_id,
        waypoints_path=os.environ.get("WAYPOINTS_PATH", "load_path.yml"),
        heartbeat_timeout_ms=int(os.environ.get("HEARTBEAT_TIMEOUT_MS", "1000")),
        nav_bridge=bridge,
    )
    node.install_common_verbs()
    node.install_motion_verbs()
    node.install_localization_verbs()
    node.install_map_verbs()
    return node, bridge


def main() -> int:
    """Dora entry point. Imports dora lazily so Mode C / unit tests never need it."""
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    node, bridge = build_node_from_env()
    runtime = NavBaseRuntime(node, bridge)
    from dora import Node  # noqa: PLC0415 — lazy; needs a running dora daemon

    dora_node = Node()
    try:
        runtime.start(dora_node)
        for event in dora_node:
            if not runtime.on_event(event, dora_node):
                break
    finally:
        runtime.stop()
    return 0
