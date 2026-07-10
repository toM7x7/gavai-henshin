"""Serve a local mocopi UDP-to-body-sim/latest adapter.

This is a narrow engineering bridge, not a production live retargeter. It
accepts privacy-minimized JSON UDP packets, derives the same body-sim shape the
Quest archive path already understands, and exposes read-only HTTP endpoints for
Web/Quest rehearsal.
"""

from __future__ import annotations

import argparse
import json
import math
import socket
import struct
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from henshin.bodyfit import CoverScale, run_body_sequence  # noqa: E402
from henshin.iw_henshin import normalize_mocopi_frames  # noqa: E402


CONTRACT_VERSION = "mocopi-body-sim-latest-adapter.v1"
DEFAULT_UDP_PORT = 12351
DEFAULT_HTTP_PORT = 8021
BODY_SIM_PATHS = {"/body-sim/latest", "/api/mocopi/body-sim/latest"}
DEBUG_PATHS = {"/health", "/api/mocopi/debug/latest"}
LIVE_PACKET_STALE_AFTER_MS = 1500

MOCOPI_MMF_FORMAT_TYPE = b"sony motion format"
MOCOPI_MMF_CONTAINER_TYPES = {"head", "sndf", "skdf", "bons", "bndt", "fram", "btrs", "btdt", "sndt"}
MOCOPI_BONE_ID_TO_CANONICAL_JOINT = {
    11: "left_shoulder",
    13: "left_elbow",
    14: "left_wrist",
    15: "right_shoulder",
    17: "right_elbow",
    18: "right_wrist",
    19: "left_hip",
    20: "left_knee",
    21: "left_ankle",
    23: "right_hip",
    24: "right_knee",
    25: "right_ankle",
}
MOCOPI_ROTATION_CHAINS = [
    {
        "start": "left_shoulder",
        "mid": "left_elbow",
        "end": "left_wrist",
        "upper_chain": (11, 12),
        "lower_chain": (11, 12, 13),
    },
    {
        "start": "right_shoulder",
        "mid": "right_elbow",
        "end": "right_wrist",
        "upper_chain": (15, 16),
        "lower_chain": (15, 16, 17),
    },
    {
        "start": "left_hip",
        "mid": "left_knee",
        "end": "left_ankle",
        "upper_chain": (0, 19),
        "lower_chain": (0, 19, 20),
    },
    {
        "start": "right_hip",
        "mid": "right_knee",
        "end": "right_ankle",
        "upper_chain": (0, 23),
        "lower_chain": (0, 23, 24),
    },
]
DEFAULT_MOCOPI_JOINTS_XY01 = {
    "left_shoulder": (0.62, 0.38),
    "right_shoulder": (0.38, 0.38),
    "left_elbow": (0.67, 0.48),
    "right_elbow": (0.33, 0.48),
    "left_wrist": (0.70, 0.61),
    "right_wrist": (0.225, 0.625),
    "left_hip": (0.57, 0.58),
    "right_hip": (0.43, 0.58),
    "left_knee": (0.57, 0.76),
    "right_knee": (0.43, 0.76),
    "left_ankle": (0.57, 0.92),
    "right_ankle": (0.43, 0.92),
}


