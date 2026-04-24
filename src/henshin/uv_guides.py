"""Generate cached UV guide images from mesh.v1 assets and UV contracts."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Literal

from PIL import Image, ImageDraw, ImageFilter

from .mesh_assets import load_mesh_payload, resolve_mesh_asset_path
from .uv_contracts import serialize_uv_contract


GUIDE_SIZE = 1024
GUIDE_ALGORITHM_VERSION = "uv-normal-fold-v1"
AI_REFERENCE_GUIDE_ALGORITHM_VERSION = "uv-ai-reference-v3"
TOPOLOGY_MASK_GUIDE_ALGORITHM_VERSION = "uv-topology-mask-v3"
CREASE_ANGLE_THRESHOLD_DEGREES = 35.0
GuideProfile = Literal["debug", "ai_reference", "topology_mask"]

SEMANTIC_FILL_COLORS: dict[str, tuple[int, int, int, int]] = {
    "front": (46, 173, 226, 46),
    "rear": (93, 171, 93, 42),
    "left_side": (148, 104, 209, 42),
    "right_side": (187, 116, 196, 42),
    "top": (235, 190, 73, 36),
    "underside": (116, 128, 148, 36),
    "transition": (112, 151, 199, 26),
}

AI_SEMANTIC_FILL_COLORS: dict[str, tuple[int, int, int, int]] = {
    "front": (225, 225, 225, 72),
    "rear": (202, 202, 202, 58),
    "left_side": (214, 214, 214, 56),
    "right_side": (214, 214, 214, 56),
    "top": (232, 232, 232, 52),
    "underside": (188, 188, 188, 44),
    "transition": (220, 220, 220, 34),
}

TOPOLOGY_OCCUPANCY_FILL = (136, 136, 136, 64)

SEMANTIC_LEGEND: dict[str, str] = {
    "front": "cyan fill = front-facing identity surface",
    "rear": "green fill = rear/service surface",
    "left_side": "purple fill = left-side wrap surface",
    "right_side": "pink fill = right-side wrap surface",
    "top": "amber fill = top/crown/load cap surface",
    "underside": "gray fill = underside or low-emphasis fold-under surface",
    "transition": "pale blue fill = transitional curved surface",
    "crease": "orange line = normal break, fold, formed edge, or hard panel bend",
    "boundary": "blue-gray line = UV island boundary or open seam",
    "motif_zone": "amber rounded rectangle = primary motif zone",
    "seam_safe": "pale border = low-frequency seam-safe margin",
}

PRIMARY_ZONE_BOXES: dict[str, tuple[float, float, float, float]] = {
    "helmet": (0.28, 0.18, 0.72, 0.48),
    "chest": (0.22, 0.18, 0.78, 0.56),
    "back": (0.26, 0.18, 0.74, 0.60),
    "left_shoulder": (0.24, 0.16, 0.70, 0.46),
    "right_shoulder": (0.30, 0.16, 0.76, 0.46),
    "left_upperarm": (0.28, 0.16, 0.72, 0.84),
    "right_upperarm": (0.28, 0.16, 0.72, 0.84),
    "left_forearm": (0.26, 0.12, 0.74, 0.88),
    "right_forearm": (0.26, 0.12, 0.74, 0.88),
    "waist": (0.16, 0.28, 0.84, 0.70),
    "left_thigh": (0.26, 0.14, 0.74, 0.84),
    "right_thigh": (0.26, 0.14, 0.74, 0.84),
    "left_shin": (0.28, 0.10, 0.72, 0.88),
    "right_shin": (0.28, 0.10, 0.72, 0.88),
    "left_boot": (0.20, 0.34, 0.80, 0.86),
    "right_boot": (0.20, 0.34, 0.80, 0.86),
    "left_hand": (0.24, 0.22, 0.76, 0.74),
    "right_hand": (0.24, 0.22, 0.76, 0.74),
}


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def _contract_hash(contract: dict[str, Any]) -> str:
    payload = json.dumps(contract, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return _hash_bytes(payload)


def _guide_algorithm_version(guide_profile: GuideProfile) -> str:
    if guide_profile == "topology_mask":
        return TOPOLOGY_MASK_GUIDE_ALGORITHM_VERSION
    if guide_profile == "ai_reference":
        return AI_REFERENCE_GUIDE_ALGORITHM_VERSION
    return GUIDE_ALGORITHM_VERSION


def _cache_path(
    session_root: Path,
    part: str,
    mesh_hash: str,
    contract_hash: str,
    semantic_hash: str,
    guide_profile: GuideProfile,
) -> Path:
    if guide_profile == "topology_mask":
        version_slug = TOPOLOGY_MASK_GUIDE_ALGORITHM_VERSION.replace("-", "_")
        return session_root / "_cache" / "uv-guides-mask" / f"{part}__{mesh_hash}__{contract_hash}__{semantic_hash}__{version_slug}.png"
    if guide_profile == "ai_reference":
        version_slug = AI_REFERENCE_GUIDE_ALGORITHM_VERSION.replace("-", "_")
        return session_root / "_cache" / "uv-guides-ai" / f"{part}__{mesh_hash}__{contract_hash}__{semantic_hash}__{version_slug}.png"
    return session_root / "_cache" / "uv-guides" / f"{part}__{mesh_hash}__{contract_hash}__{semantic_hash}.png"


def _normalized_box(box: tuple[float, float, float, float], size: int) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = box
    return (int(size * x0), int(size * y0), int(size * x1), int(size * y1))


def _dashed_vertical(draw: ImageDraw.ImageDraw, x: int, y0: int, y1: int, *, dash: int, gap: int, fill: tuple[int, int, int, int], width: int) -> None:
    y = y0
    while y < y1:
        draw.line((x, y, x, min(y + dash, y1)), fill=fill, width=width)
        y += dash + gap


def _uv_point(uv: list[float], index: int, size: int) -> tuple[float, float]:
    return uv[index * 2] * size, (1.0 - uv[index * 2 + 1]) * size


def _vec3(values: list[float], index: int) -> tuple[float, float, float]:
    return values[index * 3], values[index * 3 + 1], values[index * 3 + 2]


def _sub(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return a[0] - b[0], a[1] - b[1], a[2] - b[2]


def _cross(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _normalize(v: tuple[float, float, float]) -> tuple[float, float, float]:
    mag = math.sqrt(_dot(v, v))
    if mag <= 0.000001:
        return (0.0, 0.0, 1.0)
    return v[0] / mag, v[1] / mag, v[2] / mag


def _triangle_indices(payload: dict[str, Any]) -> list[tuple[int, int, int]]:
    indices = payload.get("indices") or []
    if indices:
        return [(int(indices[i]), int(indices[i + 1]), int(indices[i + 2])) for i in range(0, len(indices), 3)]
    count = len(payload["uv"]) // 2
    return [(i, i + 1, i + 2) for i in range(0, count, 3)]


def _triangle_normal(payload: dict[str, Any], tri: tuple[int, int, int]) -> tuple[float, float, float]:
    normals = payload.get("normals")
    if isinstance(normals, list) and len(normals) >= (max(tri) + 1) * 3:
        a = _vec3(normals, tri[0])
        b = _vec3(normals, tri[1])
        c = _vec3(normals, tri[2])
        return _normalize((a[0] + b[0] + c[0], a[1] + b[1] + c[1], a[2] + b[2] + c[2]))

    positions = payload["positions"]
    pa = _vec3(positions, tri[0])
    pb = _vec3(positions, tri[1])
    pc = _vec3(positions, tri[2])
    return _normalize(_cross(_sub(pb, pa), _sub(pc, pa)))


def _classify_normal(normal: tuple[float, float, float]) -> str:
    x, y, z = normal
    if z <= -0.45:
        return "front"
    if z >= 0.45:
        return "rear"
    if x <= -0.50:
        return "left_side"
    if x >= 0.50:
        return "right_side"
    if y >= 0.62:
        return "top"
    if y <= -0.62:
        return "underside"
    return "transition"


def analyze_uv_semantics(payload: dict[str, Any]) -> dict[str, Any]:
    triangles = _triangle_indices(payload)
    face_normals = [_triangle_normal(payload, tri) for tri in triangles]
    semantic_counts: dict[str, int] = {}
    for normal in face_normals:
        semantic = _classify_normal(normal)
        semantic_counts[semantic] = semantic_counts.get(semantic, 0) + 1

    edge_faces: dict[tuple[int, int], list[int]] = {}
    for face_index, tri in enumerate(triangles):
        for a, b in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
            edge = (min(a, b), max(a, b))
            edge_faces.setdefault(edge, []).append(face_index)

    crease_threshold = math.cos(math.radians(CREASE_ANGLE_THRESHOLD_DEGREES))
    crease_edges = 0
    boundary_edges = 0
    for faces in edge_faces.values():
        if len(faces) == 1:
            boundary_edges += 1
        elif len(faces) >= 2 and _dot(face_normals[faces[0]], face_normals[faces[1]]) < crease_threshold:
            crease_edges += 1

    return {
        "guide_algorithm_version": GUIDE_ALGORITHM_VERSION,
        "normal_source": "vertex_normals" if isinstance(payload.get("normals"), list) else "derived_face_normals",
        "triangle_count": len(triangles),
        "normal_semantic_counts": semantic_counts,
        "crease_angle_threshold_degrees": CREASE_ANGLE_THRESHOLD_DEGREES,
        "crease_edge_count": crease_edges,
        "boundary_edge_count": boundary_edges,
        "legend": dict(SEMANTIC_LEGEND),
    }


def _semantic_hash(summary: dict[str, Any]) -> str:
    payload = json.dumps(summary, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return _hash_bytes(payload)


def _draw_semantic_fills(draw: ImageDraw.ImageDraw, payload: dict[str, Any], size: int) -> None:
    uv = payload["uv"]
    for tri in _triangle_indices(payload):
        normal = _triangle_normal(payload, tri)
        semantic = _classify_normal(normal)
        color = SEMANTIC_FILL_COLORS.get(semantic, SEMANTIC_FILL_COLORS["transition"])
        points = [_uv_point(uv, tri[0], size), _uv_point(uv, tri[1], size), _uv_point(uv, tri[2], size)]
        draw.polygon(points, fill=color)


def _draw_ai_semantic_fills(draw: ImageDraw.ImageDraw, payload: dict[str, Any], size: int) -> None:
    uv = payload["uv"]
    for tri in _triangle_indices(payload):
        normal = _triangle_normal(payload, tri)
        semantic = _classify_normal(normal)
        color = AI_SEMANTIC_FILL_COLORS.get(semantic, AI_SEMANTIC_FILL_COLORS["transition"])
        points = [_uv_point(uv, tri[0], size), _uv_point(uv, tri[1], size), _uv_point(uv, tri[2], size)]
        draw.polygon(points, fill=color)


def _draw_topology_occupancy_mask(draw: ImageDraw.ImageDraw, payload: dict[str, Any], size: int) -> None:
    uv = payload["uv"]
    for tri in _triangle_indices(payload):
        points = [_uv_point(uv, tri[0], size), _uv_point(uv, tri[1], size), _uv_point(uv, tri[2], size)]
        draw.polygon(points, fill=TOPOLOGY_OCCUPANCY_FILL)


def _draw_fold_and_boundary_edges(draw: ImageDraw.ImageDraw, payload: dict[str, Any], size: int) -> None:
    triangles = _triangle_indices(payload)
    normals = [_triangle_normal(payload, tri) for tri in triangles]
    edge_faces: dict[tuple[int, int], list[tuple[int, tuple[int, int]]]] = {}
    for face_index, tri in enumerate(triangles):
        for a, b in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
            edge = (min(a, b), max(a, b))
            edge_faces.setdefault(edge, []).append((face_index, (a, b)))

    crease_threshold = math.cos(math.radians(CREASE_ANGLE_THRESHOLD_DEGREES))
    uv = payload["uv"]
    for faces in edge_faces.values():
        _, oriented = faces[0]
        a, b = oriented
        p0 = _uv_point(uv, a, size)
        p1 = _uv_point(uv, b, size)
        if len(faces) == 1:
            draw.line((*p0, *p1), fill=(43, 82, 130, 150), width=2)
            continue
        if len(faces) >= 2 and _dot(normals[faces[0][0]], normals[faces[1][0]]) < crease_threshold:
            draw.line((*p0, *p1), fill=(238, 126, 36, 230), width=4)


def _draw_ai_fold_and_boundary_edges(draw: ImageDraw.ImageDraw, payload: dict[str, Any], size: int) -> None:
    triangles = _triangle_indices(payload)
    normals = [_triangle_normal(payload, tri) for tri in triangles]
    edge_faces: dict[tuple[int, int], list[tuple[int, tuple[int, int]]]] = {}
    for face_index, tri in enumerate(triangles):
        for a, b in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
            edge = (min(a, b), max(a, b))
            edge_faces.setdefault(edge, []).append((face_index, (a, b)))

    crease_threshold = math.cos(math.radians(CREASE_ANGLE_THRESHOLD_DEGREES))
    uv = payload["uv"]
    for faces in edge_faces.values():
        _, oriented = faces[0]
        a, b = oriented
        p0 = _uv_point(uv, a, size)
        p1 = _uv_point(uv, b, size)
        if len(faces) == 1:
            draw.line((*p0, *p1), fill=(130, 130, 130, 70), width=1)
            continue
        if len(faces) >= 2 and _dot(normals[faces[0][0]], normals[faces[1][0]]) < crease_threshold:
            draw.line((*p0, *p1), fill=(92, 92, 92, 90), width=2)


def _draw_uv_wire(draw: ImageDraw.ImageDraw, payload: dict[str, Any], size: int) -> None:
    uv = payload["uv"]

    def draw_tri(a: int, b: int, c: int) -> None:
        ax, ay = _uv_point(uv, a, size)
        bx, by = _uv_point(uv, b, size)
        cx, cy = _uv_point(uv, c, size)
        draw.line((ax, ay, bx, by), fill=(15, 56, 122, 180), width=1)
        draw.line((bx, by, cx, cy), fill=(15, 56, 122, 180), width=1)
        draw.line((cx, cy, ax, ay), fill=(15, 56, 122, 180), width=1)

    for tri in _triangle_indices(payload):
        draw_tri(tri[0], tri[1], tri[2])


def _draw_ai_uv_wire(draw: ImageDraw.ImageDraw, payload: dict[str, Any], size: int) -> None:
    uv = payload["uv"]
    for tri in _triangle_indices(payload):
        points = [_uv_point(uv, tri[0], size), _uv_point(uv, tri[1], size), _uv_point(uv, tri[2], size)]
        draw.line((*points[0], *points[1]), fill=(154, 154, 154, 86), width=1)
        draw.line((*points[1], *points[2]), fill=(154, 154, 154, 86), width=1)
        draw.line((*points[2], *points[0]), fill=(154, 154, 154, 86), width=1)


def _draw_guide_structure(draw: ImageDraw.ImageDraw, part: str, contract: dict[str, Any], *, ai_reference: bool) -> None:
    margin_range = contract.get("seam_safe_margin_percent") or [3, 5]
    margin_percent = int(sum(margin_range) / max(len(margin_range), 1))
    margin_px = int(GUIDE_SIZE * margin_percent / 100)
    if margin_px > 0:
        if ai_reference:
            draw.rectangle((0, 0, GUIDE_SIZE - 1, GUIDE_SIZE - 1), outline=(170, 170, 170, 70), width=1)
            inner = (margin_px, margin_px, GUIDE_SIZE - margin_px, GUIDE_SIZE - margin_px)
            draw.rectangle(inner, outline=(190, 190, 190, 70), width=1)
        else:
            draw.rectangle((0, 0, GUIDE_SIZE - 1, GUIDE_SIZE - 1), outline=(64, 105, 168, 180), width=2)
            inner = (margin_px, margin_px, GUIDE_SIZE - margin_px, GUIDE_SIZE - margin_px)
            draw.rectangle((0, 0, GUIDE_SIZE - 1, margin_px), fill=(225, 235, 249, 180))
            draw.rectangle((0, GUIDE_SIZE - margin_px, GUIDE_SIZE - 1, GUIDE_SIZE - 1), fill=(225, 235, 249, 180))
            draw.rectangle((0, margin_px, margin_px, GUIDE_SIZE - margin_px), fill=(225, 235, 249, 180))
            draw.rectangle((GUIDE_SIZE - margin_px, margin_px, GUIDE_SIZE - 1, GUIDE_SIZE - margin_px), fill=(225, 235, 249, 180))
            draw.rectangle(inner, outline=(93, 143, 209, 160), width=2)

    focus_box = PRIMARY_ZONE_BOXES.get(part, (0.26, 0.18, 0.74, 0.82))
    if ai_reference:
        draw.rounded_rectangle(
            _normalized_box(focus_box, GUIDE_SIZE),
            radius=28,
            outline=(150, 150, 150, 55),
            fill=(235, 235, 235, 18),
            width=1,
        )
        _dashed_vertical(
            draw,
            GUIDE_SIZE // 2,
            0,
            GUIDE_SIZE,
            dash=22,
            gap=16,
            fill=(120, 120, 120, 45),
            width=1,
        )
    else:
        draw.rounded_rectangle(
            _normalized_box(focus_box, GUIDE_SIZE),
            radius=28,
            outline=(246, 155, 26, 210),
            fill=(250, 215, 171, 44),
            width=3,
        )
        _dashed_vertical(
            draw,
            GUIDE_SIZE // 2,
            0,
            GUIDE_SIZE,
            dash=22,
            gap=16,
            fill=(46, 120, 220, 180),
            width=3,
        )


def build_uv_guide_metadata(
    *,
    part: str,
    module: dict[str, Any] | None,
    contract: dict[str, Any],
    session_root: Path,
    repo_root: Path | None = None,
    guide_profile: GuideProfile = "debug",
) -> dict[str, Any]:
    mesh_path = resolve_mesh_asset_path(part, module, repo_root=repo_root)
    mesh_bytes = mesh_path.read_bytes()
    mesh_hash = _hash_bytes(mesh_bytes)
    payload = load_mesh_payload(mesh_path)
    semantic_summary = analyze_uv_semantics(payload)
    semantic_hash = _semantic_hash(semantic_summary)
    contract_hash = _contract_hash(contract)
    algorithm_version = _guide_algorithm_version(guide_profile)
    guide_hash = _hash_bytes(f"{algorithm_version}:{mesh_hash}:{contract_hash}:{semantic_hash}".encode("utf-8"))
    guide_path = _cache_path(session_root, part, mesh_hash, contract_hash, semantic_hash, guide_profile)
    return {
        "part": part,
        "guide_profile": guide_profile,
        "mesh_path": str(mesh_path),
        "mesh_hash": mesh_hash,
        "contract_hash": contract_hash,
        "semantic_hash": semantic_hash,
        "guide_hash": guide_hash,
        "guide_algorithm_version": algorithm_version,
        "cache_key": guide_path.stem,
        "path": str(guide_path),
        "exists": guide_path.exists(),
        "semantic_summary": semantic_summary,
    }


def ensure_uv_guide_image(
    *,
    part: str,
    module: dict[str, Any] | None,
    contract: dict[str, Any],
    session_root: Path,
    repo_root: Path | None = None,
    write_image: bool = True,
    guide_profile: GuideProfile = "debug",
) -> dict[str, Any]:
    info = build_uv_guide_metadata(
        part=part,
        module=module,
        contract=contract,
        session_root=session_root,
        repo_root=repo_root,
        guide_profile=guide_profile,
    )
    guide_path = Path(info["path"])
    if not write_image:
        return info
    if guide_path.exists():
        return {**info, "exists": True, "created": False}

    payload = load_mesh_payload(Path(info["mesh_path"]))
    guide_path.parent.mkdir(parents=True, exist_ok=True)
    if guide_profile == "debug":
        background = (248, 251, 255, 255)
    elif guide_profile == "topology_mask":
        background = (128, 128, 128, 255)
    else:
        background = (250, 250, 250, 255)
    image = Image.new("RGBA", (GUIDE_SIZE, GUIDE_SIZE), background)
    draw = ImageDraw.Draw(image, "RGBA")

    if guide_profile == "topology_mask":
        _draw_topology_occupancy_mask(draw, payload, GUIDE_SIZE)
        image = image.filter(ImageFilter.GaussianBlur(radius=18.0))
        neutral = Image.new("RGBA", (GUIDE_SIZE, GUIDE_SIZE), (128, 128, 128, 255))
        image = Image.blend(image, neutral, alpha=0.56)
    elif guide_profile == "ai_reference":
        _draw_ai_semantic_fills(draw, payload, GUIDE_SIZE)
        _draw_guide_structure(draw, part, contract, ai_reference=True)
        _draw_ai_fold_and_boundary_edges(draw, payload, GUIDE_SIZE)
    else:
        _draw_guide_structure(draw, part, contract, ai_reference=False)
        _draw_semantic_fills(draw, payload, GUIDE_SIZE)
        _draw_fold_and_boundary_edges(draw, payload, GUIDE_SIZE)
        _draw_uv_wire(draw, payload, GUIDE_SIZE)

    image.save(guide_path, format="PNG")
    return {**info, "exists": True, "created": True}


def serialize_uv_guide(info: dict[str, Any]) -> dict[str, Any]:
    return {
        "part": info["part"],
        "guide_profile": info.get("guide_profile", "debug"),
        "mesh_hash": info["mesh_hash"],
        "contract_hash": info["contract_hash"],
        "semantic_hash": info["semantic_hash"],
        "guide_hash": info["guide_hash"],
        "guide_algorithm_version": info["guide_algorithm_version"],
        "cache_key": info["cache_key"],
        "path": info["path"],
        "semantic_summary": info["semantic_summary"],
    }


def resolve_uv_guide_contract(contract: Any) -> dict[str, Any]:
    if isinstance(contract, dict):
        return contract
    return serialize_uv_contract(contract)
