"""Conformance adapter tests against the real wire contract."""
from nav_base_node.conformance_adapter import InProcessAdapter
from nav_base_node.node import NavBaseNode
from tests.fakes import FakeNavBridge


def _adapter() -> InProcessAdapter:
    node = NavBaseNode(robot_id="nav-base-test", nav_bridge=FakeNavBridge())
    node.install_common_verbs()
    return InProcessAdapter(node)


def test_adapter_routes_verb_and_echoes_request_id():
    adapter = _adapter()
    env = {"verb": "robot.heartbeat", "params": {}, "request_id": "abc-123",
           "target": "nav-base-test"}
    resp = adapter.send(env)
    assert resp["ok"] is True
    assert resp["request_id"] == "abc-123"
    assert resp["code"] == "0"


def test_adapter_returns_invalid_envelope_on_missing_verb():
    adapter = _adapter()
    resp = adapter.send({"request_id": "x"})
    assert resp["ok"] is False
    assert resp["code"] == "INVALID_PARAMS"
    assert resp["request_id"] == "x"
