"""Conformance-suite adapter for NavBaseNode.

Test/conformance-only — not a runtime dependency.
"""
from __future__ import annotations

from typing import Any

from nav_base_node._envelope import (
    InvalidEnvelope,
    build_cmd_response,
    parse_cmd_request,
)
from nav_base_node.node import NavBaseNode


class InProcessAdapter:
    def __init__(self, node: NavBaseNode) -> None:
        self._node = node

    def send(self, envelope: dict[str, Any]) -> dict[str, Any]:
        try:
            req = parse_cmd_request(envelope)
        except InvalidEnvelope as e:
            return build_cmd_response(
                request_id=str(envelope.get("id", "")),
                ok=False, code="INVALID_PARAMS", msg=str(e),
            )
        out = self._node.dispatch(req.verb, req.args)
        return build_cmd_response(
            request_id=req.id,
            ok=bool(out.get("ok")),
            code=str(out.get("code", "0")),
            data=out.get("data"),
            msg=out.get("msg"),
        )
