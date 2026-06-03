#!/usr/bin/env python3
"""Mode B driver — emits one robot.heartbeat envelope per 2 s tick."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import pyarrow as pa
from dora import Node


def main() -> None:
    node = Node()
    for event in node:
        if event["type"] != "INPUT":
            continue
        env = {
            "id": str(uuid.uuid4()),
            "verb": "robot.heartbeat",
            "args": {},
            "target": "nav-base-demo",
            "source": "cmd_driver",
            "ts": datetime.now(timezone.utc).isoformat(),
        }
        node.send_output("cmd_request", pa.array([json.dumps(env)]))


if __name__ == "__main__":
    main()