class MocopiBodySimLatestAdapter:
    def __init__(self, *, max_frames: int = 120) -> None:
        self.max_frames = max_frames
        self.started_at = time.time()
        self.packet_count = 0
        self.valid_packet_count = 0
        self.unsupported_packet_count = 0
        self.last_sender = ""
        self.last_error = ""
        self.last_received_at: float | None = None
        self.last_valid_received_at: float | None = None
        self._latest_body_sim: dict[str, Any] | None = None
        self._lock = threading.Lock()

    def ingest_packet(self, payload: bytes, *, sender: str = "") -> dict[str, Any]:
        now = time.time()
        result = payload_to_body_sim(payload, max_frames=self.max_frames)
        with self._lock:
            self.packet_count += 1
            self.last_sender = sender
            self.last_received_at = now
            if result["ok"]:
                self.valid_packet_count += 1
                self.last_error = ""
                self.last_valid_received_at = now
                self._latest_body_sim = result["body_sim"]
            else:
                self.unsupported_packet_count += 1
                self.last_error = result["error"]
        return result

    def latest_body_sim(self) -> dict[str, Any] | None:
        with self._lock:
            if not self._latest_body_sim:
                return None
            body_sim = json.loads(json.dumps(self._latest_body_sim))
            self._attach_runtime_status(body_sim)
            return body_sim

    def debug_summary(self) -> dict[str, Any]:
        with self._lock:
            frame_count = len(self._latest_body_sim.get("frames", [])) if self._latest_body_sim else 0
            motion_source = str(
                (self._latest_body_sim or {}).get("motion_source")
                or (self._latest_body_sim or {}).get("source")
                or ""
            )
            age_ms = None if self.last_received_at is None else round((time.time() - self.last_received_at) * 1000, 3)
            valid_age_ms = None if self.last_valid_received_at is None else round((time.time() - self.last_valid_received_at) * 1000, 3)
            stale = valid_age_ms is None or valid_age_ms > LIVE_PACKET_STALE_AFTER_MS
            return {
                "contract_version": CONTRACT_VERSION,
                "ok": self._latest_body_sim is not None,
                "uptime_sec": round(time.time() - self.started_at, 3),
                "packet_count": self.packet_count,
                "valid_packet_count": self.valid_packet_count,
                "unsupported_packet_count": self.unsupported_packet_count,
                "last_sender": self.last_sender,
                "last_packet_age_ms": age_ms,
                "last_valid_packet_age_ms": valid_age_ms,
                "last_error": self.last_error,
                "latest": {
                    "present": self._latest_body_sim is not None,
                    "frame_count": frame_count,
                    "motion_source": motion_source,
                    "body_sim_url": "/body-sim/latest",
                    "stale": stale,
                },
                "privacy_note": "Raw UDP motion payloads are not retained; only derived latest body-sim state is kept in memory.",
            }

    def _attach_runtime_status(self, body_sim: dict[str, Any]) -> None:
        valid_age_ms = None if self.last_valid_received_at is None else round((time.time() - self.last_valid_received_at) * 1000, 3)
        stale = valid_age_ms is None or valid_age_ms > LIVE_PACKET_STALE_AFTER_MS
        body_sim["adapter_packet_age_ms"] = valid_age_ms
        body_sim["adapter_stale"] = stale
        body_sim["adapter_stale_after_ms"] = LIVE_PACKET_STALE_AFTER_MS
        metadata = body_sim.get("metadata") if isinstance(body_sim.get("metadata"), dict) else {}
        body_sim["metadata"] = {
            **metadata,
            "adapter_packet_age_ms": valid_age_ms,
            "adapter_stale": stale,
            "adapter_stale_after_ms": LIVE_PACKET_STALE_AFTER_MS,
        }


def payload_to_body_sim(payload: bytes, *, max_frames: int = 120) -> dict[str, Any]:
    try:
        decoded = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        decoded = _decode_mocopi_mmf_payload(payload)
        if decoded is None:
            return {"ok": False, "error": f"unsupported UDP payload; expected JSON or mocopi MMF: {exc}"}
    if not isinstance(decoded, dict):
        return {"ok": False, "error": "unsupported UDP payload; JSON root must be an object"}

    body_sim = _body_sim_from_payload(decoded, max_frames=max_frames)
    if body_sim is None:
        return {"ok": False, "error": "payload did not contain body_sim frames or mocopi-like frames"}
    return {"ok": True, "body_sim": body_sim}


