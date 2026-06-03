from nav_base_node.node import NavBaseNode


def test_heartbeat_verb_returns_ok():
    node = NavBaseNode(robot_id="nav-base-test", heartbeat_timeout_ms=1000)
    node.install_common_verbs()
    out = node.dispatch("robot.heartbeat", {})
    assert out == {"ok": True, "code": "0"}


def test_heartbeat_when_watchdog_disabled_still_ok():
    node = NavBaseNode(robot_id="nav-base-test", heartbeat_timeout_ms=0)
    node.install_common_verbs()
    out = node.dispatch("robot.heartbeat", {})
    assert out["ok"] is True
