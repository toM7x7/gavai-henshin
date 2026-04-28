"""Pure-Python quality gates for armor model assets.

This is intentionally a read-only gate. It tells Web Forge, Quest, and later
GLB/PlayCanvas/Unity adapters whether the current model assets are safe to use
as final texture targets, without trying to repair authoring data at runtime.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Sequence

from .armor_fit_contract import ARMOR_SLOT_SPECS, normalize_slot_id
from .validators import load_json


ARMOR_MODEL_QUALITY_SCHEMA_VERSION = "model-quality-gate.v1"
MODEL_QUALITY_BLOCKING_GATE = "mesh_fit_before_texture_final"
DEFAULT_MESH_ASSET_DIR = Path("viewer/assets/meshes")
P0_MODEL_PARTS: tuple[str, ...] = (
    "helmet",
    "chest",
    "back",
    "left_shoulder",
    "right_shoulder",
)
_STATUS_RANK = {"pass": 0, "warn": 1, "fail": 2}


def audit_mesh_payload(
    part: str,
    payload: dict[str, Any],
    *,
    path: str | Path | None = None,
    required: bool = True,
) -> dict[str, Any]:
    """Audit one in-memory mesh.v1 payload."""

    reasons: list[str] = []
    warnings: list[str] = []
    checks = {
        "format_mesh_v1": False,
        "positions": False,
        "normals": False,
        "uv": False,
        "uv_range": False,
        "indices": False,
        "index_range": False,
        "non_degenerate_triangles": False,
        "explicit_bounds": False,
        "bounds": False,
        "bounds_non_zero": False,
        "body_fit_slot_resolved": False,
    }
    body_fit_slot_id = None
    runtime_part_id = None

    try:
        body_fit_slot_id = normalize_slot_id(part)
        runtime_part_id = ARMOR_SLOT_SPECS[body_fit_slot_id].runtime_part_id
        checks["body_fit_slot_resolved"] = True
    except ValueError:
        message = f"{part}: cannot resolve body-fit slot"
        if required:
            reasons.append(message)
        else:
            warnings.append(message)

    if payload.get("format") == "mesh.v1":
        checks["format_mesh_v1"] = True
    else:
        reasons.append(f"{part}: format must be mesh.v1")

    positions = payload.get("positions")
    vertex_count = 0
    computed_bounds = None
    if _is_number_list(positions) and len(positions) >= 9 and len(positions) % 3 == 0:
        checks["positions"] = True
        vertex_count = len(positions) // 3
        computed_bounds = _position_bounds(positions)
    else:
        reasons.append(f"{part}: positions missing or invalid")

    normals = payload.get("normals")
    if _is_number_list(normals) and vertex_count and len(normals) == vertex_count * 3:
        checks["normals"] = True
        invalid_normals = _invalid_normal_count(normals)
        if invalid_normals:
            reasons.append(f"{part}: normals must be unit-length vectors ({invalid_normals} invalid)")
    else:
        reasons.append(f"{part}: normals missing or invalid")

    uv = payload.get("uv")
    uv_key = "uv"
    if uv is None and "uvs" in payload:
        uv = payload.get("uvs")
        uv_key = "uvs"
    uv_count = 0
    if _is_number_list(uv) and len(uv) >= 6 and len(uv) % 2 == 0:
        checks["uv"] = True
        uv_count = len(uv) // 2
        if vertex_count and uv_count != vertex_count:
            reasons.append(f"{part}: uv count must match vertex count")
        if all(0 <= float(value) <= 1 for value in uv):
            checks["uv_range"] = True
        else:
            reasons.append(f"{part}: uv values must stay inside 0..1")
    else:
        reasons.append(f"{part}: uv missing or invalid")

    indices = payload.get("indices")
    triangle_count = 0
    if _is_index_list(indices) and len(indices) >= 3 and len(indices) % 3 == 0:
        checks["indices"] = True
        triangle_count = len(indices) // 3
        if vertex_count and max(indices) >= vertex_count:
            reasons.append(f"{part}: indices reference vertices outside positions")
        elif vertex_count:
            checks["index_range"] = True
            degenerate_count = _degenerate_triangle_count(positions, indices) if checks["positions"] else 0
            if degenerate_count:
                reasons.append(f"{part}: contains degenerate triangles ({degenerate_count})")
            else:
                checks["non_degenerate_triangles"] = True
    else:
        reasons.append(f"{part}: indices missing or invalid")

    bounds = payload.get("bounds")
    bounds_dimensions = _bounds_dimensions(bounds)
    if bounds_dimensions is not None:
        checks["explicit_bounds"] = True
        checks["bounds"] = True
        if all(dimension > 0 for dimension in bounds_dimensions):
            checks["bounds_non_zero"] = True
        else:
            reasons.append(f"{part}: bounds must be non-zero on every axis")
    else:
        reasons.append(f"{part}: bounds missing or invalid")

    status = _status_from(reasons, warnings)
    if not reasons and not warnings:
        reasons.append(f"{part}: mesh.v1 quality gate passed")

    return {
        "part": part,
        "path": None if path is None else str(path),
        "status": status,
        "ok": status != "fail",
        "required": bool(required),
        "reasons": reasons + warnings,
        "body_fit_slot_id": body_fit_slot_id,
        "runtime_part_id": runtime_part_id,
        "checks": checks,
        "metrics": {
            "vertex_count": vertex_count,
            "uv_count": uv_count,
            "triangle_count": triangle_count,
            "bounds_dimensions": bounds_dimensions,
            "computed_bounds": computed_bounds,
            "uv_key": uv_key if checks["uv"] else None,
        },
    }


def audit_mesh_file(
    part: str,
    path: str | Path,
    *,
    required: bool = True,
) -> dict[str, Any]:
    """Audit one mesh.v1 JSON file without raising for quality failures."""

    mesh_path = Path(path)
    if not mesh_path.exists():
        return _missing_part_result(part, mesh_path, required=required)
    try:
        payload = load_json(mesh_path)
    except Exception as exc:  # noqa: BLE001
        status = "fail" if required else "warn"
        return {
            "part": part,
            "path": str(mesh_path),
            "status": status,
            "ok": status != "fail",
            "required": bool(required),
            "reasons": [f"{part}: unreadable mesh asset: {exc}"],
            "body_fit_slot_id": None,
            "runtime_part_id": None,
            "checks": {},
            "metrics": {},
        }
    return audit_mesh_payload(part, payload, path=mesh_path, required=required)


def audit_viewer_mesh_assets(
    repo_root: str | Path = ".",
    *,
    mesh_dir: str | Path = DEFAULT_MESH_ASSET_DIR,
    required_parts: Iterable[str] = P0_MODEL_PARTS,
    include_extra: bool = False,
) -> dict[str, Any]:
    """Audit mesh assets under viewer/assets/meshes for the required P0 parts."""

    root = Path(repo_root)
    mesh_root = Path(mesh_dir)
    if not mesh_root.is_absolute():
        mesh_root = root / mesh_root
    mesh_root = mesh_root.resolve()

    required = _unique_parts(required_parts)
    parts_to_check = list(required)
    if include_extra and mesh_root.exists():
        for mesh_path in sorted(mesh_root.glob("*.mesh.json")):
            part = mesh_path.name[: -len(".mesh.json")]
            if part not in parts_to_check:
                parts_to_check.append(part)

    part_results: dict[str, dict[str, Any]] = {}
    for part in parts_to_check:
        path = mesh_root / f"{part}.mesh.json"
        part_results[part] = audit_mesh_file(part, path, required=part in required)

    missing_required = [
        part for part in required if part_results[part]["status"] == "fail" and not Path(part_results[part]["path"]).exists()
    ]
    status = _aggregate_status(part_results.values())
    reasons = _aggregate_reasons(part_results.values())
    if not reasons:
        reasons.append("mesh.v1 P0 quality gate passed")

    return {
        "contract_version": ARMOR_MODEL_QUALITY_SCHEMA_VERSION,
        "schema_version": ARMOR_MODEL_QUALITY_SCHEMA_VERSION,
        "blocking_gate": MODEL_QUALITY_BLOCKING_GATE,
        "gate": "mesh.v1.p0",
        "status": status,
        "ok": status != "fail",
        "mesh_assets_ready": status == "pass",
        "texture_lock_allowed": status == "pass",
        "repo_root": str(root.resolve()),
        "mesh_dir": str(mesh_root),
        "p0_parts": required,
        "required_parts": required,
        "present_parts": [
            part for part in required if part_results[part]["status"] != "fail" or Path(part_results[part]["path"]).exists()
        ],
        "missing_required_parts": missing_required,
        "reasons": reasons,
        "summary": _summary(part_results.values(), required),
        "parts": part_results,
    }


def _missing_part_result(part: str, path: Path, *, required: bool) -> dict[str, Any]:
    status = "fail" if required else "warn"
    return {
        "part": part,
        "path": str(path),
        "status": status,
        "ok": status != "fail",
        "required": bool(required),
        "reasons": [f"{part}: required mesh asset missing" if required else f"{part}: mesh asset missing"],
        "body_fit_slot_id": None,
        "runtime_part_id": None,
        "checks": {
            "format_mesh_v1": False,
            "positions": False,
            "normals": False,
            "uv": False,
            "uv_range": False,
            "indices": False,
            "index_range": False,
            "non_degenerate_triangles": False,
            "explicit_bounds": False,
            "bounds": False,
            "bounds_non_zero": False,
            "body_fit_slot_resolved": False,
        },
        "metrics": {},
    }


def _aggregate_status(results: Iterable[dict[str, Any]]) -> str:
    status = "pass"
    for result in results:
        current = str(result.get("status") or "fail")
        if _STATUS_RANK.get(current, 2) > _STATUS_RANK[status]:
            status = current
    return status


def _aggregate_reasons(results: Iterable[dict[str, Any]]) -> list[str]:
    reasons: list[str] = []
    for result in results:
        if result.get("status") == "pass":
            continue
        reasons.extend(str(reason) for reason in result.get("reasons") or [])
    return reasons


def _summary(results: Iterable[dict[str, Any]], required_parts: Sequence[str]) -> dict[str, Any]:
    result_list = list(results)
    status_counts = {"pass": 0, "warn": 0, "fail": 0}
    for result in result_list:
        status = str(result.get("status") or "fail")
        status_counts[status if status in status_counts else "fail"] += 1
    return {
        "required_count": len(required_parts),
        "checked_count": len(result_list),
        "pass_count": status_counts["pass"],
        "warn_count": status_counts["warn"],
        "fail_count": status_counts["fail"],
        "required_pass_count": sum(
            1 for result in result_list if result.get("part") in required_parts and result.get("status") == "pass"
        ),
    }


def _position_bounds(positions: list[int | float]) -> dict[str, list[float]]:
    xs = [float(positions[index]) for index in range(0, len(positions), 3)]
    ys = [float(positions[index]) for index in range(1, len(positions), 3)]
    zs = [float(positions[index]) for index in range(2, len(positions), 3)]
    return {
        "min": [min(xs), min(ys), min(zs)],
        "max": [max(xs), max(ys), max(zs)],
        "size": [max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)],
    }


def _invalid_normal_count(normals: list[int | float]) -> int:
    invalid = 0
    for index in range(0, len(normals), 3):
        x = float(normals[index])
        y = float(normals[index + 1])
        z = float(normals[index + 2])
        length_sq = x * x + y * y + z * z
        if not 0.64 <= length_sq <= 1.44:
            invalid += 1
    return invalid


def _degenerate_triangle_count(positions: list[int | float] | None, indices: list[int]) -> int:
    if not positions:
        return 0
    degenerate = 0
    for index in range(0, len(indices), 3):
        a = _vertex(positions, indices[index])
        b = _vertex(positions, indices[index + 1])
        c = _vertex(positions, indices[index + 2])
        ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        ac = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
        cross = (
            ab[1] * ac[2] - ab[2] * ac[1],
            ab[2] * ac[0] - ab[0] * ac[2],
            ab[0] * ac[1] - ab[1] * ac[0],
        )
        area_sq = cross[0] * cross[0] + cross[1] * cross[1] + cross[2] * cross[2]
        if area_sq <= 1e-12:
            degenerate += 1
    return degenerate


def _vertex(positions: list[int | float], vertex_index: int) -> tuple[float, float, float]:
    offset = vertex_index * 3
    return (float(positions[offset]), float(positions[offset + 1]), float(positions[offset + 2]))


def _bounds_dimensions(bounds: Any) -> list[float] | None:
    if isinstance(bounds, dict):
        size = bounds.get("size") or bounds.get("extent") or bounds.get("extents")
        if _is_number_list(size) and len(size) == 3:
            return [abs(float(value)) for value in size]
        minimum = bounds.get("min") or bounds.get("minimum")
        maximum = bounds.get("max") or bounds.get("maximum")
        if _is_number_list(minimum) and _is_number_list(maximum) and len(minimum) == 3 and len(maximum) == 3:
            return [abs(float(maximum[index]) - float(minimum[index])) for index in range(3)]
        return None
    if _is_number_list(bounds) and len(bounds) == 6:
        return [abs(float(bounds[index + 3]) - float(bounds[index])) for index in range(3)]
    if isinstance(bounds, Sequence) and len(bounds) == 2:
        minimum, maximum = bounds
        if _is_number_list(minimum) and _is_number_list(maximum) and len(minimum) == 3 and len(maximum) == 3:
            return [abs(float(maximum[index]) - float(minimum[index])) for index in range(3)]
    return None


def _is_number_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in value)


def _is_index_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, int) and not isinstance(item, bool) and item >= 0 for item in value)


def _status_from(reasons: list[str], warnings: list[str]) -> str:
    if reasons:
        return "fail"
    if warnings:
        return "warn"
    return "pass"


def _unique_parts(parts: Iterable[str]) -> list[str]:
    unique = []
    seen = set()
    for part in parts:
        token = str(part).strip()
        if token and token not in seen:
            seen.add(token)
            unique.append(token)
    return unique


__all__ = [
    "ARMOR_MODEL_QUALITY_SCHEMA_VERSION",
    "DEFAULT_MESH_ASSET_DIR",
    "MODEL_QUALITY_BLOCKING_GATE",
    "P0_MODEL_PARTS",
    "audit_mesh_file",
    "audit_mesh_payload",
    "audit_viewer_mesh_assets",
]
