"""Conformance adapter tests."""
from nav_base_node.conformance_adapter import InProcessAdapter
from nav_base_node.node import NavBaseNode
from tests.fakes import FakeNavBridge


def test_adapter_routes_verb():
    node = NavBaseNode(robot_id="nav-base-test", nav_bridge=FakeNavBridge())
    node.install_common_verbs()
    adapter = InProcessAdapter(node)

    env = {"id": "x", "verb": "robot.heartbeat", "args": {}}
    resp = adapter.send(env)
    assert resp["ok"] is True


def test_adapter_returns_invalid_envelope_on_bad_input():
    node = NavBaseNode(robot_id="nav-base-test", nav_bridge=FakeNavBridge())
    node.install_common_verbs()
    adapter = InProcessAdapter(node)

    resp = adapter.send({"id": "x"})
    assert resp["ok"] is False
    assert resp["code"] == "INVALID_PARAMS"
