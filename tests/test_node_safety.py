import time

from nav_base_node.node import NavBaseNode
from tests.fakes import FakeNavBridge


def _node():
    n = NavBaseNode(robot_id="nav-base-test", nav_bridge=FakeNavBridge())
    n.install_common_verbs()
    return n


def test_estop_emits_safety_event():
    n = _node()
    n.dispatch("robot.estop", {"reason": "test"})
    events = n.drain_safety_events()
    assert len(events) == 1
    assert events[0]["kind"] == "estop"


def test_drain_clears_queue():
    n = _node()
    n.dispatch("robot.estop", {"reason": "x"})
    _ = n.drain_safety_events()
    assert n.drain_safety_events() == []


def test_heartbeat_timeout_emits_safety_event():
    n = NavBaseNode(
        robot_id="nav-base-test", nav_bridge=FakeNavBridge(), heartbeat_timeout_ms=10
    )
    n.install_common_verbs()
    n._on_heartbeat_timeout(0.0)
    events = n.drain_safety_events()
    assert len(events) == 1
    assert events[0]["kind"] == "heartbeat_timeout"


def test_estop_actively_stops_the_base():
    """estop must not just latch — it cancels the goal and commands zero velocity."""
    b = FakeNavBridge()
    n = NavBaseNode(robot_id="nav-base-test", nav_bridge=b)
    n.install_common_verbs()
    n.install_motion_verbs()
    # Base is moving toward a goal.
    n.dispatch(
        "vendor.dora_nav.base.go_to_pose",
        {"pose": {"position": [1.0, 0.0, 0.0], "orientation": [0, 0, 0, 1]},
         "control_source": "c"},
    )
    n.dispatch("robot.estop", {"reason": "manual"})
    assert b.pending_cancels >= 1
    assert {"linear": 0.0, "angular": 0.0} in b.pending_cmd_vels


def test_watchdog_deadman_engages_estop_and_stops_base():
    b = FakeNavBridge()
    n = NavBaseNode(robot_id="nav-base-test", nav_bridge=b, heartbeat_timeout_ms=20)
    n.install_common_verbs()
    n.install_motion_verbs()
    # Commanding motion arms the watchdog.
    n.dispatch(
        "vendor.dora_nav.base.go_to_pose",
        {"pose": {"position": [1.0, 0.0, 0.0], "orientation": [0, 0, 0, 1]},
         "control_source": "c"},
    )
    time.sleep(0.05)
    n._watchdog.tick()  # the dora loop will call this periodically (node runtime — pending)
    assert n.is_estopped is True
    assert n.estop_reason == "heartbeat_timeout"
    assert {"linear": 0.0, "angular": 0.0} in b.pending_cmd_vels
    assert any(e["kind"] == "heartbeat_timeout" for e in n.drain_safety_events())
