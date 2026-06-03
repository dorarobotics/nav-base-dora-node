"""Lifecycle invariants — clean construction, registration ordering, estop latching."""
from nav_base_node.node import NavBaseNode
from tests.fakes import FakeNavBridge


def test_node_starts_with_no_verbs():
    n = NavBaseNode(robot_id="nav-base-test")
    out = n.dispatch("robot.heartbeat", {})
    assert out["ok"] is False
    assert out["code"] == "INVALID_PARAMS"


def test_install_common_verbs_idempotent_double_call_raises():
    n = NavBaseNode(robot_id="nav-base-test")
    n.install_common_verbs()
    try:
        n.install_common_verbs()
    except ValueError as e:
        assert "already registered" in str(e)
    else:
        raise AssertionError("expected ValueError on duplicate registration")


def test_full_install_sequence():
    n = NavBaseNode(robot_id="nav-base-test", nav_bridge=FakeNavBridge())
    n.install_common_verbs()
    n.install_motion_verbs()
    n.install_localization_verbs()
    n.install_map_verbs()
    caps = n.dispatch("robot.get_capabilities", {})
    verbs = {cmd["verb"] for cmd in caps["data"]["commands"]}
    expected = {
        "robot.heartbeat", "robot.estop", "robot.release_control",
        "robot.get_capabilities",
        "vendor.dora_nav.base.go_to_pose",
        "vendor.dora_nav.base.go_to_named",
        "vendor.dora_nav.base.set_velocity",
        "vendor.dora_nav.base.stop",
        "vendor.dora_nav.localization.get_pose",
        "vendor.dora_nav.map.get_obstacles",
    }
    assert expected.issubset(verbs)
