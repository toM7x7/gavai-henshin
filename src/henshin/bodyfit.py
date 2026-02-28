"""Full-body fitting and equip simulation.

Generalized from right-arm PoC so any segment can be tracked by joint pairs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


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
class SegmentSpec:
    name: str
    start_joint: str
    end_joint: str
    radius_factor: float = 0.22
    radius_min: float = 0.05
    radius_max: float = 0.22
    z: float = 0.22
    smooth_gain: float = 18.0
    dock_offset_x: float = 0.0
    dock_offset_y: float = 0.0


@dataclass(slots=True)
class SegmentTransform:
    position_x: float
    position_y: float
    position_z: float
    rotation_z: float
    scale_x: float
    scale_y: float
    scale_z: float


@dataclass(slots=True)
class BodyFrame:
    dt_sec: float
    joints_xy01: dict[str, tuple[float, float]]


class DockCharger:
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

    def tick(self, *, dt_sec: float, trigger_point: Vec2 | None, already_equipped: bool) -> bool:
        if already_equipped:
            self.hold_sec = 0.0
            return False

        if trigger_point is not None and self.contains(trigger_point):
            self.hold_sec += dt_sec
        else:
            self.hold_sec = max(0.0, self.hold_sec - dt_sec * self.decay_rate)

        ratio = clamp(self.hold_sec / self.hold_to_equip_sec, 0.0, 1.0)
        if ratio >= 1.0:
            self.hold_sec = 0.0
            return True
        return False


class SegmentFollower:
    def __init__(self, spec: SegmentSpec) -> None:
        self.spec = spec
        self._transform = SegmentTransform(
            position_x=0.0,
            position_y=0.0,
            position_z=spec.z,
            rotation_z=0.0,
            scale_x=1.0,
            scale_y=1.0,
            scale_z=1.0,
        )

    @property
    def transform(self) -> SegmentTransform:
        return self._transform

    def set_dock_pose(self, dock_center: Vec2) -> SegmentTransform:
        self._transform = SegmentTransform(
            position_x=dock_center.x + self.spec.dock_offset_x,
            position_y=dock_center.y + self.spec.dock_offset_y,
            position_z=self.spec.z,
            rotation_z=0.0,
            scale_x=1.0,
            scale_y=1.0,
            scale_z=1.0,
        )
        return self._transform

    def follow(self, *, start: Vec2, end: Vec2, dt_sec: float) -> SegmentTransform:
        direction = end.sub(start)
        length = math.hypot(direction.x, direction.y)
        midpoint = start.add(end).mul(0.5)

        angle = math.atan2(direction.y, direction.x)
        rotation_z = angle - math.pi / 2
        radius = clamp(length * self.spec.radius_factor, self.spec.radius_min, self.spec.radius_max)
        lerp = clamp(dt_sec * self.spec.smooth_gain, 0.0, 1.0)

        prev = self._transform
        self._transform = SegmentTransform(
            position_x=_lerp(prev.position_x, midpoint.x, lerp),
            position_y=_lerp(prev.position_y, midpoint.y, lerp),
            position_z=self.spec.z,
            rotation_z=_lerp(prev.rotation_z, rotation_z, lerp),
            scale_x=_lerp(prev.scale_x, radius, lerp),
            scale_y=_lerp(prev.scale_y, length, lerp),
            scale_z=_lerp(prev.scale_z, radius, lerp),
        )
        return self._transform


def norm_to_world(x01: float, y01: float, *, mirror: bool, cover_scale: CoverScale) -> Vec2:
    x_norm = (1 - x01) if mirror else x01
    x_ndc = x_norm * 2 - 1
    y_ndc = -(y01 * 2 - 1)
    return Vec2(x_ndc * cover_scale.x, y_ndc * cover_scale.y)


DEFAULT_SEGMENT_SPECS: list[SegmentSpec] = [
    SegmentSpec("right_upperarm", "right_shoulder", "right_elbow", dock_offset_x=0.28, dock_offset_y=0.05),
    SegmentSpec("right_forearm", "right_elbow", "right_wrist", dock_offset_x=0.28, dock_offset_y=-0.02),
    SegmentSpec("left_upperarm", "left_shoulder", "left_elbow", dock_offset_x=-0.28, dock_offset_y=0.05),
    SegmentSpec("left_forearm", "left_elbow", "left_wrist", dock_offset_x=-0.28, dock_offset_y=-0.02),
    SegmentSpec("right_thigh", "right_hip", "right_knee", dock_offset_x=0.12, dock_offset_y=-0.34),
    SegmentSpec("right_shin", "right_knee", "right_ankle", dock_offset_x=0.12, dock_offset_y=-0.56),
    SegmentSpec("left_thigh", "left_hip", "left_knee", dock_offset_x=-0.12, dock_offset_y=-0.34),
    SegmentSpec("left_shin", "left_knee", "left_ankle", dock_offset_x=-0.12, dock_offset_y=-0.56),
    SegmentSpec("chest_core", "left_shoulder", "right_hip", radius_factor=0.38, radius_max=0.35),
]


def run_body_sequence(
    frames: Iterable[BodyFrame],
    *,
    mirror: bool = True,
    cover_scale: CoverScale | None = None,
    dock_center: Vec2 | None = None,
    dock_radius: float = 0.18,
    hold_to_equip_sec: float = 0.7,
    trigger_joint: str = "right_wrist",
    segment_specs: list[SegmentSpec] | None = None,
) -> dict:
    scale = cover_scale or CoverScale(1.0, 1.0)
    center = dock_center or Vec2(0.55, -0.25)
    specs = segment_specs or DEFAULT_SEGMENT_SPECS

    dock = DockCharger(center=center, radius=dock_radius, hold_to_equip_sec=hold_to_equip_sec)
    followers = {spec.name: SegmentFollower(spec) for spec in specs}
    for follower in followers.values():
        follower.set_dock_pose(center)

    equipped = False
    equip_frame = -1
    output_frames = []

    for index, frame in enumerate(frames):
        joints_world: dict[str, Vec2] = {}
        for joint_name, xy in frame.joints_xy01.items():
            joints_world[joint_name] = norm_to_world(
                float(xy[0]),
                float(xy[1]),
                mirror=mirror,
                cover_scale=scale,
            )

        trigger_point = joints_world.get(trigger_joint)
        equip_now = dock.tick(dt_sec=frame.dt_sec, trigger_point=trigger_point, already_equipped=equipped)
        if equip_now and not equipped:
            equipped = True
            equip_frame = index

        segment_data: dict[str, dict[str, float]] = {}
        for spec in specs:
            follower = followers[spec.name]
            start = joints_world.get(spec.start_joint)
            end = joints_world.get(spec.end_joint)

            if equipped and start is not None and end is not None:
                t = follower.follow(start=start, end=end, dt_sec=frame.dt_sec)
            else:
                t = follower.set_dock_pose(center)

            segment_data[spec.name] = {
                "position_x": t.position_x,
                "position_y": t.position_y,
                "position_z": t.position_z,
                "rotation_z": t.rotation_z,
                "scale_x": t.scale_x,
                "scale_y": t.scale_y,
                "scale_z": t.scale_z,
            }

        output_frames.append(
            {
                "index": index,
                "equipped": equipped,
                "hold_sec": round(dock.hold_sec, 4),
                "segments": segment_data,
            }
        )

    return {
        "equipped": equipped,
        "equip_frame": equip_frame,
        "trigger_joint": trigger_joint,
        "segments": [spec.name for spec in specs],
        "frames": output_frames,
    }
