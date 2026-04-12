"""Generate cached UV guide images from mesh.v1 assets and UV contracts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from .mesh_assets import load_mesh_payload, resolve_mesh_asset_path
from .uv_contracts import serialize_uv_contract


GUIDE_SIZE = 1024

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


def _cache_path(session_root: Path, part: str, mesh_hash: str, contract_hash: str) -> Path:
    return session_root / "_cache" / "uv-guides" / f"{part}__{mesh_hash}__{contract_hash}.png"


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


def _draw_uv_wire(draw: ImageDraw.ImageDraw, payload: dict[str, Any], size: int) -> None:
    uv = payload["uv"]
    indices = payload.get("indices") or []

    def draw_tri(a: int, b: int, c: int) -> None:
        ax, ay = _uv_point(uv, a, size)
        bx, by = _uv_point(uv, b, size)
        cx, cy = _uv_point(uv, c, size)
        draw.line((ax, ay, bx, by), fill=(15, 56, 122, 180), width=1)
        draw.line((bx, by, cx, cy), fill=(15, 56, 122, 180), width=1)
        draw.line((cx, cy, ax, ay), fill=(15, 56, 122, 180), width=1)

    if indices:
        for i in range(0, len(indices), 3):
            draw_tri(indices[i], indices[i + 1], indices[i + 2])
    else:
        count = len(uv) // 2
        for i in range(0, count, 3):
            draw_tri(i, i + 1, i + 2)


def build_uv_guide_metadata(
    *,
    part: str,
    module: dict[str, Any] | None,
    contract: dict[str, Any],
    session_root: Path,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    mesh_path = resolve_mesh_asset_path(part, module, repo_root=repo_root)
    mesh_hash = _hash_bytes(mesh_path.read_bytes())
    contract_hash = _contract_hash(contract)
    guide_hash = _hash_bytes(f"{mesh_hash}:{contract_hash}".encode("utf-8"))
    guide_path = _cache_path(session_root, part, mesh_hash, contract_hash)
    return {
        "part": part,
        "mesh_path": str(mesh_path),
        "mesh_hash": mesh_hash,
        "contract_hash": contract_hash,
        "guide_hash": guide_hash,
        "cache_key": guide_path.stem,
        "path": str(guide_path),
        "exists": guide_path.exists(),
    }


def ensure_uv_guide_image(
    *,
    part: str,
    module: dict[str, Any] | None,
    contract: dict[str, Any],
    session_root: Path,
    repo_root: Path | None = None,
    write_image: bool = True,
) -> dict[str, Any]:
    info = build_uv_guide_metadata(
        part=part,
        module=module,
        contract=contract,
        session_root=session_root,
        repo_root=repo_root,
    )
    guide_path = Path(info["path"])
    if not write_image:
        return info
    if guide_path.exists():
        return {**info, "exists": True, "created": False}

    payload = load_mesh_payload(Path(info["mesh_path"]))
    guide_path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGBA", (GUIDE_SIZE, GUIDE_SIZE), (248, 251, 255, 255))
    draw = ImageDraw.Draw(image, "RGBA")

    margin_range = contract.get("seam_safe_margin_percent") or [3, 5]
    margin_percent = int(sum(margin_range) / max(len(margin_range), 1))
    margin_px = int(GUIDE_SIZE * margin_percent / 100)
    if margin_px > 0:
        draw.rectangle((0, 0, GUIDE_SIZE - 1, GUIDE_SIZE - 1), outline=(64, 105, 168, 180), width=2)
        inner = (margin_px, margin_px, GUIDE_SIZE - margin_px, GUIDE_SIZE - margin_px)
        draw.rectangle((0, 0, GUIDE_SIZE - 1, margin_px), fill=(225, 235, 249, 180))
        draw.rectangle((0, GUIDE_SIZE - margin_px, GUIDE_SIZE - 1, GUIDE_SIZE - 1), fill=(225, 235, 249, 180))
        draw.rectangle((0, margin_px, margin_px, GUIDE_SIZE - margin_px), fill=(225, 235, 249, 180))
        draw.rectangle((GUIDE_SIZE - margin_px, margin_px, GUIDE_SIZE - 1, GUIDE_SIZE - margin_px), fill=(225, 235, 249, 180))
        draw.rectangle(inner, outline=(93, 143, 209, 160), width=2)

    focus_box = PRIMARY_ZONE_BOXES.get(part, (0.26, 0.18, 0.74, 0.82))
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
    _draw_uv_wire(draw, payload, GUIDE_SIZE)

    image.save(guide_path, format="PNG")
    return {**info, "exists": True, "created": True}


def serialize_uv_guide(info: dict[str, Any]) -> dict[str, Any]:
    return {
        "part": info["part"],
        "mesh_hash": info["mesh_hash"],
        "contract_hash": info["contract_hash"],
        "guide_hash": info["guide_hash"],
        "cache_key": info["cache_key"],
        "path": info["path"],
    }


def resolve_uv_guide_contract(contract: Any) -> dict[str, Any]:
    if isinstance(contract, dict):
        return contract
    return serialize_uv_contract(contract)
