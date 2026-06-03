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