def _decode_mocopi_mmf_payload(payload: bytes) -> dict[str, Any] | None:
    try:
        boxes = _parse_mocopi_mmf_boxes(payload)
    except ValueError:
        return None
    if not _is_mocopi_mmf_boxes(boxes):
        return None

    frame_box = _find_first_box(boxes, "fram")
    skeleton_box = _find_first_box(boxes, "skdf")
    frame = _mocopi_frame_box_to_mocopi_like_frame(frame_box) if frame_box else None
    if frame is None and skeleton_box is not None:
        frame = _mocopi_skeleton_box_to_mocopi_like_frame(skeleton_box)
    if frame is None:
        return None

    return {
        "source": "mocopi",
        "motion_source": "mocopi",
        "format": "mocopi-motion-serializer.mmf.v1",
        "frames": _with_equip_bootstrap_frame(frame),
        "metadata": {
            "motion_source": "mocopi",
            "input_format": "mocopi-motion-serializer.mmf.v1",
            "retarget": "mocopi-rotation-chain.xy01.v1",
            "raw_payload_retained": False,
        },
    }


def _parse_mocopi_mmf_boxes(payload: bytes, *, offset: int = 0, end: int | None = None) -> list[dict[str, Any]]:
    end = len(payload) if end is None else end
    boxes: list[dict[str, Any]] = []
    while offset < end:
        if offset + 8 > end:
            raise ValueError("incomplete mocopi MMF box header")
        size = struct.unpack_from("<I", payload, offset)[0]
        try:
            type_4cc = payload[offset + 4 : offset + 8].decode("ascii")
        except UnicodeDecodeError as exc:
            raise ValueError("invalid mocopi MMF box type") from exc
        data_start = offset + 8
        data_end = data_start + size
        if size <= 0 or data_end > end:
            raise ValueError("invalid mocopi MMF box size")
        data = payload[data_start:data_end]
        children: list[dict[str, Any]] = []
        if type_4cc in MOCOPI_MMF_CONTAINER_TYPES:
            try:
                children = _parse_mocopi_mmf_boxes(payload, offset=data_start, end=data_end)
            except ValueError:
                children = []
        boxes.append({"type": type_4cc, "data": data, "children": children})
        offset = data_end
    return boxes


def _is_mocopi_mmf_boxes(boxes: list[dict[str, Any]]) -> bool:
    head = _find_first_box(boxes, "head")
    if head is None:
        return False
    ftyp = _find_first_box(head.get("children", []), "ftyp")
    version = _find_first_box(head.get("children", []), "vrsn")
    if ftyp is None or ftyp.get("data") != MOCOPI_MMF_FORMAT_TYPE:
        return False
    return version is None or version.get("data", b"\x01")[:1] == b"\x01"


def _find_first_box(boxes: list[dict[str, Any]], type_4cc: str) -> dict[str, Any] | None:
    for box in boxes:
        if box.get("type") == type_4cc:
            return box
        found = _find_first_box(box.get("children", []), type_4cc)
        if found is not None:
            return found
    return None


def _find_child_boxes(box: dict[str, Any], type_4cc: str) -> list[dict[str, Any]]:
    return [child for child in box.get("children", []) if child.get("type") == type_4cc]


def _mocopi_frame_box_to_mocopi_like_frame(frame_box: dict[str, Any]) -> dict[str, Any] | None:
    frame_number = _box_i32(_find_first_box(frame_box.get("children", []), "fnum")) or 0
    records = []
    for transform_box in _find_child_boxes(_find_first_box(frame_box.get("children", []), "btrs") or {}, "btdt"):
        record = _mocopi_transform_record(transform_box)
        if record is not None:
            records.append(record)
    if not records:
        return None
    return _mocopi_records_to_mocopi_like_frame(records, frame_number=frame_number)


def _mocopi_skeleton_box_to_mocopi_like_frame(skeleton_box: dict[str, Any]) -> dict[str, Any] | None:
    records = []
    for bone_box in _find_child_boxes(_find_first_box(skeleton_box.get("children", []), "bons") or {}, "bndt"):
        record = _mocopi_transform_record(bone_box)
        if record is not None:
            records.append(record)
    if not records:
        return None
    return _mocopi_records_to_mocopi_like_frame(records, frame_number=0)


