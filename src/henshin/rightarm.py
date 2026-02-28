"""Right-arm fitting logic extracted from the WebCam PoC.

This module keeps the math/state independent from rendering engines.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


@dataclass(slots=True)
class Vec2:
    x: float
    y: float

    def distance_to(self, other: "Vec2") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def add(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x + other.x, self.y + other.y)

    def sub(self, other: "Vec2") -> "Vec2":
        return Vec2(self.x - other.x, self.y - other.y)

    def mul(self, scalar: float) -> "Vec2":
        return Vec2(self.x * scalar, self.y * scalar)


@dataclass(slots=True)
class CoverScale:
    x: float = 1.0
    y: float = 1.0


@dataclass(slots=True)
class ArmTransform:
    position_x: float
    position_y: float
    position_z: float
    rotation_z: float
    scale_x: float
    scale_y: float
    scale_z: float


def norm_to_world(x01: float, y01: float, *, mirror: bool, cover_scale: CoverScale) -> Vec2:
    x_norm = (1 - x01) if mirror else x01
    x_ndc = x_norm * 2 - 1
    y_ndc = -(y01 * 2 - 1)
    return Vec2(x_ndc * cover_scale.x, y_ndc * cover_scale.y)


class DockCharger:
    """Ring docking logic used for equip trigger."""

    def __init__(
        self,
        *,
        center: Vec2,
        radius: float,
        hold_to_equip_sec: float = 0.7,
        decay_rate: float = 2.2,
    ) -> None:
        self.center = center
        self.radius = radius
        self.hold_to_equip_sec = hold_to_equip_sec
        self.decay_rate = decay_rate
        self.hold_sec = 0.0

    def contains(self, point: Vec2) -> bool:
        return point.distance_to(self.center) <= self.radius

    def tick(self, *, dt_sec: float, wrist: Vec2 | None, already_equipped: bool) -> bool:
        if already_equipped:
            self.hold_sec = 0.0
            return False

        if wrist is not None and self.contains(wrist):
            self.hold_sec += dt_sec
        else:
            self.hold_sec = max(0.0, self.hold_sec - dt_sec * self.decay_rate)

        ratio = clamp(self.hold_sec / self.hold_to_equip_sec, 0.0, 1.0)
        if ratio >= 1.0:
            self.hold_sec = 0.0
            return True
        return False


class ArmFollower:
    """Compute gauntlet transform from elbow->wrist segment."""

    def __init__(self) -> None:
        self._transform = ArmTransform(
            position_x=0.0,
            position_y=0.0,
            position_z=0.22,
            rotation_z=0.0,
            scale_x=1.0,
            scale_y=1.0,
            scale_z=1.0,
        )

    @property
    def transform(self) -> ArmTransform:
        return self._transform

    def set_dock_pose(self, center: Vec2) -> ArmTransform:
        self._transform = ArmTransform(
            position_x=center.x,
            position_y=center.y,
            position_z=0.22,
            rotation_z=0.0,
            scale_x=1.0,
            scale_y=1.0,
            scale_z=1.0,
        )
        return self._transform

    def follow_forearm(self, *, elbow: Vec2, wrist: Vec2, dt_sec: float) -> ArmTransform:
        direction = wrist.sub(elbow)
        length = math.hypot(direction.x, direction.y)
        midpoint = elbow.add(wrist).mul(0.5)

        angle = math.atan2(direction.y, direction.x)
        rotation_z = angle - math.pi / 2

        radius = clamp(length * 0.22, 0.08, 0.22)
        lerp = clamp(dt_sec * 18.0, 0.0, 1.0)

        prev = self._transform
        self._transform = ArmTransform(
            position_x=_lerp(prev.position_x, midpoint.x, lerp),
            position_y=_lerp(prev.position_y, midpoint.y, lerp),
            position_z=0.22,
            rotation_z=_lerp(prev.rotation_z, rotation_z, lerp),
            scale_x=_lerp(prev.scale_x, radius, lerp),
            scale_y=_lerp(prev.scale_y, length, lerp),
            scale_z=_lerp(prev.scale_z, radius, lerp),
        )
        return self._transform


@dataclass(slots=True)
class RightArmFrame:
    dt_sec: float
    right_elbow_xy01: tuple[float, float]
    right_wrist_xy01: tuple[float, float]


def run_rightarm_sequence(
    frames: Iterable[RightArmFrame],
    *,
    mirror: bool = True,
    cover_scale: CoverScale | None = None,
    dock_center: Vec2 | None = None,
    dock_radius: float = 0.18,
    hold_to_equip_sec: float = 0.7,
) -> dict:
    scale = cover_scale or CoverScale(1.0, 1.0)
    center = dock_center or Vec2(0.55, -0.25)
    dock = DockCharger(center=center, radius=dock_radius, hold_to_equip_sec=hold_to_equip_sec)
    follower = ArmFollower()
    follower.set_dock_pose(center)

    equipped = False
    equip_frame = -1
    output_frames = []

    for index, frame in enumerate(frames):
        elbow = norm_to_world(
            frame.right_elbow_xy01[0],
            frame.right_elbow_xy01[1],
            mirror=mirror,
            cover_scale=scale,
        )
        wrist = norm_to_world(
            frame.right_wrist_xy01[0],
            frame.right_wrist_xy01[1],
            mirror=mirror,
            cover_scale=scale,
        )

        equip_now = dock.tick(dt_sec=frame.dt_sec, wrist=wrist, already_equipped=equipped)
        if equip_now and not equipped:
            equipped = True
            equip_frame = index

        if equipped:
            follower.follow_forearm(elbow=elbow, wrist=wrist, dt_sec=frame.dt_sec)
        else:
            follower.set_dock_pose(center)

        t = follower.transform
        output_frames.append(
            {
                "index": index,
                "equipped": equipped,
                "hold_sec": round(dock.hold_sec, 4),
                "transform": {
                    "position_x": t.position_x,
                    "position_y": t.position_y,
                    "position_z": t.position_z,
                    "rotation_z": t.rotation_z,
                    "scale_x": t.scale_x,
                    "scale_y": t.scale_y,
                    "scale_z": t.scale_z,
                },
            }
        )

    return {
        "equipped": equipped,
        "equip_frame": equip_frame,
        "frames": output_frames,
    }


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t
