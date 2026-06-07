from nav_base_node.node import NavBaseNode
from tests.fakes import FakeNavBridge


def _full_node():
    b = FakeNavBridge()
    n = NavBaseNode(robot_id="nav-base-test", nav_bridge=b)
    n.install_common_verbs()
    n.install_motion_verbs()
    n.install_localization_verbs()
    n.install_map_verbs()
    return n, b


def test_state_snapshot_has_required_fields():
    n, b = _full_node()
    b.on_pose_update({"x": 1.0, "y": 2.0, "theta": 0.0})
    b.on_status_update("following")
    snap = n.state_snapshot()
    assert snap["robot_id"] == "nav-base-test"
    assert snap["pose"] == {"x": 1.0, "y": 2.0, "theta": 0.0}
    assert snap["nav_status"] == "following"
    assert snap["estopped"] is False
    assert "obstacles_count" in snap


def test_state_snapshot_reflects_estop():
    n, _ = _full_node()
    n.dispatch("robot.estop", {"reason": "test"})
    snap = n.state_snapshot()
    assert snap["estopped"] is True
    assert snap["estop_reason"] == "test"


def test_state_snapshot_has_monotonic_seq():
    n, _ = _full_node()
    assert n.state_snapshot()["seq"] == 1
    assert n.state_snapshot()["seq"] == 2


def test_state_snapshot_has_seq_without_bridge():
    n = NavBaseNode(robot_id="nav-base-test")
    n.install_common_verbs()
    assert n.state_snapshot()["seq"] == 1
