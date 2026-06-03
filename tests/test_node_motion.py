from nav_base_node.node import NavBaseNode
from tests.fakes import FakeNavBridge


def _node():
    b = FakeNavBridge()
    n = NavBaseNode(robot_id="nav-base-test", nav_bridge=b)
    n.install_common_verbs()
    n.install_motion_verbs()
    return n, b


def test_go_to_pose_queues_goal():
    n, b = _node()
    pose = {"position": [1.0, 2.0, 0.0], "orientation": [0, 0, 0, 1]}
    out = n.dispatch(
        "vendor.dora_nav.base.go_to_pose",
        {"pose": pose, "control_source": "test"},
    )
    assert out["ok"] is True
    assert b.pending_goals == [pose]


def test_go_to_pose_rejects_malformed_pose():
    n, _ = _node()
    out = n.dispatch(
        "vendor.dora_nav.base.go_to_pose",
        {"pose": {"position": [1.0]}, "control_source": "test"},
    )
    assert out["ok"] is False
    assert out["code"] == "INVALID_PARAMS"


def test_go_to_pose_blocked_by_estop():
    n, _ = _node()
    n.dispatch("robot.estop", {"reason": "test"})
    pose = {"position": [1.0, 2.0, 0.0], "orientation": [0, 0, 0, 1]}
    out = n.dispatch(
        "vendor.dora_nav.base.go_to_pose",
        {"pose": pose, "control_source": "test"},
    )
    assert out["ok"] is False
    assert out["code"] == "VENDOR_ERROR"


def test_go_to_pose_acquires_motion_lock():
    n, _ = _node()
    n._guard.acquire("other")
    pose = {"position": [1.0, 2.0, 0.0], "orientation": [0, 0, 0, 1]}
    out = n.dispatch(
        "vendor.dora_nav.base.go_to_pose",
        {"pose": pose, "control_source": "me"},
    )
    assert out["ok"] is False
    assert out["code"] == "CONTROLLER_BUSY"


def test_go_to_named_queues_resolved_pose(tmp_path):
    yml = tmp_path / "wp.yaml"
    yml.write_text(
        "home:\n  position: [0.0, 0.0, 0.0]\n  orientation: [0.0, 0.0, 0.0, 1.0]\n"
    )
    b = FakeNavBridge()
    n = NavBaseNode(
        robot_id="nav-base-test", nav_bridge=b, waypoints_path=str(yml)
    )
    n.install_common_verbs()
    n.install_motion_verbs()
    out = n.dispatch(
        "vendor.dora_nav.base.go_to_named",
        {"name": "home", "control_source": "test"},
    )
    assert out["ok"] is True
    assert b.pending_goals[0]["position"] == [0.0, 0.0, 0.0]


def test_go_to_named_rejects_unknown_name(tmp_path):
    yml = tmp_path / "wp.yaml"
    yml.write_text(
        "home:\n  position: [0,0,0]\n  orientation: [0,0,0,1]\n"
    )
    b = FakeNavBridge()
    n = NavBaseNode(
        robot_id="nav-base-test", nav_bridge=b, waypoints_path=str(yml)
    )
    n.install_common_verbs()
    n.install_motion_verbs()
    out = n.dispatch(
        "vendor.dora_nav.base.go_to_named",
        {"name": "attic", "control_source": "test"},
    )
    assert out["ok"] is False
    assert out["code"] == "INVALID_PARAMS"


def test_set_velocity_cancels_then_queues_cmd_vel():
    n, b = _node()
    out = n.dispatch(
        "vendor.dora_nav.base.set_velocity",
        {"linear": 0.3, "angular": 0.0, "control_source": "test"},
    )
    assert out["ok"] is True
    assert b.pending_cancels == 1
    assert b.pending_cmd_vels == [{"linear": 0.3, "angular": 0.0}]


def test_set_velocity_blocked_by_estop():
    n, _ = _node()
    n.dispatch("robot.estop", {"reason": "test"})
    out = n.dispatch(
        "vendor.dora_nav.base.set_velocity",
        {"linear": 0.3, "angular": 0.0, "control_source": "test"},
    )
    assert out["ok"] is False
    assert out["code"] == "VENDOR_ERROR"
