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


def test_estop_records_state_and_returns_ok():
    node = NavBaseNode(robot_id="nav-base-test")
    node.install_common_verbs()
    out = node.dispatch("robot.estop", {"reason": "manual"})
    assert out["ok"] is True
    assert node.is_estopped is True
    assert node.estop_reason == "manual"


def test_estop_reason_defaults_to_unspecified():
    node = NavBaseNode(robot_id="nav-base-test")
    node.install_common_verbs()
    out = node.dispatch("robot.estop", {})
    assert out["ok"] is True
    assert node.estop_reason == "unspecified"


def test_release_control_frees_motion_lock():
    node = NavBaseNode(robot_id="nav-base-test")
    node.install_common_verbs()
    node._guard.acquire("caller-a")
    out = node.dispatch("robot.release_control", {"control_source": "caller-a"})
    assert out["ok"] is True
    assert node._guard.holder is None


def test_release_control_by_non_holder_is_ok_but_noop():
    node = NavBaseNode(robot_id="nav-base-test")
    node.install_common_verbs()
    node._guard.acquire("caller-a")
    out = node.dispatch("robot.release_control", {"control_source": "stranger"})
    assert out["ok"] is True
    assert node._guard.holder == "caller-a"


def test_get_capabilities_returns_spec_advert_shape():
    node = NavBaseNode(robot_id="nav-base-test")
    node.install_common_verbs()
    out = node.dispatch("robot.get_capabilities", {})
    assert out["ok"] is True
    data = out["data"]
    assert data["spec_version"] == "1.0.0"
    assert data["vendor"] == "dora_nav"
    assert data["model"] == "base"
    # The bridge consumes advert["commands"][*]["verb"] — a flat verb list is not
    # recognized. Each command must carry a verb and a safety_tier.
    verbs = {cmd["verb"] for cmd in data["commands"]}
    assert "robot.heartbeat" in verbs
    assert all("safety_tier" in cmd for cmd in data["commands"])
    assert "state" in data["streams"]


def test_dispatch_bad_args_returns_invalid_params():
    node = NavBaseNode(robot_id="nav-base-test")
    node.install_common_verbs()
    out = node.dispatch("robot.estop", {"bogus": 1})
    assert out["ok"] is False
    assert out["code"] == "INVALID_PARAMS"