def _mocopi_transform_record(box: dict[str, Any]) -> dict[str, Any] | None:
    bone_id = _box_i16(_find_first_box(box.get("children", []), "bnid"))
    transform = _box_transform(_find_first_box(box.get("children", []), "tran"))
    if bone_id is None or transform is None:
        return None
    return {"bone_id": bone_id, **transform}


def _box_i32(box: dict[str, Any] | None) -> int | None:
    data = box.get("data", b"") if isinstance(box, dict) else b""
    return struct.unpack("<i", data[:4])[0] if len(data) >= 4 else None


def _box_i16(box: dict[str, Any] | None) -> int | None:
    data = box.get("data", b"") if isinstance(box, dict) else b""
    return struct.unpack("<h", data[:2])[0] if len(data) >= 2 else None


def _box_transform(box: dict[str, Any] | None) -> dict[str, Any] | None:
    data = box.get("data", b"") if isinstance(box, dict) else b""
    if len(data) < 28:
        return None
    rx, ry, rz, rw, px, py, pz = struct.unpack("<7f", data[:28])
    return {
        "rotation": (rx, ry, rz, rw),
        "position": (px, py, pz),
    }


def _mocopi_records_to_mocopi_like_frame(records: list[dict[str, Any]], *, frame_number: int) -> dict[str, Any] | None:
    positions: dict[str, tuple[float, float, float]] = {}
    records_by_bone: dict[int, dict[str, Any]] = {}
    for record in records:
        bone_id = int(record["bone_id"])
        records_by_bone[bone_id] = record
        canonical = MOCOPI_BONE_ID_TO_CANONICAL_JOINT.get(bone_id)
        if canonical is not None:
            positions[canonical] = tuple(float(value) for value in record["position"])
    if not positions:
        return None

    bones = _rotation_retargeted_xy01(records_by_bone, fallback=_positions_to_xy01(positions))
    if not bones:
        return None
    return {
        "dt_sec": 0.1,
        "frame_number": frame_number,
        "bones": bones,
        "metadata": {
            "input_format": "mocopi-motion-serializer.mmf.v1",
            "retarget": "mocopi-rotation-chain.xy01.v1",
        },
    }


def _rotation_retargeted_xy01(records_by_bone: dict[int, dict[str, Any]], *, fallback: dict[str, list[float]]) -> dict[str, list[float]]:
    if not any("rotation" in record for record in records_by_bone.values()):
        return fallback

    bones = {name: [float(default_xy[0]), float(default_xy[1])] for name, default_xy in DEFAULT_MOCOPI_JOINTS_XY01.items()}

    for spec in MOCOPI_ROTATION_CHAINS:
        start_name = str(spec["start"])
        mid_name = str(spec["mid"])
        end_name = str(spec["end"])
        start = tuple(bones[start_name])
        default_mid = DEFAULT_MOCOPI_JOINTS_XY01[mid_name]
        default_end = DEFAULT_MOCOPI_JOINTS_XY01[end_name]

        upper_dx = default_mid[0] - DEFAULT_MOCOPI_JOINTS_XY01[start_name][0]
        upper_dy = default_mid[1] - DEFAULT_MOCOPI_JOINTS_XY01[start_name][1]
        lower_dx = default_end[0] - default_mid[0]
        lower_dy = default_end[1] - default_mid[1]

        upper_direction = _direction_from_rotation_chain(records_by_bone, spec["upper_chain"], (upper_dx, upper_dy))
        mid = _extend_xy01(start, upper_direction, math.hypot(upper_dx, upper_dy))
        bones[mid_name] = [round(mid[0], 6), round(mid[1], 6)]

        lower_direction = _direction_from_rotation_chain(records_by_bone, spec["lower_chain"], (lower_dx, lower_dy))
        end = _extend_xy01(mid, lower_direction, math.hypot(lower_dx, lower_dy))
        bones[end_name] = [round(end[0], 6), round(end[1], 6)]

    return {name: [round(_clamp01(value[0]), 6), round(_clamp01(value[1]), 6)] for name, value in bones.items()}


