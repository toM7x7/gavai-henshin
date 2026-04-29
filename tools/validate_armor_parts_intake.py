"""Lightweight validation for modeler-delivered armor part assets."""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path
from typing import Any


DEFAULT_ARMOR_PARTS_DIR = Path("viewer/assets/armor-parts")
SIDECAR_CONTRACT_VERSION = "modeler-part-sidecar.v1"
GLB_MAGIC = b"glTF"
GLB_VERSION = 2
GLB_JSON_CHUNK_TYPE = 0x4E4F534A
EXPECTED_PARTS = (
    "helmet",
    "chest",
    "back",
    "waist",
    "left_shoulder",
    "right_shoulder",
    "left_upperarm",
    "right_upperarm",
    "left_forearm",
    "right_forearm",
    "left_hand",
    "right_hand",
    "left_thigh",
    "right_thigh",
    "left_shin",
    "right_shin",
    "left_boot",
    "right_boot",
)


def validate_armor_parts(root: str | Path = DEFAULT_ARMOR_PARTS_DIR) -> dict[str, Any]:
    """Validate delivered armor GLBs and modeler sidecars without loading meshes."""

    armor_root = Path(root)
    reasons: list[str] = []
    warnings: list[str] = []
    parts: dict[str, Any] = {}

    if not armor_root.exists():
        return {
            "ok": False,
            "status": "fail",
            "root": str(armor_root),
            "part_count": 0,
            "present_parts": [],
            "missing_parts": list(EXPECTED_PARTS),
            "reasons": [f"armor parts directory missing: {armor_root}"],
            "warnings": [],
            "parts": {},
        }

    blend1_files = sorted(armor_root.rglob("*.blend1"))
    for blend1_path in blend1_files:
        reasons.append(f"backup file must not be committed: {blend1_path.as_posix()}")

    module_dirs = [
        path
        for path in sorted(armor_root.iterdir())
        if path.is_dir() and not path.name.startswith("_") and (path / f"{path.name}.glb").exists()
    ]
    present_part_names = [path.name for path in module_dirs]
    missing_parts = [part for part in EXPECTED_PARTS if part not in present_part_names]
    for part in missing_parts:
        reasons.append(f"{part}: required armor part directory or GLB missing")

    extra_parts = [part for part in present_part_names if part not in EXPECTED_PARTS]
    for part in extra_parts:
        warnings.append(f"{part}: extra armor part is not in the expected delivery list")

    for module_dir in module_dirs:
        part = module_dir.name
        glb_path = module_dir / f"{part}.glb"
        sidecar_path = module_dir / f"{part}.modeler.json"
        glb_result = validate_glb_header(glb_path)
        sidecar_result = validate_modeler_sidecar(sidecar_path, expected_module=part)
        part_reasons = glb_result["reasons"] + sidecar_result["reasons"]
        part_warnings = glb_result["warnings"] + sidecar_result["warnings"]
        reasons.extend(part_reasons)
        warnings.extend(part_warnings)
        parts[part] = {
            "status": "fail" if part_reasons else "warn" if part_warnings else "pass",
            "glb": glb_result,
            "sidecar": sidecar_result,
        }

    status = "fail" if reasons else "warn" if warnings else "pass"
    return {
        "ok": status != "fail",
        "status": status,
        "root": str(armor_root),
        "part_count": len(present_part_names),
        "present_parts": present_part_names,
        "missing_parts": missing_parts,
        "reasons": reasons,
        "warnings": warnings,
        "parts": parts,
    }


def validate_glb_header(path: str | Path) -> dict[str, Any]:
    """Validate the GLB container header and first JSON chunk header."""

    glb_path = Path(path)
    reasons: list[str] = []
    warnings: list[str] = []
    metrics: dict[str, Any] = {}
    if not glb_path.exists():
        return {
            "ok": False,
            "path": str(glb_path),
            "reasons": [f"GLB missing: {glb_path.as_posix()}"],
            "warnings": [],
            "metrics": metrics,
        }

    data = glb_path.read_bytes()
    metrics["file_size_bytes"] = len(data)
    if len(data) < 20:
        reasons.append(f"GLB too small for header and first chunk: {glb_path.as_posix()}")
    else:
        magic, version, declared_length = struct.unpack_from("<4sII", data, 0)
        metrics.update(
            {"magic": magic.decode("ascii", errors="replace"), "version": version, "declared_length": declared_length}
        )
        if magic != GLB_MAGIC:
            reasons.append(f"GLB magic must be glTF: {glb_path.as_posix()}")
        if version != GLB_VERSION:
            reasons.append(f"GLB version must be 2: {glb_path.as_posix()}")
        if declared_length != len(data):
            reasons.append(
                f"GLB declared length must match file size: {glb_path.as_posix()} ({declared_length} != {len(data)})"
            )
        chunk_length, chunk_type = struct.unpack_from("<II", data, 12)
        metrics.update({"first_chunk_length": chunk_length, "first_chunk_type": _chunk_type_label(chunk_type)})
        if chunk_type != GLB_JSON_CHUNK_TYPE:
            reasons.append(f"GLB first chunk must be JSON: {glb_path.as_posix()}")
        if chunk_length <= 0 or 20 + chunk_length > len(data):
            reasons.append(f"GLB first chunk length is invalid: {glb_path.as_posix()}")
        else:
            try:
                gltf_json = json.loads(data[20 : 20 + chunk_length].decode("utf-8").strip(" \t\r\n\0"))
                asset_version = gltf_json.get("asset", {}).get("version") if isinstance(gltf_json, dict) else None
                metrics["asset_version"] = asset_version
                if asset_version != "2.0":
                    reasons.append(f"GLB asset.version must be 2.0: {glb_path.as_posix()}")
            except Exception as exc:  # noqa: BLE001
                reasons.append(f"GLB JSON chunk unreadable: {glb_path.as_posix()}: {exc}")

    return {
        "ok": not reasons,
        "path": str(glb_path),
        "reasons": reasons,
        "warnings": warnings,
        "metrics": metrics,
    }


