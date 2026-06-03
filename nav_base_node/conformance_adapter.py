"""Conformance-suite adapter for NavBaseNode.

Drives the node through the SAME request-handling path as the live dora runtime
(`NavBaseRuntime.handle_request`), so conformance tests exercise the real
cmd_request → cmd_response contract — just without a dora process in the loop.

Test/conformance-only — not a runtime dependency.
"""
from __future__ import annotations

from typing import Any

from nav_base_node.nav_bridge import LocalNavBridge
from nav_base_node.node import NavBaseNode
from nav_base_node.runtime import NavBaseRuntime


class InProcessAdapter:
    """Send SPEC-V1 cmd_request envelopes to a NavBaseNode without dora."""

    def __init__(self, node: NavBaseNode) -> None:
        # handle_request only calls node.dispatch; the runtime's own bridge is
        # unused on this path, so a fresh LocalNavBridge is fine here.
        self._runtime = NavBaseRuntime(node, LocalNavBridge())

    def send(self, envelope: dict[str, Any]) -> dict[str, Any]:
        return self._runtime.handle_request(envelope)
