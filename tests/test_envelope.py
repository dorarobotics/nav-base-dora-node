from nav_base_node._envelope import (
    build_cmd_response,
    parse_cmd_request,
    InvalidEnvelope,
)


def test_parse_cmd_request_extracts_fields():
    env = {
        "id": "abc-123",
        "verb": "robot.heartbeat",
        "args": {},
        "target": "nav-base-001",
        "source": "test-suite",
    }
    parsed = parse_cmd_request(env)
    assert parsed.id == "abc-123"
    assert parsed.verb == "robot.heartbeat"
    assert parsed.args == {}


def test_parse_cmd_request_rejects_missing_verb():
    try:
        parse_cmd_request({"id": "x", "args": {}})
    except InvalidEnvelope as e:
        assert "verb" in str(e)
    else:
        raise AssertionError("expected InvalidEnvelope")


def test_build_cmd_response_ok():
    out = build_cmd_response(request_id="abc", ok=True, code="0", data={"x": 1})
    assert out["ok"] is True
    assert out["data"] == {"x": 1}


def test_build_cmd_response_error():
    out = build_cmd_response(request_id="abc", ok=False, code="VENDOR_ERROR", msg="boom")
    assert out["msg"] == "boom"
