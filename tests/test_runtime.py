"""Runtime/event-loop tests driven by a fake dora node + the real LocalNavBridge."""
import json
import time

import pyarrow as pa

from nav_base_node.nav_bridge import LocalNavBridge
from nav_base_node.node import NavBaseNode
from nav_base_node.runtime import NavBaseRuntime


class FakeDoraNode:
    """Records send_output calls; decodes the pyarrow/JSON payloads."""

    def __init__(self) -> None:
        self.outputs: list[tuple[str, object]] = []

    def send_output(self, output_id: str, data) -> None:  # noqa: ANN001
        self.outputs.append((output_id, json.loads(data.to_pylist()[0])))

    def by_id(self, output_id: str) -> list:
        return [payload for (oid, payload) in self.outputs if oid == output_id]

    def ids_in_order(self) -> list[str]:
        return [oid for (oid, _payload) in self.outputs]


def _runtime() -> tuple[NavBaseRuntime, NavBaseNode, LocalNavBridge]:
    bridge = LocalNavBridge()
    node = NavBaseNode(robot_id="nav-base-001", nav_bridge=bridge)
    node.install_common_verbs()
    node.install_motion_verbs()
    node.install_localization_verbs()
    node.install_map_verbs()
    return NavBaseRuntime(node, bridge), node, bridge


def _cmd_request(envelope: dict) -> dict:
    return {"type": "INPUT", "id": "cmd_request", "value": pa.array([json.dumps(envelope)])}


def _input(input_id: str, payload) -> dict:
    return {"type": "INPUT", "id": input_id, "value": pa.array([json.dumps(payload)])}


def test_start_publishes_capabilities_advert_with_commands():
    rt, _, _ = _runtime()
    fake = FakeDoraNode()
    rt.start(fake)
    rt.stop()
    caps = fake.by_id("capabilities")
    assert len(caps) == 1
    verbs = {cmd["verb"] for cmd in caps[0]["commands"]}
    assert "vendor.dora_nav.base.go_to_pose" in verbs


def test_go_to_pose_responds_and_relays_goal_to_dora_nav():
    rt, _, _ = _runtime()
    fake = FakeDoraNode()
    pose = {"position": [1.0, 2.0, 0.0], "orientation": [0, 0, 0, 1]}
    env = {"verb": "vendor.dora_nav.base.go_to_pose", "params": {"pose": pose},
           "request_id": "r1", "target": "nav-base-001"}
    rt.on_event(_cmd_request(env), fake)
    assert fake.by_id("cmd_response")[0]["ok"] is True
    assert fake.by_id("dora_nav_goal") == [pose]


def test_set_velocity_relays_cancel_then_cmd_vel_in_order():
    rt, _, _ = _runtime()
    fake = FakeDoraNode()
    env = {"verb": "vendor.dora_nav.base.set_velocity",
           "params": {"linear": 0.3, "angular": 0.0}, "request_id": "r2",
           "target": "nav-base-001"}
    rt.on_event(_cmd_request(env), fake)
    ids = [i for i in fake.ids_in_order() if i.startswith("dora_nav_")]
    assert ids == ["dora_nav_cancel", "dora_nav_cmd_vel"]
    assert fake.by_id("dora_nav_cmd_vel") == [{"linear": 0.3, "angular": 0.0}]


def test_inbound_pose_feeds_get_pose_verb():
    rt, _, _ = _runtime()
    fake = FakeDoraNode()
    rt.on_event(_input("dora_nav_pose", {"x": 1.0, "y": 2.0, "theta": 0.5}), fake)
    env = {"verb": "vendor.dora_nav.localization.get_pose", "params": {},
           "request_id": "r3", "target": "nav-base-001"}
    rt.on_event(_cmd_request(env), fake)
    resp = fake.by_id("cmd_response")[0]
    assert resp["ok"] is True
    assert resp["data"]["pose"] == {"x": 1.0, "y": 2.0, "theta": 0.5}


def test_inbound_status_reflected_in_state():
    rt, _, _ = _runtime()
    fake = FakeDoraNode()
    rt.on_event(_input("dora_nav_status", "following"), fake)
    rt.publish_state_once(fake)
    assert fake.by_id("state")[0]["nav_status"] == "following"


def test_on_event_drops_foreign_target():
    rt, _, _ = _runtime()
    fake = FakeDoraNode()
    env = {"verb": "robot.heartbeat", "params": {}, "request_id": "r", "target": "other"}
    rt.on_event(_cmd_request(env), fake)
    assert fake.by_id("cmd_response") == []


def test_on_event_malformed_json_does_not_crash():
    rt, _, _ = _runtime()
    fake = FakeDoraNode()
    ev = {"type": "INPUT", "id": "cmd_request", "value": pa.array(["{nope"])}
    assert rt.on_event(ev, fake) is True
    assert fake.by_id("cmd_response") == []


def test_on_event_stop_returns_false():
    rt, _, _ = _runtime()
    assert rt.on_event({"type": "STOP"}, FakeDoraNode()) is False


def test_estop_relays_safe_stop_to_dora_nav():
    rt, node, _ = _runtime()
    fake = FakeDoraNode()
    env = {"verb": "robot.estop", "params": {"reason": "manual"}, "request_id": "e1",
           "target": "nav-base-001"}
    rt.on_event(_cmd_request(env), fake)
    # estop cancels the goal and commands zero velocity on the dora-nav topics.
    assert "dora_nav_cancel" in fake.ids_in_order()
    assert {"linear": 0.0, "angular": 0.0} in fake.by_id("dora_nav_cmd_vel")


def test_watchdog_deadman_estops_and_relays_safe_stop():
    bridge = LocalNavBridge()
    node = NavBaseNode(robot_id="nav-base-001", nav_bridge=bridge, heartbeat_timeout_ms=20)
    node.install_common_verbs()
    node.install_motion_verbs()
    rt = NavBaseRuntime(node, bridge)
    fake = FakeDoraNode()
    node.dispatch(
        "vendor.dora_nav.base.go_to_pose",
        {"pose": {"position": [1.0, 0.0, 0.0], "orientation": [0, 0, 0, 1]},
         "control_source": "c"},
    )
    bridge.drain_intents()  # discard the goal queued above
    time.sleep(0.05)
    rt.tick_watchdog_once(fake)
    assert node.is_estopped is True
    assert {"linear": 0.0, "angular": 0.0} in fake.by_id("dora_nav_cmd_vel")
    assert any(e["kind"] == "heartbeat_timeout" for e in fake.by_id("safety_event"))


def test_publish_state_once_emits_snapshot():
    rt, _, _ = _runtime()
    fake = FakeDoraNode()
    rt.publish_state_once(fake)
    states = fake.by_id("state")
    assert len(states) == 1
    assert states[0]["robot_id"] == "nav-base-001"
