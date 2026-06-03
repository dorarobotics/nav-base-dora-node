"""Mode C client library tests."""
from nav_base_node.client import NavBaseClient, NavConfig
from nav_base_node.client.types import Pose2D
from nav_base_node.client.state import NavState


def test_pose2d_round_trip():
    p = Pose2D(x=1.0, y=2.0, theta=0.5)
    d = p.to_dict()
    assert d == {"x": 1.0, "y": 2.0, "theta": 0.5}
    assert Pose2D.from_dict(d) == p


def test_navstate_from_snapshot():
    snap = {
        "robot_id": "nav-base-test",
        "pose": {"x": 1.0, "y": 2.0, "theta": 0.0},
        "nav_status": "following",
        "obstacles_count": 0,
        "estopped": False,
        "estop_reason": None,
        "controller_holder": None,
    }
    s = NavState.from_snapshot(snap)
    assert s.robot_id == "nav-base-test"
    assert s.nav_status == "following"


def test_client_constructs_from_config():
    cfg = NavConfig(robot_id="nav-base-001")
    client = NavBaseClient(config=cfg)
    assert client.config.robot_id == "nav-base-001"