def _direction_from_rotation_chain(
    records_by_bone: dict[int, dict[str, Any]],
    chain: tuple[int, ...],
    rest_direction_xy: tuple[float, float],
) -> tuple[float, float]:
    chain_rotation = _chain_quaternion(records_by_bone, chain)
    if chain_rotation is None:
        return _unit_xy(rest_direction_xy)

    rest_dx, rest_dy = rest_direction_xy
    rotated = _quat_rotate_vector(chain_rotation, (rest_dx, -rest_dy, 0.0))
    direction = (rotated[0], -rotated[1])
    if math.hypot(direction[0], direction[1]) < 0.0001:
        return _unit_xy(rest_direction_xy)
    return _unit_xy(direction)


def _chain_quaternion(records_by_bone: dict[int, dict[str, Any]], chain: tuple[int, ...]) -> tuple[float, float, float, float] | None:
    combined: tuple[float, float, float, float] | None = None
    for bone_id in chain:
        record = records_by_bone.get(bone_id)
        if record is None:
            continue
        rotation = tuple(float(value) for value in record.get("rotation", ()))
        if len(rotation) != 4:
            continue
        unity_rotation = _mocopi_quaternion_to_unity(rotation)
        combined = unity_rotation if combined is None else _quat_multiply(combined, unity_rotation)
    return _normalize_quaternion(combined) if combined is not None else None