def validate_modeler_sidecar(path: str | Path, *, expected_module: str) -> dict[str, Any]:
    """Validate the small sidecar fields needed before runtime integration."""

    sidecar_path = Path(path)
    reasons: list[str] = []
    warnings: list[str] = []
    metrics: dict[str, Any] = {}
    if not sidecar_path.exists():
        return {
            "ok": False,
            "path": str(sidecar_path),
            "reasons": [f"sidecar missing: {sidecar_path.as_posix()}"],
            "warnings": [],
            "metrics": metrics,
        }

    try:
        payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "path": str(sidecar_path),
            "reasons": [f"sidecar unreadable: {sidecar_path.as_posix()}: {exc}"],
            "warnings": [],
            "metrics": metrics,
        }

    if payload.get("contract_version") != SIDECAR_CONTRACT_VERSION:
        reasons.append(f"{expected_module}: sidecar contract_version must be {SIDECAR_CONTRACT_VERSION}")
    if payload.get("module") != expected_module:
        reasons.append(f"{expected_module}: sidecar module must match folder name")

    part_id = payload.get("part_id")
    if not isinstance(part_id, str) or not part_id:
        reasons.append(f"{expected_module}: sidecar part_id missing")
    elif expected_module not in part_id:
        warnings.append(f"{expected_module}: sidecar part_id does not include module name")

    bbox = payload.get("bbox_m")
    bbox_size = _bbox_size(bbox)
    metrics["bbox_size_m"] = bbox_size
    if bbox_size is None:
        reasons.append(f"{expected_module}: sidecar bbox_m must expose positive x/y/z or size")
    elif not all(value > 0 for value in bbox_size):
        reasons.append(f"{expected_module}: sidecar bbox_m dimensions must be positive")

    triangle_count = payload.get("triangle_count", payload.get("triangles"))
    metrics["triangle_count"] = triangle_count
    if not isinstance(triangle_count, int) or triangle_count <= 0:
        reasons.append(f"{expected_module}: sidecar triangle_count must be a positive integer")

    material_zones = payload.get("material_zones")
    metrics["material_zones"] = material_zones
    if not isinstance(material_zones, list) or not material_zones or not all(isinstance(zone, str) for zone in material_zones):
        reasons.append(f"{expected_module}: sidecar material_zones must be a non-empty string list")
    elif "base_surface" not in material_zones:
        warnings.append(f"{expected_module}: sidecar material_zones should include base_surface")

    if payload.get("texture_provider_profile") != "nano_banana":
        reasons.append(f"{expected_module}: sidecar texture_provider_profile must be nano_banana")

    attachment = payload.get("vrm_attachment")
    if not isinstance(attachment, dict):
        reasons.append(f"{expected_module}: sidecar vrm_attachment missing")
    else:
        if not isinstance(attachment.get("primary_bone"), str) or not attachment.get("primary_bone"):
            reasons.append(f"{expected_module}: sidecar vrm_attachment.primary_bone missing")
        for field in ("offset_m", "rotation_deg"):
            if not _number_list(attachment.get(field), expected_len=3):
                reasons.append(f"{expected_module}: sidecar vrm_attachment.{field} must be a 3-number list")

    return {
        "ok": not reasons,
        "path": str(sidecar_path),
        "reasons": reasons,
        "warnings": warnings,
        "metrics": metrics,
    }


def _bbox_size(value: Any) -> list[float] | None:
    if not isinstance(value, dict):
        return None
    size = value.get("size") or value.get("dimensions")
    if _number_list(size, expected_len=3):
        return [float(item) for item in size]
    xyz = [value.get(axis) for axis in ("x", "y", "z")]
    if _number_list(xyz, expected_len=3):
        return [float(item) for item in xyz]
    return None


def _number_list(value: Any, *, expected_len: int) -> bool:
    return (
        isinstance(value, list)
        and len(value) == expected_len
        and all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in value)
    )


def _chunk_type_label(value: int) -> str:
    try:
        return struct.pack("<I", value).decode("ascii")
    except UnicodeDecodeError:
        return f"0x{value:08x}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(DEFAULT_ARMOR_PARTS_DIR), help="armor-parts directory to validate")
    args = parser.parse_args()

    result = validate_armor_parts(Path(args.root))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
