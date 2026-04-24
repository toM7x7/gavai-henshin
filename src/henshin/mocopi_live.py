"""Live mocopi frame buffer for the Quest henshin bridge."""

from __future__ import annotations

import math
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Any

from .bodyfit import BodyFrame
from .iw_henshin import normalize_mocopi_frames


@dataclass(slots=True)
class LiveMocopiRecord:
    index: int
    received_at: float
    frame: BodyFrame
    source: str = "mocopi-live"

    def as_frame_payload(self) -> dict[str, Any]:
        return {
            "dt_sec": self.frame.dt_sec,
            "joints": {name: [xy[0], xy[1]] for name, xy in self.frame.joints_xy01.items()},
        }


class MocopiBridgeStatus:
    def __init__(self, *, stale_after_sec: float = 3.0) -> None:
        self.stale_after_sec = stale_after_sec
        self._lock = threading.Lock()
        self._payload: dict[str, Any] | None = None
        self._updated_at: float | None = None
        self._last_packet_at: float | None = None

    def update(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = time.time()
        normalized = {
            "ok": bool(payload.get("ok", True)),
            "event": str(payload.get("event") or "status"),
            "listening": payload.get("listening"),
            "received": int(payload.get("received") or 0),
            "forwarded_frames": int(payload.get("forwarded_frames") or 0),
            "unsupported": int(payload.get("unsupported") or 0),
            "last_source": payload.get("last_source") or payload.get("source"),
            "last_error": payload.get("last_error") or payload.get("error"),
            "last_packet_bytes": payload.get("last_packet_bytes"),
            "input_format": payload.get("input_format"),
            "dry_run": bool(payload.get("dry_run", False)),
        }
        if payload.get("packet_seen") or normalized["event"] in {"accepted", "unsupported", "packet"}:
            self._last_packet_at = now
        with self._lock:
            self._payload = normalized
            self._updated_at = now
            heartbeat_age_ms = 0.0
            packet_age_ms = 0.0 if self._last_packet_at is not None else None
        return self.status(now=now) | {
            "heartbeat_age_ms": heartbeat_age_ms,
            "last_packet_age_ms": packet_age_ms,
        }

    def status(self, *, now: float | None = None) -> dict[str, Any]:
        current = time.time() if now is None else now
        with self._lock:
            payload = dict(self._payload or {})
            updated_at = self._updated_at
            last_packet_at = self._last_packet_at
        if updated_at is None:
            return {
                "ok": True,
                "connected": False,
                "receiving": False,
                "reason": "bridge_not_reported",
                "received": 0,
                "forwarded_frames": 0,
                "unsupported": 0,
            }
        heartbeat_age = current - updated_at
        packet_age = current - last_packet_at if last_packet_at is not None else None
        payload["connected"] = heartbeat_age <= self.stale_after_sec
        payload["receiving"] = packet_age is not None and packet_age <= self.stale_after_sec
        payload["reason"] = (
            "ok"
            if payload["receiving"]
            else "no_udp_packets"
            if int(payload.get("received") or 0) == 0
            else "udp_stale"
        )
        payload["heartbeat_age_ms"] = round(heartbeat_age * 1000, 1)
        payload["last_packet_age_ms"] = round(packet_age * 1000, 1) if packet_age is not None else None
        return payload


def _midpoint(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float]:
    return ((a[0] + b[0]) * 0.5, (a[1] + b[1]) * 0.5)


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def compute_body_axis(frame: BodyFrame | None, *, age_ms: float | None = None) -> dict[str, Any]:
    if frame is None:
        return {"locked": False, "confidence": 0.0, "reason": "no_frame"}

    joints = frame.joints_xy01
    left_shoulder = joints.get("left_shoulder")
    right_shoulder = joints.get("right_shoulder")
    left_hip = joints.get("left_hip")
    right_hip = joints.get("right_hip")
    if left_shoulder is None or right_shoulder is None:
        return {
            "locked": False,
            "confidence": 0.0,
            "reason": "missing_shoulder_pair",
            "joint_count": len(joints),
            "age_ms": age_ms,
        }

    shoulder_center = _midpoint(left_shoulder, right_shoulder)
    shoulder_width = _distance(left_shoulder, right_shoulder)
    hip_center = _midpoint(left_hip, right_hip) if left_hip is not None and right_hip is not None else None
    torso_center = _midpoint(shoulder_center, hip_center) if hip_center is not None else shoulder_center
    torso_height = abs(hip_center[1] - shoulder_center[1]) if hip_center is not None else None
    has_hips = hip_center is not None
    locked = shoulder_width >= 0.06 and (not has_hips or (torso_height is not None and torso_height >= 0.08))
    confidence = 0.55
    if shoulder_width >= 0.12:
        confidence += 0.2
    if has_hips:
        confidence += 0.2
    if age_ms is not None and age_ms <= 500:
        confidence += 0.05

    return {
        "locked": locked,
        "confidence": round(min(confidence, 1.0), 3) if locked else 0.25,
        "reason": "ok" if locked else "axis_unstable",
        "joint_count": len(joints),
        "age_ms": age_ms,
        "shoulder_center": [round(shoulder_center[0], 4), round(shoulder_center[1], 4)],
        "shoulder_width": round(shoulder_width, 4),
        "hip_center": [round(hip_center[0], 4), round(hip_center[1], 4)] if hip_center else None,
        "torso_center": [round(torso_center[0], 4), round(torso_center[1], 4)],
        "torso_height": round(torso_height, 4) if torso_height is not None else None,
    }


class LiveMocopiStore:
    def __init__(self, *, max_frames: int = 180, stale_after_sec: float = 1.2) -> None:
        self.max_frames = max_frames
        self.stale_after_sec = stale_after_sec
        self._records: deque[LiveMocopiRecord] = deque(maxlen=max_frames)
        self._lock = threading.Lock()
        self._next_index = 0
        self.bridge = MocopiBridgeStatus()

    def push_payload(self, payload: dict[str, Any], *, source: str = "mocopi-live") -> dict[str, Any]:
        frames_payload = payload if isinstance(payload.get("frames"), list) or isinstance(payload.get("mocopi_frames"), list) else {"frames": [payload]}
        frames = normalize_mocopi_frames(frames_payload, fallback=False)
        received_at = time.time()
        records: list[LiveMocopiRecord] = []
        with self._lock:
            for frame in frames:
                self._next_index += 1
                record = LiveMocopiRecord(
                    index=self._next_index,
                    received_at=received_at,
                    frame=frame,
                    source=source,
                )
                self._records.append(record)
                records.append(record)
        return self.status(now=received_at) | {"accepted_frames": len(records)}

    def recent_payload(self, *, max_frames: int = 48, max_age_sec: float = 6.0) -> dict[str, Any] | None:
        now = time.time()
        with self._lock:
            records = [
                record
                for record in self._records
                if now - record.received_at <= max_age_sec
            ][-max_frames:]
        if not records:
            return None
        return {
            "frames": [record.as_frame_payload() for record in records],
            "meta": {
                "source": "mocopi-live-buffer",
                "frame_count": len(records),
                "oldest_age_ms": round((now - records[0].received_at) * 1000, 1),
                "latest_age_ms": round((now - records[-1].received_at) * 1000, 1),
            },
        }

    def status(self, *, now: float | None = None) -> dict[str, Any]:
        current = time.time() if now is None else now
        with self._lock:
            latest = self._records[-1] if self._records else None
            frame_count = len(self._records)
        if latest is None:
            return {
                "ok": True,
                "connected": False,
                "frame_count": 0,
                "latest": None,
                "axis": compute_body_axis(None),
                "bridge": self.bridge.status(now=current),
            }

        age_sec = current - latest.received_at
        age_ms = round(age_sec * 1000, 1)
        return {
            "ok": True,
            "connected": age_sec <= self.stale_after_sec,
            "frame_count": frame_count,
            "latest": {
                "index": latest.index,
                "source": latest.source,
                "received_at": latest.received_at,
                "age_ms": age_ms,
                **latest.as_frame_payload(),
            },
            "axis": compute_body_axis(latest.frame, age_ms=age_ms),
            "bridge": self.bridge.status(now=current),
        }
