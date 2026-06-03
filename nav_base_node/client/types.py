"""Typed payloads for Mode C."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Pose2D:
    x: float
    y: float
    theta: float   # yaw in radians

    def to_dict(self) -> dict[str, float]:
        return {"x": self.x, "y": self.y, "theta": self.theta}

    @classmethod
    def from_dict(cls, d: dict[str, float]) -> "Pose2D":
        return cls(x=float(d["x"]), y=float(d["y"]), theta=float(d["theta"]))
