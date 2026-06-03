from nav_base_node.node import NavBaseNode
from tests.fakes import FakeNavBridge


def _node():
    b = FakeNavBridge()
    n = NavBaseNode(robot_id="nav-base-test", nav_bridge=b)
    n.install_common_verbs()
    n.install_localization_verbs()
    return n, b


def test_get_pose_returns_latest():
    n, b = _node()
    b.on_pose_update({"x": 1.0, "y": 2.0, "theta": 0.5})
    out = n.dispatch("vendor.dora_nav.localization.get_pose", {})
    assert out["ok"] is True
    assert out["data"]["pose"] == {"x": 1.0, "y": 2.0, "theta": 0.5}


def test_get_pose_when_not_yet_received():
    n, _ = _node()
    out = n.dispatch("vendor.dora_nav.localization.get_pose", {})
    assert out["ok"] is False
    assert out["code"] == "VENDOR_ERROR"
    assert "no pose" in out["msg"].lower()
