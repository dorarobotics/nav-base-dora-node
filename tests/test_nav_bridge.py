from tests.fakes import FakeNavBridge


def test_fake_queues_a_goal():
    b = FakeNavBridge()
    b.request_goal({"position": [1.0, 2.0, 0.0], "orientation": [0, 0, 0, 1]})
    assert b.pending_goals == [{"position": [1.0, 2.0, 0.0], "orientation": [0, 0, 0, 1]}]


def test_fake_queues_a_cancel():
    b = FakeNavBridge()
    b.cancel()
    assert b.pending_cancels == 1


def test_fake_queues_a_cmd_vel():
    b = FakeNavBridge()
    b.request_cmd_vel({"linear": 0.2, "angular": 0.0})
    assert b.pending_cmd_vels == [{"linear": 0.2, "angular": 0.0}]


def test_fake_reports_latest_pose():
    b = FakeNavBridge()
    b.on_pose_update({"x": 1.0, "y": 2.0, "theta": 0.5})
    assert b.latest_pose() == {"x": 1.0, "y": 2.0, "theta": 0.5}


def test_fake_status_tracking():
    b = FakeNavBridge()
    b.on_status_update("planning")
    b.on_status_update("following")
    b.on_status_update("arrived")
    assert b.status_history == ["planning", "following", "arrived"]
    assert b.current_status() == "arrived"


def test_fake_obstacles_update():
    b = FakeNavBridge()
    obs = [{"id": 1, "pose": {"x": 1.0, "y": 0.0}}]
    b.on_obstacles_update(obs)
    assert b.latest_obstacles() == obs