def _mocopi_quaternion_to_unity(rotation: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
    x, y, z, w = _normalize_quaternion(rotation)
    return _normalize_quaternion((-x, y, z, -w))


def _quat_multiply(
    left: tuple[float, float, float, float],
    right: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    lx, ly, lz, lw = _normalize_quaternion(left)
    rx, ry, rz, rw = _normalize_quaternion(right)
    return (
        lw * rx + lx * rw + ly * rz - lz * ry,
        lw * ry - lx * rz + ly * rw + lz * rx,
        lw * rz + lx * ry - ly * rx + lz * rw,
        lw * rw - lx * rx - ly * ry - lz * rz,
    )


def _quat_rotate_vector(
    rotation: tuple[float, float, float, float],
    vector: tuple[float, float, float],
) -> tuple[float, float, float]:
    x, y, z, w = _normalize_quaternion(rotation)
    vx, vy, vz = vector
    uv = (y * vz - z * vy, z * vx - x * vz, x * vy - y * vx)
    uuv = (y * uv[2] - z * uv[1], z * uv[0] - x * uv[2], x * uv[1] - y * uv[0])
    return (
        vx + 2.0 * (w * uv[0] + uuv[0]),
        vy + 2.0 * (w * uv[1] + uuv[1]),
        vz + 2.0 * (w * uv[2] + uuv[2]),
    )


def _normalize_quaternion(rotation: tuple[float, float, float, float] | None) -> tuple[float, float, float, float]:
    if rotation is None:
        return (0.0, 0.0, 0.0, 1.0)
    x, y, z, w = rotation
    length = math.sqrt(x * x + y * y + z * z + w * w)
    if length < 0.000001:
        return (0.0, 0.0, 0.0, 1.0)
    return (x / length, y / length, z / length, w / length)


def _unit_xy(direction: tuple[float, float]) -> tuple[float, float]:
    length = math.hypot(direction[0], direction[1])
    if length < 0.000001:
        return (0.0, 1.0)
    return (direction[0] / length, direction[1] / length)


def _extend_xy01(start: tuple[float, float], direction: tuple[float, float], length: float) -> tuple[float, float]:
    return (
        _clamp01(start[0] + direction[0] * length),
        _clamp01(start[1] + direction[1] * length),
    )


def _positions_to_xy01(positions: dict[str, tuple[float, float, float]]) -> dict[str, list[float]]:
    xy = {name: (pos[0], pos[1]) for name, pos in positions.items()}
    if _positions_look_normalized(xy):
        return {name: [round(_clamp01(x), 6), round(_clamp01(y), 6)] for name, (x, y) in xy.items()}

    xs = [point[0] for point in xy.values()]
    ys = [point[1] for point in xy.values()]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    span_x = max_x - min_x
    span_y = max_y - min_y
    if span_x < 0.001 or span_y < 0.001:
        return {name: [x, y] for name, (x, y) in DEFAULT_MOCOPI_JOINTS_XY01.items() if name in positions}

    converted: dict[str, list[float]] = {}
    for name, (x, y) in xy.items():
        x01 = 0.15 + 0.70 * ((x - min_x) / span_x)
        y01 = 0.05 + 0.90 * (1.0 - ((y - min_y) / span_y))
        converted[name] = [round(_clamp01(x01), 6), round(_clamp01(y01), 6)]
    return converted


def _positions_look_normalized(xy: dict[str, tuple[float, float]]) -> bool:
    if len(xy) < 4:
        return False
    xs = [point[0] for point in xy.values()]
    ys = [point[1] for point in xy.values()]
    return all(-0.05 <= value <= 1.05 for value in [*xs, *ys]) and (max(xs) - min(xs)) > 0.05 and (max(ys) - min(ys)) > 0.05


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _with_equip_bootstrap_frame(frame: dict[str, Any]) -> list[dict[str, Any]]:
    bootstrap = json.loads(json.dumps(frame))
    bones = bootstrap.setdefault("bones", {})
    bones["right_wrist"] = [0.225, 0.625]
    bootstrap["dt_sec"] = 0.1
    bootstrap["frame_number"] = -1
    bootstrap["metadata"] = {**(bootstrap.get("metadata") if isinstance(bootstrap.get("metadata"), dict) else {}), "bootstrap": "equip-dock"}
    return [bootstrap, frame]


def _body_sim_from_payload(payload: dict[str, Any], *, max_frames: int) -> dict[str, Any] | None:
    embedded = payload.get("body_sim")
    if isinstance(embedded, dict) and _has_body_sim_frames(embedded):
        return _normalize_body_sim(embedded, source_payload=payload, max_frames=max_frames)
    if _has_body_sim_frames(payload):
        return _normalize_body_sim(payload, source_payload=payload, max_frames=max_frames)
    if not _has_mocopi_like_frames(payload):
        return None
    frames = normalize_mocopi_frames(payload)
    if not frames:
        return None
    body_sim = run_body_sequence(
        frames[:max_frames],
        mirror=True,
        cover_scale=CoverScale(1.0, 1.0),
        hold_to_equip_sec=0.1,
    )
    return _normalize_body_sim(body_sim, source_payload=payload, max_frames=max_frames)


def _has_body_sim_frames(payload: dict[str, Any]) -> bool:
    frames = payload.get("frames")
    return isinstance(frames, list) and any(isinstance(frame, dict) and isinstance(frame.get("segments"), dict) for frame in frames)


def _has_mocopi_like_frames(payload: dict[str, Any]) -> bool:
    frames = payload.get("frames") or payload.get("mocopi_frames")
    return isinstance(frames, list) and any(isinstance(frame, dict) for frame in frames)


def _normalize_body_sim(body_sim: dict[str, Any], *, source_payload: dict[str, Any], max_frames: int) -> dict[str, Any]:
    frames = body_sim.get("frames") if isinstance(body_sim.get("frames"), list) else []
    clipped_frames = frames[-max_frames:]
    source = _motion_source(source_payload, body_sim)
    source_metadata = source_payload.get("metadata") if isinstance(source_payload.get("metadata"), dict) else {}
    body_metadata = body_sim.get("metadata") if isinstance(body_sim.get("metadata"), dict) else {}
    normalized = {
        **body_sim,
        "contract_version": CONTRACT_VERSION,
        "source": source,
        "motion_source": source,
        "frames": clipped_frames,
        "frame_count": len(clipped_frames),
        "updated_at_unix_ms": int(time.time() * 1000),
        "metadata": {
            **source_metadata,
            **body_metadata,
            "source": source,
            "motion_source": source,
            "adapter": CONTRACT_VERSION,
            "raw_payload_retained": False,
            "latest_endpoint": "/body-sim/latest",
        },
    }
    return normalized


def _motion_source(source_payload: dict[str, Any], body_sim: dict[str, Any]) -> str:
    candidates = [
        source_payload.get("motion_source"),
        source_payload.get("source"),
        body_sim.get("motion_source"),
        body_sim.get("source"),
        (source_payload.get("metadata") or {}).get("motion_source") if isinstance(source_payload.get("metadata"), dict) else "",
    ]
    text = " ".join(str(value or "").lower() for value in candidates)
    return "mocopi" if "mocopi" in text else "body_sim"


def make_handler(adapter: MocopiBodySimLatestAdapter) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            path = self.path.split("?", 1)[0]
            if path in BODY_SIM_PATHS:
                body_sim = adapter.latest_body_sim()
                if body_sim is None:
                    self._send_json({"ok": False, "error": "No mocopi body-sim payload has been received yet."}, status=404)
                    return
                self._send_json(body_sim)
                return
            if path in DEBUG_PATHS:
                self._send_json(adapter.debug_summary())
                return
            self._send_json({"ok": False, "error": f"Unknown endpoint: {path}"}, status=404)

        def log_message(self, format: str, *args: Any) -> None:
            return

        def _send_json(self, payload: dict[str, Any], *, status: int = 200) -> None:
            body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def run_udp_receiver(
    adapter: MocopiBodySimLatestAdapter,
    *,
    bind_host: str,
    udp_port: int,
    stop_event: threading.Event,
    timeout_sec: float = 0.25,
) -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((bind_host, udp_port))
        sock.settimeout(timeout_sec)
        while not stop_event.is_set():
            try:
                payload, sender = sock.recvfrom(65535)
            except socket.timeout:
                continue
            adapter.ingest_packet(payload, sender=f"{sender[0]}:{sender[1]}")


def run_server(*, bind_host: str, udp_port: int, http_host: str, http_port: int, max_frames: int) -> None:
    adapter = MocopiBodySimLatestAdapter(max_frames=max_frames)
    stop_event = threading.Event()
    udp_thread = threading.Thread(
        target=run_udp_receiver,
        args=(adapter,),
        kwargs={"bind_host": bind_host, "udp_port": udp_port, "stop_event": stop_event},
        daemon=True,
    )
    udp_thread.start()
    server = ThreadingHTTPServer((http_host, http_port), make_handler(adapter))
    print(f"mocopi body-sim latest HTTP: http://{http_host}:{http_port}/body-sim/latest")
    print(f"mocopi UDP listen: {bind_host}:{udp_port}")
    try:
        server.serve_forever()
    finally:
        stop_event.set()
        server.server_close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bind-host", default="0.0.0.0")
    parser.add_argument("--udp-port", type=int, default=DEFAULT_UDP_PORT)
    parser.add_argument("--http-host", default="127.0.0.1")
    parser.add_argument("--http-port", type=int, default=DEFAULT_HTTP_PORT)
    parser.add_argument("--max-frames", type=int, default=120)
    args = parser.parse_args(argv)

    run_server(
        bind_host=args.bind_host,
        udp_port=args.udp_port,
        http_host=args.http_host,
        http_port=args.http_port,
        max_frames=args.max_frames,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
