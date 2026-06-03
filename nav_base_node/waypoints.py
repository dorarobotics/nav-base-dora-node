"""Waypoints loader — reads a YAML file of named poses (matches dora-nav's load_path.yml)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    import yaml  # type: ignore[import-untyped]
except ImportError as e:
    raise ImportError("PyYAML is required: pip install pyyaml") from e


@dataclass(frozen=True)
class Waypoints:
    _data: dict[str, dict[str, Any]]

    def names(self) -> list[str]:
        return sorted(self._data.keys())

    def lookup(self, name: str) -> dict[str, Any]:
        if name not in self._data:
            raise KeyError(f"unknown waypoint: {name}")
        return dict(self._data[name])


def load_waypoints(path: str) -> Waypoints:
    with open(path) as f:
        raw = yaml.safe_load(f) or {}
    return Waypoints(_data=raw)
