"""Lightweight validation for modeler-delivered armor part assets."""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from henshin.armor_fit_contract import ARMOR_SLOT_SPECS, MIRROR_SLOT_PAIRS, normalize_slot_id  # noqa: E402
from henshin import modeler_blueprints as blueprints  # noqa: E402


DEFAULT_ARMOR_PARTS_DIR = Path("viewer/assets/armor-parts")
SIDECAR_CONTRACT_VERSION = "modeler-part-sidecar.v1"
GLB_MAGIC = b"glTF"
GLB_VERSION = 2
GLB_JSON_CHUNK_TYPE = 0x4E4F534A
DEFAULT_EXPECTED_PARTS = (
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
EXPECTED_PARTS = DEFAULT_EXPECTED_PARTS
AXES = ("x", "y", "z")
BBOX_PASS_TOLERANCE_RATIO = 0.10
BBOX_FAIL_TOLERANCE_RATIO = 0.15
MIRROR_PAIR_WARN_TOLERANCE_RATIO = 0.03
MIRROR_PAIR_FAIL_TOLERANCE_RATIO = 0.05
OFFSET_HARD_FAIL_TOLERANCE_M = 0.30
ATTACHMENT_OFFSET_TARGET_BY_MODULE = {
    "helmet": 0.08,
    "chest": 0.08,
    "back": 0.08,
    "waist": 0.06,
    "left_shoulder": 0.04,
    "right_shoulder": 0.04,
    "left_upperarm": 0.04,
    "right_upperarm": 0.04,
    "left_forearm": 0.04,
    "right_forearm": 0.04,
    "left_shin": 0.04,
    "right_shin": 0.04,
    "left_boot": 0.06,
    "right_boot": 0.06,
}
P0_METADATA_MODULES = (
    "helmet",
    "chest",
    "back",
    "waist",
    "left_shoulder",
    "right_shoulder",
    "left_shin",
    "right_shin",
)
P0_REQUIRED_TOPPING_SLOTS = {
    "helmet": ("crest", "visor_trim"),
    "chest": ("chest_core", "rib_trim"),
    "back": ("spine_ridge", "rear_core"),
    "waist": ("belt_buckle", "side_clip"),
    "left_shoulder": ("shoulder_fin", "edge_trim"),
    "right_shoulder": ("shoulder_fin", "edge_trim"),
    "left_shin": ("shin_spike", "ankle_cuff_trim"),
    "right_shin": ("shin_spike", "ankle_cuff_trim"),
}


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
        sidecar_result = validate_modeler_sidecar(
            sidecar_path,
            expected_module=part,
            enforce_p0_metadata=tuple(EXPECTED_PARTS) == DEFAULT_EXPECTED_PARTS,
        )
        part_reasons = glb_result["reasons"] + sidecar_result["reasons"]
        part_warnings = glb_result["warnings"] + sidecar_result["warnings"]
        reasons.extend(part_reasons)
        warnings.extend(part_warnings)
        parts[part] = {
            "status": "fail" if part_reasons else "warn" if part_warnings else "pass",
            "glb": glb_result,
            "sidecar": sidecar_result,
        }

    mirror_checks = _mirror_pair_checks(parts)
    for check in mirror_checks:
        if check["status"] == "fail":
            reasons.append(
                f"{check['pair'][0]}/{check['pair'][1]}: mirror pair dimensions exceed "
                f"{MIRROR_PAIR_FAIL_TOLERANCE_RATIO * 100:.1f}% (max_delta={check.get('max_delta_pct')}%)"
            )
        elif check["status"] == "warn":
            warnings.append(
                f"{check['pair'][0]}/{check['pair'][1]}: mirror pair dimensions exceed "
                f"{MIRROR_PAIR_WARN_TOLERANCE_RATIO * 100:.1f}% (max_delta={check.get('max_delta_pct')}%)"
            )
        for module in check["pair"]:
            if module in parts:
                parts[module]["mirror_pair_check"] = check
                parts[module]["status"] = _merge_part_status(parts[module]["status"], check["status"])

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
        "mirror_pair_checks": mirror_checks,
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


def validate_modeler_sidecar(
    path: str | Path,
    *,
    expected_module: str,
    enforce_p0_metadata: bool = False,
) -> dict[str, Any]:
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
    else:
        bbox_gate = _bbox_target_gate(expected_module, bbox_size)
        metrics["bbox_target_gate"] = bbox_gate
        if bbox_gate["status"] == "fail":
            reasons.append(
                f"{expected_module}: bbox_m exceeds target envelope by more than "
                f"{BBOX_FAIL_TOLERANCE_RATIO * 100:.1f}% ({bbox_gate['axis_delta_pct']})"
            )
        elif bbox_gate["status"] == "warn":
            warnings.append(
                f"{expected_module}: bbox_m exceeds pass target by more than "
                f"{BBOX_PASS_TOLERANCE_RATIO * 100:.1f}% ({bbox_gate['axis_delta_pct']})"
            )

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
        primary_bone = attachment.get("primary_bone")
        if not isinstance(primary_bone, str) or not primary_bone:
            reasons.append(f"{expected_module}: sidecar vrm_attachment.primary_bone missing")
        else:
            try:
                expected_anchor = ARMOR_SLOT_SPECS[normalize_slot_id(expected_module)].body_anchor
            except ValueError:
                expected_anchor = None
            metrics["expected_primary_bone"] = expected_anchor
            if expected_anchor is not None and primary_bone != expected_anchor:
                reasons.append(
                    f"{expected_module}: sidecar vrm_attachment.primary_bone must be {expected_anchor}"
                )
        for field in ("offset_m", "rotation_deg"):
            if not _number_list(attachment.get(field), expected_len=3):
                reasons.append(f"{expected_module}: sidecar vrm_attachment.{field} must be a 3-number list")
        offset = attachment.get("offset_m")
        if _number_list(offset, expected_len=3):
            offset_gate = _attachment_offset_gate(expected_module, offset)
            metrics["attachment_offset_gate"] = offset_gate
            if offset_gate["status"] == "fail":
                reasons.append(
                    f"{expected_module}: vrm_attachment.offset_m magnitude "
                    f"{offset_gate['magnitude_m']:.4f}m exceeds hard tolerance "
                    f"{offset_gate['hard_fail_tolerance_m']:.4f}m"
                )
            elif offset_gate["status"] == "warn":
                warnings.append(
                    f"{expected_module}: vrm_attachment.offset_m magnitude "
                    f"{offset_gate['magnitude_m']:.4f}m exceeds target "
                    f"{offset_gate['target_m']:.4f}m"
                )

    p0_metadata = _p0_metadata_gate(expected_module, payload, enforce=enforce_p0_metadata)
    metrics["p0_metadata_gate"] = p0_metadata
    if p0_metadata["status"] == "fail":
        reasons.extend(f"{expected_module}: {reason}" for reason in p0_metadata["reasons"])

    return {
        "ok": not reasons,
        "path": str(sidecar_path),
        "reasons": reasons,
        "warnings": warnings,
        "metrics": metrics,
    }


def _merge_part_status(current: str, incoming: str) -> str:
    rank = {"pass": 0, "warn": 1, "fail": 2}
    return incoming if rank.get(incoming, 0) > rank.get(current, 0) else current


def _reference_target_dimensions(module: str) -> dict[str, float]:
    target = getattr(blueprints, "_reference_target_dimensions")(module)
    return {axis: float(target[axis]) for axis in AXES}


def _bbox_target_gate(module: str, bbox_size: list[float]) -> dict[str, Any]:
    target = _reference_target_dimensions(module)
    deltas = {}
    max_abs = 0.0
    for index, axis in enumerate(AXES):
        target_value = target[axis]
        delta = ((float(bbox_size[index]) - target_value) / target_value) if target_value else 0.0
        deltas[axis] = round(delta * 100, 1)
        max_abs = max(max_abs, abs(delta))
    if max_abs > BBOX_FAIL_TOLERANCE_RATIO:
        status = "fail"
    elif max_abs > BBOX_PASS_TOLERANCE_RATIO:
        status = "warn"
    else:
        status = "pass"
    return {
        "status": status,
        "bbox_m": dict(zip(AXES, bbox_size)),
        "target_bbox_m": target,
        "axis_delta_pct": deltas,
        "pass_tolerance_pct": BBOX_PASS_TOLERANCE_RATIO * 100,
        "fail_tolerance_pct": BBOX_FAIL_TOLERANCE_RATIO * 100,
    }


def _attachment_offset_gate(module: str, offset: list[Any]) -> dict[str, Any]:
    magnitude = sum(float(value) ** 2 for value in offset) ** 0.5
    target = ATTACHMENT_OFFSET_TARGET_BY_MODULE.get(module, 0.08)
    if magnitude > OFFSET_HARD_FAIL_TOLERANCE_M:
        status = "fail"
    elif magnitude > target:
        status = "warn"
    else:
        status = "pass"
    return {
        "status": status,
        "offset_m": [float(value) for value in offset],
        "magnitude_m": round(magnitude, 4),
        "target_m": target,
        "hard_fail_tolerance_m": OFFSET_HARD_FAIL_TOLERANCE_M,
    }


def _p0_metadata_gate(module: str, payload: dict[str, Any], *, enforce: bool) -> dict[str, Any]:
    if module not in P0_METADATA_MODULES:
        return {"status": "pass", "required": False, "reasons": []}
    reasons = []
    variant_key = payload.get("variant_key")
    if not isinstance(variant_key, str) or not variant_key.strip():
        reasons.append("P0 metadata `variant_key` missing")

    motif_link = payload.get("base_motif_link")
    if not isinstance(motif_link, dict):
        reasons.append("P0 metadata `base_motif_link` must be an object with name and surface_zone")
        motif_summary = None
    else:
        motif_summary = {
            "name": motif_link.get("name"),
            "surface_zone": motif_link.get("surface_zone"),
        }
        if not isinstance(motif_summary["name"], str) or not motif_summary["name"].strip():
            reasons.append("P0 metadata `base_motif_link.name` missing")
        if not isinstance(motif_summary["surface_zone"], str) or not motif_summary["surface_zone"].strip():
            reasons.append("P0 metadata `base_motif_link.surface_zone` missing")

    required_slots = P0_REQUIRED_TOPPING_SLOTS.get(module, ())
    present_slots, slot_summaries, slot_reasons = _topping_slot_metadata(payload.get("topping_slots"), module)
    reasons.extend(slot_reasons)
    if not slot_reasons and len(present_slots) < 2:
        reasons.append("P0 metadata `topping_slots` must declare at least 2 slots")
    missing_slots = [slot for slot in required_slots if slot not in present_slots]
    if missing_slots:
        reasons.append(f"P0 required topping slots missing: {missing_slots}")
    return {
        "status": "fail" if enforce and reasons else "pass",
        "required": True,
        "enforced": enforce,
        "variant_key": variant_key if isinstance(variant_key, str) else None,
        "base_motif_link": motif_summary,
        "required_topping_slots": list(required_slots),
        "declared_topping_slots": sorted(present_slots),
        "topping_slot_count": len(present_slots),
        "topping_slots": slot_summaries,
        "reasons": reasons,
    }


def _topping_slot_metadata(value: Any, module: str) -> tuple[set[str], list[dict[str, Any]], list[str]]:
    if not isinstance(value, list):
        return set(), [], ["P0 metadata `topping_slots` must be an object list"]

    present: set[str] = set()
    summaries: list[dict[str, Any]] = []
    reasons: list[str] = []
    for index, slot in enumerate(value):
        label = f"P0 metadata `topping_slots[{index}]`"
        if not isinstance(slot, dict):
            reasons.append(f"{label} must be an object")
            continue

        slot_name = slot.get("topping_slot")
        if not isinstance(slot_name, str) or not slot_name.strip():
            reasons.append(f"{label}.topping_slot missing")
            continue
        slot_name = slot_name.strip()
        present.add(slot_name)

        slot_transform = slot.get("slot_transform")
        if not isinstance(slot_transform, dict):
            reasons.append(f"{label}.slot_transform missing")
        else:
            if not _number_list(slot_transform.get("anchor"), expected_len=3):
                reasons.append(f"{label}.slot_transform.anchor must be a 3-number list")
            if not _number_list(slot_transform.get("rotation_deg"), expected_len=3):
                reasons.append(f"{label}.slot_transform.rotation_deg must be a 3-number list")

        max_bbox = slot.get("max_bbox_m")
        if not isinstance(max_bbox, dict):
            reasons.append(f"{label}.max_bbox_m missing")
        else:
            dims = [max_bbox.get(axis) for axis in AXES]
            if not _number_list(dims, expected_len=3) or not all(float(dim) > 0 for dim in dims):
                reasons.append(f"{label}.max_bbox_m must provide positive x/y/z")

        conflicts_with = slot.get("conflicts_with", [])
        if not isinstance(conflicts_with, list) or not all(isinstance(item, str) for item in conflicts_with):
            reasons.append(f"{label}.conflicts_with must be a string list")

        parent_module = slot.get("parent_module")
        if parent_module != module:
            reasons.append(f"{label}.parent_module must be {module}")

        summaries.append(
            {
                "topping_slot": slot_name,
                "parent_module": parent_module,
                "max_bbox_m": max_bbox if isinstance(max_bbox, dict) else None,
                "conflicts_with": conflicts_with if isinstance(conflicts_with, list) else [],
            }
        )
    return present, summaries, reasons


def _mirror_pair_checks(parts: dict[str, Any]) -> list[dict[str, Any]]:
    checks = []
    for left_slot, right_slot in MIRROR_SLOT_PAIRS:
        left_module = ARMOR_SLOT_SPECS[left_slot].runtime_part_id
        right_module = ARMOR_SLOT_SPECS[right_slot].runtime_part_id
        if left_module not in parts and right_module not in parts:
            continue
        left_bbox = _part_bbox_metric(parts.get(left_module))
        right_bbox = _part_bbox_metric(parts.get(right_module))
        check = {
            "pair": [left_module, right_module],
            "left_bbox_m": left_bbox,
            "right_bbox_m": right_bbox,
            "warn_tolerance_pct": MIRROR_PAIR_WARN_TOLERANCE_RATIO * 100,
            "fail_tolerance_pct": MIRROR_PAIR_FAIL_TOLERANCE_RATIO * 100,
        }
        if left_bbox is None or right_bbox is None:
            checks.append({**check, "status": "fail", "reason": "missing bbox for mirror comparison"})
            continue
        axis_delta_pct = {}
        max_delta = 0.0
        for axis in AXES:
            denom = max(abs(left_bbox[axis]), abs(right_bbox[axis]), 1e-9)
            delta = abs(left_bbox[axis] - right_bbox[axis]) / denom
            axis_delta_pct[axis] = round(delta * 100, 2)
            max_delta = max(max_delta, delta)
        if max_delta > MIRROR_PAIR_FAIL_TOLERANCE_RATIO:
            status = "fail"
        elif max_delta > MIRROR_PAIR_WARN_TOLERANCE_RATIO:
            status = "warn"
        else:
            status = "pass"
        checks.append(
            {
                **check,
                "status": status,
                "axis_delta_pct": axis_delta_pct,
                "max_delta_pct": round(max_delta * 100, 2),
            }
        )
    return checks


def _part_bbox_metric(part: Any) -> dict[str, float] | None:
    if not isinstance(part, dict):
        return None
    bbox = part.get("sidecar", {}).get("metrics", {}).get("bbox_size_m")
    if _number_list(bbox, expected_len=3):
        return {axis: float(bbox[index]) for index, axis in enumerate(AXES)}
    return None


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
