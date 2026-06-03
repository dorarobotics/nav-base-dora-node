from nav_base_node.node import NavBaseNode
from tests.fakes import FakeNavBridge


def _node():
    b = FakeNavBridge()
    n = NavBaseNode(robot_id="nav-base-test", nav_bridge=b)
    n.install_common_verbs()
    n.install_map_verbs()
    return n, b


def test_get_obstacles_returns_latest_list():
    n, b = _node()
    obs = [{"id": 1, "pose": {"x": 1.0, "y": 0.0}}]
    b.on_obstacles_update(obs)
    out = n.dispatch("vendor.dora_nav.map.get_obstacles", {})
    assert out["ok"] is True
    assert out["data"]["obstacles"] == obs


def test_get_obstacles_empty_when_no_update():
    n, _ = _node()
    out = n.dispatch("vendor.dora_nav.map.get_obstacles", {})
    assert out["ok"] is True
    assert out["data"]["obstacles"] == []
