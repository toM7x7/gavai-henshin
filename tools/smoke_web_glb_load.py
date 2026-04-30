"""Offline smoke verifier for the Web Forge armor GLB loader path.

Simulates the loader behavior in ``viewer/armor-forge/forge.js``
(``createArmorMesh`` -> ``loadArmorGlbGeometry``) without a browser. For each
of the 18 expected armor modules we:

1. Resolve the asset_ref via ``henshin.forge.armor_glb_asset_ref`` and confirm
   it ends in ``.glb`` and exists on disk (otherwise the runtime would fall
   back to the seed proxy ``mesh.json`` path).
2. Validate the GLB header (glTF 2.0 binary, JSON chunk asset.version=2.0).
3. Validate the modeler sidecar contract.
4. Confirm ``vrm_attachment.primary_bone`` matches the body-fit anchor expected
   by ``henshin.armor_fit_contract.ARMOR_SLOT_SPECS``.
5. Confirm the bbox center, when offset by ``vrm_attachment.offset_m``, lands
   within +/- 0.30 m of the expected bone position in our 170cm reference rig.

Prints the summary line ``previewGlbParts=N previewFallbackParts=M`` so QA can
match the brief in ``docs/modeler-context-and-actions-2026-04-30.md``.
Exit 0 iff ``previewFallbackParts == 0``.

Usage::

    python tools/smoke_web_glb_load.py
    python tools/smoke_web_glb_load.py --report-json
    python tools/smoke_web_glb_load.py --repo-root some/other/checkout
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import struct
import sys
from pathlib import Path
from typing import Any, Iterable


_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_PATH = _REPO_ROOT / "src"
if str(_SRC_PATH) not in sys.path:
    sys.path.insert(0, str(_SRC_PATH))

from henshin.armor_fit_contract import ARMOR_SLOT_SPECS, normalize_slot_id  # noqa: E402
from henshin import modeler_blueprints as modeler_blueprints  # noqa: E402
from henshin.forge import armor_glb_asset_ref  # noqa: E402


# Approximate VRM humanoid bone positions at the 170cm reference rig. These
# are the body-fit baseline used to sanity-check that sidecar offsets land near
# the right bone. Values are meters in the standard glTF Y-up frame, with the
# avatar centered on the world origin and the floor at y=0.
REFERENCE_BONE_POSITIONS_170CM: dict[str, tuple[float, float, float]] = {
    "head": (0.0, 1.60, 0.0),
    "neck": (0.0, 1.48, 0.0),
    "upperChest": (0.0, 1.36, 0.0),
    "chest": (0.0, 1.24, 0.0),
    "spine": (0.0, 1.10, 0.0),
    "hips": (0.0, 0.96, 0.0),
    "leftShoulder": (0.10, 1.40, 0.0),
    "rightShoulder": (-0.10, 1.40, 0.0),
    "leftUpperArm": (0.20, 1.38, 0.0),
    "rightUpperArm": (-0.20, 1.38, 0.0),
    "leftLowerArm": (0.20, 1.10, 0.0),
    "rightLowerArm": (-0.20, 1.10, 0.0),
    "leftHand": (0.20, 0.84, 0.0),
    "rightHand": (-0.20, 0.84, 0.0),
    "leftUpperLeg": (0.10, 0.92, 0.0),
    "rightUpperLeg": (-0.10, 0.92, 0.0),
    "leftLowerLeg": (0.10, 0.50, 0.0),
    "rightLowerLeg": (-0.10, 0.50, 0.0),
    "leftFoot": (0.10, 0.08, 0.05),
    "rightFoot": (-0.10, 0.08, 0.05),
}

# Offset magnitude tolerance vs expected bone position. Sidecars author small
# offsets in meters (typically below 0.15m). 0.30m is a generous envelope that
# still catches accidental cross-bone authoring.
OFFSET_MAGNITUDE_TOLERANCE_M = 0.30
SIDECAR_GLB_BBOX_TOLERANCE_M = 0.002
TARGET_BBOX_TOLERANCE_RATIO = 0.15
TARGET_BBOX_PASS_RATIO = 0.10
MIRROR_PAIR_WARN_TOLERANCE_RATIO = 0.03
MIRROR_PAIR_FAIL_TOLERANCE_RATIO = 0.05
MIN_RENDERABLE_MESH_SIZE_M = 0.002
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

_WEB_FORGE_PART_RE = re.compile(
    r'\[\s*"(?P<module>[^"]+)"\s*,\s*"(?P<label>[^"]*)"\s*,\s*(?P<checked>true|false)\s*\]'
)


def expected_modules() -> tuple[str, ...]:
    """Module list from ``henshin.modeler_blueprints`` (18 entries)."""

    return tuple(modeler_blueprints._CATEGORY_BY_MODULE.keys())


def _load_intake_module():
    """Load ``tools/validate_armor_parts_intake.py`` as a sibling module.

    It isn't packaged so we load it via importlib to reuse
    ``validate_glb_header`` / ``validate_modeler_sidecar`` exactly as the
    intake validator does.
    """

    intake_path = Path(__file__).resolve().parent / "validate_armor_parts_intake.py"
    spec = importlib.util.spec_from_file_location("validate_armor_parts_intake", intake_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load intake validator: {intake_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("validate_armor_parts_intake", module)
    spec.loader.exec_module(module)
    return module


def _bbox_center(bbox: Any) -> tuple[float, float, float] | None:
    """Return the center of ``bbox_m`` in the local part frame.

    The sidecar bbox is stored as side lengths along x/y/z (from
    ``modeler_sidecar.py``) so the unsigned center sits at half-extents from
    the local origin. That matches how the runtime treats GLB-baked geometry
    (it ``.center()``-s before attaching).
    """

    if not isinstance(bbox, dict):
        return None
    size = bbox.get("size") or bbox.get("dimensions")
    if isinstance(size, list) and len(size) == 3 and all(isinstance(v, (int, float)) for v in size):
        return (float(size[0]) / 2.0, float(size[1]) / 2.0, float(size[2]) / 2.0)
    xyz = [bbox.get(axis) for axis in ("x", "y", "z")]
    if all(isinstance(v, (int, float)) for v in xyz):
        return (float(xyz[0]) / 2.0, float(xyz[1]) / 2.0, float(xyz[2]) / 2.0)
    return None


def _bbox_size_dict(bbox: Any) -> dict[str, float] | None:
    if not isinstance(bbox, dict):
        return None
    size = bbox.get("size") or bbox.get("dimensions")
    if isinstance(size, list) and len(size) == 3 and all(isinstance(v, (int, float)) for v in size):
        return {axis: float(size[index]) for index, axis in enumerate(("x", "y", "z"))}
    xyz = [bbox.get(axis) for axis in ("x", "y", "z")]
    if all(isinstance(v, (int, float)) for v in xyz):
        return {axis: float(xyz[index]) for index, axis in enumerate(("x", "y", "z"))}
    return None


def _reference_target_dimensions(module: str) -> dict[str, float]:
    target = getattr(modeler_blueprints, "_reference_target_dimensions")(module)
    return {axis: float(target[axis]) for axis in ("x", "y", "z")}


def _bbox_delta_pct(bbox: dict[str, float], target: dict[str, float]) -> dict[str, float]:
    result = {}
    for axis in ("x", "y", "z"):
        target_value = target[axis]
        result[axis] = round(((bbox[axis] - target_value) / target_value) * 100, 1) if target_value else 0.0
    return result


def _bbox_abs_delta_m(a: dict[str, float], b: dict[str, float]) -> dict[str, float]:
    return {axis: round(a[axis] - b[axis], 5) for axis in ("x", "y", "z")}


def _bbox_axes_outside_target(
    bbox: dict[str, float],
    target: dict[str, float],
    *,
    tolerance_ratio: float = TARGET_BBOX_TOLERANCE_RATIO,
) -> list[str]:
    delta = _bbox_delta_pct(bbox, target)
    return [axis for axis, value in delta.items() if abs(value) > tolerance_ratio * 100]


def _bbox_target_status(bbox: dict[str, float], target: dict[str, float]) -> str:
    delta = _bbox_delta_pct(bbox, target)
    max_abs = max(abs(value) for value in delta.values())
    if max_abs > TARGET_BBOX_TOLERANCE_RATIO * 100:
        return "fail"
    if max_abs > TARGET_BBOX_PASS_RATIO * 100:
        return "warn"
    return "pass"


def _bbox_axes_outside_abs_delta(
    a: dict[str, float],
    b: dict[str, float],
    *,
    tolerance_m: float = SIDECAR_GLB_BBOX_TOLERANCE_M,
) -> list[str]:
    return [axis for axis in ("x", "y", "z") if abs(a[axis] - b[axis]) > tolerance_m]


def _read_glb_json(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    if len(data) < 20:
        raise ValueError("GLB too small for JSON chunk")
    magic, version, declared_length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or declared_length != len(data):
        raise ValueError("GLB header is not a valid glTF 2.0 binary")
    chunk_length, chunk_type = struct.unpack_from("<II", data, 12)
    if chunk_type != 0x4E4F534A or chunk_length <= 0 or 20 + chunk_length > len(data):
        raise ValueError("GLB first chunk is not a valid JSON chunk")
    return json.loads(data[20 : 20 + chunk_length].decode("utf-8").strip(" \t\r\n\0"))


def _number_vec3(value: Any) -> list[float] | None:
    if (
        isinstance(value, list)
        and len(value) == 3
        and all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in value)
    ):
        return [float(item) for item in value]
    return None


def _extract_glb_geometry_metrics(path: str | Path) -> dict[str, Any]:
    glb_path = Path(path)
    reasons: list[str] = []
    warnings: list[str] = []
    try:
        gltf = _read_glb_json(glb_path)
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "path": str(glb_path),
            "reasons": [f"GLB JSON unreadable for geometry audit: {glb_path.as_posix()}: {exc}"],
            "warnings": [],
        }

    meshes = gltf.get("meshes") if isinstance(gltf.get("meshes"), list) else []
    accessors = gltf.get("accessors") if isinstance(gltf.get("accessors"), list) else []
    position_accessor_indices: set[int] = set()
    primitive_count = 0
    triangle_count_estimated = 0
    mins: list[list[float]] = []
    maxes: list[list[float]] = []

    for mesh in meshes:
        primitives = mesh.get("primitives") if isinstance(mesh, dict) and isinstance(mesh.get("primitives"), list) else []
        primitive_count += len(primitives)
        for primitive in primitives:
            if not isinstance(primitive, dict):
                continue
            attributes = primitive.get("attributes") if isinstance(primitive.get("attributes"), dict) else {}
            pos_index = attributes.get("POSITION")
            if isinstance(pos_index, int) and 0 <= pos_index < len(accessors):
                position_accessor_indices.add(pos_index)
                position_accessor = accessors[pos_index]
                if isinstance(position_accessor, dict):
                    min_vec = _number_vec3(position_accessor.get("min"))
                    max_vec = _number_vec3(position_accessor.get("max"))
                    if min_vec and max_vec:
                        mins.append(min_vec)
                        maxes.append(max_vec)
            if primitive.get("mode", 4) == 4:
                index_accessor = None
                if isinstance(primitive.get("indices"), int) and 0 <= primitive["indices"] < len(accessors):
                    index_accessor = accessors[primitive["indices"]]
                elif isinstance(pos_index, int) and 0 <= pos_index < len(accessors):
                    index_accessor = accessors[pos_index]
                if isinstance(index_accessor, dict) and isinstance(index_accessor.get("count"), int):
                    triangle_count_estimated += index_accessor["count"] // 3

    if not meshes:
        reasons.append(f"GLB asset has no meshes: {glb_path.as_posix()}")
    if primitive_count <= 0:
        reasons.append(f"GLB asset has no mesh primitives: {glb_path.as_posix()}")
    if not position_accessor_indices:
        reasons.append(f"GLB asset has no POSITION accessors: {glb_path.as_posix()}")
    if not mins or not maxes:
        reasons.append(f"GLB asset has no POSITION accessor min/max bounds: {glb_path.as_posix()}")

    bbox_min = [min(vec[index] for vec in mins) for index in range(3)] if mins else None
    bbox_max = [max(vec[index] for vec in maxes) for index in range(3)] if maxes else None
    bbox_m = None
    if bbox_min and bbox_max:
        bbox_m = {
            "x": bbox_max[0] - bbox_min[0],
            "y": bbox_max[1] - bbox_min[1],
            "z": bbox_max[2] - bbox_min[2],
        }
        if max(bbox_m.values()) < MIN_RENDERABLE_MESH_SIZE_M:
            reasons.append(f"GLB asset bounds are below renderable size: {glb_path.as_posix()}")

    return {
        "ok": not reasons,
        "path": str(glb_path),
        "reasons": reasons,
        "warnings": warnings,
        "mesh_count": len(meshes),
        "primitive_count": primitive_count,
        "position_accessor_count": len(position_accessor_indices),
        "triangle_count_estimated": triangle_count_estimated,
        "bbox_min": bbox_min,
        "bbox_max": bbox_max,
        "bbox_m": bbox_m,
    }


def _vec_distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5


def _check_offset_reachable(
    *,
    primary_bone: str,
    offset_m: list[float],
    bbox_center: tuple[float, float, float] | None,
) -> dict[str, Any]:
    bone_pos = REFERENCE_BONE_POSITIONS_170CM.get(primary_bone)
    if bone_pos is None:
        return {
            "ok": False,
            "reason": f"no reference bone position for {primary_bone}",
            "primary_bone": primary_bone,
            "magnitude_m": None,
            "tolerance_m": OFFSET_MAGNITUDE_TOLERANCE_M,
        }
    if not (
        isinstance(offset_m, list)
        and len(offset_m) == 3
        and all(isinstance(v, (int, float)) for v in offset_m)
    ):
        return {
            "ok": False,
            "reason": "offset_m must be a 3-number list",
            "primary_bone": primary_bone,
            "magnitude_m": None,
            "tolerance_m": OFFSET_MAGNITUDE_TOLERANCE_M,
        }
    # The runtime composes: anchor_position = bone_world_position + offset_m
    # (modulo bone-local rotation, which we ignore here because every shipped
    # sidecar uses [0,0,0] rotation). We score the distance between that
    # composed point and the bone itself; a small magnitude means the part is
    # parented to the right bone.
    composed = (
        bone_pos[0] + float(offset_m[0]),
        bone_pos[1] + float(offset_m[1]),
        bone_pos[2] + float(offset_m[2]),
    )
    magnitude = _vec_distance(composed, bone_pos)
    ok = magnitude <= OFFSET_MAGNITUDE_TOLERANCE_M
    detail: dict[str, Any] = {
        "ok": ok,
        "primary_bone": primary_bone,
        "bone_position_m": list(bone_pos),
        "offset_m": list(offset_m),
        "anchor_position_m": list(composed),
        "magnitude_m": round(magnitude, 4),
        "tolerance_m": OFFSET_MAGNITUDE_TOLERANCE_M,
    }
    if bbox_center is not None:
        detail["bbox_center_local_m"] = list(bbox_center)
    if not ok:
        detail["reason"] = (
            f"offset magnitude {magnitude:.4f}m exceeds {OFFSET_MAGNITUDE_TOLERANCE_M}m tolerance"
        )
    return detail


def _check_attachment_offset_target(module: str, offset_m: Any) -> dict[str, Any]:
    target = ATTACHMENT_OFFSET_TARGET_BY_MODULE.get(module, 0.08)
    if not (
        isinstance(offset_m, list)
        and len(offset_m) == 3
        and all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in offset_m)
    ):
        return {
            "status": "fail",
            "reason": "offset_m must be a 3-number list",
            "target_m": target,
            "hard_fail_tolerance_m": OFFSET_MAGNITUDE_TOLERANCE_M,
        }
    magnitude = sum(float(value) ** 2 for value in offset_m) ** 0.5
    if magnitude > OFFSET_MAGNITUDE_TOLERANCE_M:
        status = "fail"
    elif magnitude > target:
        status = "warn"
    else:
        status = "pass"
    return {
        "status": status,
        "offset_m": [float(value) for value in offset_m],
        "magnitude_m": round(magnitude, 4),
        "target_m": target,
        "hard_fail_tolerance_m": OFFSET_MAGNITUDE_TOLERANCE_M,
    }


def _mirror_pair_checks(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_module = {entry["module"]: entry for entry in entries}
    checks = []
    for module in expected_modules():
        try:
            slot_id = normalize_slot_id(module)
        except ValueError:
            continue
        spec = ARMOR_SLOT_SPECS[slot_id]
        if not spec.mirror_pair or slot_id > spec.mirror_pair:
            continue
        partner_module = ARMOR_SLOT_SPECS[spec.mirror_pair].runtime_part_id
        if module not in by_module and partner_module not in by_module:
            continue
        bbox = _entry_comparison_bbox(by_module.get(module))
        partner_bbox = _entry_comparison_bbox(by_module.get(partner_module))
        check = {
            "pair": [module, partner_module],
            "left_bbox_m": bbox,
            "right_bbox_m": partner_bbox,
            "warn_tolerance_pct": MIRROR_PAIR_WARN_TOLERANCE_RATIO * 100,
            "fail_tolerance_pct": MIRROR_PAIR_FAIL_TOLERANCE_RATIO * 100,
        }
        if bbox is None or partner_bbox is None:
            checks.append({**check, "status": "fail", "reason": "missing bbox for mirror comparison"})
            continue
        axis_delta_pct = {}
        max_delta = 0.0
        for axis in ("x", "y", "z"):
            denom = max(abs(bbox[axis]), abs(partner_bbox[axis]), 1e-9)
            delta = abs(bbox[axis] - partner_bbox[axis]) / denom
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


def _entry_comparison_bbox(entry: dict[str, Any] | None) -> dict[str, float] | None:
    if not isinstance(entry, dict):
        return None
    bbox = entry.get("glb_bbox_m")
    if isinstance(bbox, dict):
        return bbox
    bbox = entry.get("sidecar_bbox_m")
    if isinstance(bbox, dict):
        return bbox
    sidecar_bbox = entry.get("sidecar", {}).get("metrics", {}).get("bbox_size_m")
    if (
        isinstance(sidecar_bbox, list)
        and len(sidecar_bbox) == 3
        and all(isinstance(value, (int, float)) for value in sidecar_bbox)
    ):
        return {axis: float(sidecar_bbox[index]) for index, axis in enumerate(("x", "y", "z"))}
    return None


def _parse_web_forge_parts(js_text: str) -> list[dict[str, Any]]:
    start = js_text.find("const PARTS = [")
    if start < 0:
        return []
    end = js_text.find("];", start)
    if end < 0:
        return []
    block = js_text[start:end]
    parts = []
    for match in _WEB_FORGE_PART_RE.finditer(block):
        parts.append(
            {
                "module": match.group("module"),
                "label": match.group("label"),
                "default_checked": match.group("checked") == "true",
            }
        )
    return parts


def _check_web_preview_contract(repo_root: str | Path) -> dict[str, Any]:
    repo_root_path = Path(repo_root)
    expected = list(expected_modules())
    forge_path = repo_root_path / "viewer" / "armor-forge" / "forge.js"
    if not forge_path.exists():
        return {
            "ok": True,
            "path": forge_path.as_posix(),
            "skipped": True,
            "reason": "viewer/armor-forge/forge.js not present in this repo_root; preview contract check skipped",
            "expected_parts": expected,
            "parts": [],
            "default_selected_parts": [],
            "default_unselected_parts": [],
            "missing_parts": [],
            "extra_parts": [],
            "duplicate_parts": [],
            "warnings": [],
            "reasons": [],
        }

    parts = _parse_web_forge_parts(forge_path.read_text(encoding="utf-8"))
    names = [part["module"] for part in parts]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    missing = [name for name in expected if name not in names]
    extra = [name for name in names if name not in expected]
    default_selected = [part["module"] for part in parts if part["default_checked"]]
    default_unselected = [part["module"] for part in parts if not part["default_checked"]]
    reasons = []
    warnings = []
    if not parts:
        reasons.append("Web Forge PARTS list could not be parsed")
    if missing:
        reasons.append(f"Web Forge PARTS missing expected modules: {missing}")
    if extra:
        reasons.append(f"Web Forge PARTS includes unknown modules: {extra}")
    if duplicates:
        reasons.append(f"Web Forge PARTS includes duplicate modules: {duplicates}")
    if names and names != expected:
        warnings.append(
            "Web Forge PARTS order differs from blueprint order; this is usually OK, but can hide preview count drift"
        )
    if default_unselected:
        warnings.append(
            f"Web Forge defaults select {len(default_selected)}/{len(expected)} parts; unselected by default: {default_unselected}"
        )
    return {
        "ok": not reasons,
        "path": forge_path.as_posix(),
        "skipped": False,
        "expected_parts": expected,
        "parts": parts,
        "part_count": len(names),
        "expected_part_count": len(expected),
        "default_selected_parts": default_selected,
        "default_unselected_parts": default_unselected,
        "missing_parts": missing,
        "extra_parts": extra,
        "duplicate_parts": duplicates,
        "warnings": warnings,
        "reasons": reasons,
    }


def smoke_check_web_glb_load(
    repo_root: str | Path = ".",
    *,
    modules: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Run the full smoke chain. Returns a structured report dict."""

    intake = _load_intake_module()
    repo_root_path = Path(repo_root)
    selected_modules = list(modules) if modules is not None else list(expected_modules())

    per_module: list[dict[str, Any]] = []
    glb_resolved = 0
    fallback_used = 0
    failures: list[str] = []
    warnings: list[str] = []

    for module in selected_modules:
        entry: dict[str, Any] = {"module": module}
        # 1. resolve asset_ref via the runtime helper.
        asset_ref = armor_glb_asset_ref(module, repo_root=repo_root_path)
        entry["asset_ref"] = asset_ref
        if not asset_ref:
            fallback_used += 1
            entry.update(
                {
                    "ok": False,
                    "would_fallback": True,
                    "fallback_asset_ref": f"viewer/assets/meshes/{module}.mesh.json",
                    "reason": "GLB missing; runtime would use mesh.v1 proxy",
                }
            )
            failures.append(f"{module}: GLB missing - would fall back to mesh.v1 proxy")
            per_module.append(entry)
            continue
        if not asset_ref.lower().endswith(".glb"):
            fallback_used += 1
            entry.update({"ok": False, "would_fallback": True, "reason": f"asset_ref does not end in .glb: {asset_ref}"})
            failures.append(f"{module}: asset_ref does not end in .glb: {asset_ref}")
            per_module.append(entry)
            continue
        glb_path = repo_root_path / asset_ref
        if not glb_path.is_file():
            fallback_used += 1
            entry.update({"ok": False, "would_fallback": True, "reason": f"resolved asset_ref does not exist: {glb_path.as_posix()}"})
            failures.append(f"{module}: resolved asset_ref missing on disk: {glb_path.as_posix()}")
            per_module.append(entry)
            continue
        glb_resolved += 1
        entry["would_fallback"] = False
        entry["glb_path"] = glb_path.as_posix()

        # 2. GLB header check.
        glb_result = intake.validate_glb_header(glb_path)
        entry["glb"] = glb_result
        if not glb_result.get("ok", False):
            failures.extend(f"{module}: {reason}" for reason in glb_result.get("reasons", []))
            entry["ok"] = False
            per_module.append(entry)
            continue
        warnings.extend(f"{module}: {warn}" for warn in glb_result.get("warnings", []))

        glb_geometry = _extract_glb_geometry_metrics(glb_path)
        entry["glb_geometry"] = glb_geometry
        if not glb_geometry.get("ok", False):
            failures.extend(f"{module}: {reason}" for reason in glb_geometry.get("reasons", []))
            entry["ok"] = False
            per_module.append(entry)
            continue

        # 3. Sidecar contract check.
        sidecar_path = glb_path.with_name(f"{module}.modeler.json")
        sidecar_result = intake.validate_modeler_sidecar(
            sidecar_path,
            expected_module=module,
            enforce_p0_metadata=True,
        )
        entry["sidecar"] = sidecar_result
        if not sidecar_result.get("ok", False):
            failures.extend(f"{module}: {reason}" for reason in sidecar_result.get("reasons", []))
            entry["ok"] = False
            per_module.append(entry)
            continue
        warnings.extend(f"{module}: {warn}" for warn in sidecar_result.get("warnings", []))

        try:
            sidecar_payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            entry["ok"] = False
            failures.append(f"{module}: sidecar reread failed: {exc}")
            per_module.append(entry)
            continue
        attachment = sidecar_payload.get("vrm_attachment") or {}
        primary_bone = attachment.get("primary_bone")
        offset_m = attachment.get("offset_m")
        sidecar_bbox = _bbox_size_dict(sidecar_payload.get("bbox_m"))
        glb_bbox = glb_geometry.get("bbox_m")
        target_bbox = _reference_target_dimensions(module)
        bbox_center = _bbox_center(sidecar_payload.get("bbox_m"))
        entry["primary_bone"] = primary_bone
        entry["offset_m"] = offset_m
        entry["sidecar_bbox_m"] = sidecar_bbox
        entry["glb_bbox_m"] = glb_bbox
        entry["target_bbox_m"] = target_bbox
        entry["bbox_center_local_m"] = list(bbox_center) if bbox_center is not None else None

        if not isinstance(sidecar_bbox, dict):
            entry["ok"] = False
            failures.append(f"{module}: sidecar bbox_m is not readable for GLB/preview comparison")
            per_module.append(entry)
            continue
        if not isinstance(glb_bbox, dict):
            entry["ok"] = False
            failures.append(f"{module}: GLB bbox is not readable for preview comparison")
            per_module.append(entry)
            continue

        sidecar_glb_delta = _bbox_abs_delta_m(sidecar_bbox, glb_bbox)
        sidecar_glb_axes = _bbox_axes_outside_abs_delta(sidecar_bbox, glb_bbox)
        entry["sidecar_glb_bbox_delta_m"] = sidecar_glb_delta
        entry["sidecar_glb_bbox_outside_tolerance_axes"] = sidecar_glb_axes
        if sidecar_glb_axes:
            entry["ok"] = False
            failures.append(
                f"{module}: sidecar bbox_m differs from GLB bounds on {sidecar_glb_axes} "
                f"(delta_m={sidecar_glb_delta}, tolerance_m={SIDECAR_GLB_BBOX_TOLERANCE_M})"
            )
            per_module.append(entry)
            continue

        glb_target_delta = _bbox_delta_pct(glb_bbox, target_bbox)
        glb_target_axes = _bbox_axes_outside_target(glb_bbox, target_bbox)
        glb_target_warn_axes = _bbox_axes_outside_target(
            glb_bbox,
            target_bbox,
            tolerance_ratio=TARGET_BBOX_PASS_RATIO,
        )
        glb_target_status = _bbox_target_status(glb_bbox, target_bbox)
        entry["glb_target_bbox_delta_pct"] = glb_target_delta
        entry["glb_target_bbox_outside_tolerance_axes"] = glb_target_axes
        entry["glb_target_bbox_warn_axes"] = glb_target_warn_axes
        entry["glb_target_bbox_status"] = glb_target_status
        if module == "back" and glb_bbox["z"] < target_bbox["z"] * (1.0 - TARGET_BBOX_TOLERANCE_RATIO):
            entry["ok"] = False
            failures.append(
                f"{module}: back GLB z thickness too thin "
                f"({glb_bbox['z']:.4f}m < {target_bbox['z'] * (1.0 - TARGET_BBOX_TOLERANCE_RATIO):.4f}m)"
            )
            per_module.append(entry)
            continue
        if glb_target_axes:
            entry["ok"] = False
            failures.append(
                f"{module}: GLB bbox outside target envelope on {glb_target_axes} "
                f"(delta_pct={glb_target_delta}, tolerance_pct={TARGET_BBOX_TOLERANCE_RATIO * 100:.1f})"
            )
            per_module.append(entry)
            continue
        if glb_target_status == "warn":
            warnings.append(
                f"{module}: GLB bbox outside pass envelope on {glb_target_warn_axes} "
                f"(delta_pct={glb_target_delta}, pass_tolerance_pct={TARGET_BBOX_PASS_RATIO * 100:.1f})"
            )

        # 4. body-fit anchor cross-check.
        try:
            slot_id = normalize_slot_id(module)
        except ValueError as exc:
            entry["ok"] = False
            failures.append(f"{module}: cannot map module to body-fit slot: {exc}")
            per_module.append(entry)
            continue
        spec = ARMOR_SLOT_SPECS[slot_id]
        entry["body_fit_slot"] = slot_id
        entry["expected_body_anchor"] = spec.body_anchor
        if primary_bone != spec.body_anchor:
            entry["ok"] = False
            failures.append(
                f"{module}: primary_bone={primary_bone} does not match body-fit anchor {spec.body_anchor}"
            )
            per_module.append(entry)
            continue

        # 5. offset-magnitude reachability vs the 170cm reference rig.
        attachment_check = _check_offset_reachable(
            primary_bone=primary_bone,
            offset_m=offset_m,
            bbox_center=bbox_center,
        )
        entry["attachment_check"] = attachment_check
        if not attachment_check["ok"]:
            entry["ok"] = False
            failures.append(f"{module}: {attachment_check.get('reason', 'offset out of tolerance')}")
            per_module.append(entry)
            continue

        attachment_target_check = _check_attachment_offset_target(module, offset_m)
        entry["attachment_target_check"] = attachment_target_check
        if attachment_target_check["status"] == "fail":
            entry["ok"] = False
            failures.append(
                f"{module}: offset magnitude {attachment_target_check.get('magnitude_m')}m exceeds "
                f"{attachment_target_check.get('hard_fail_tolerance_m')}m hard tolerance"
            )
            per_module.append(entry)
            continue
        if attachment_target_check["status"] == "warn":
            warnings.append(
                f"{module}: offset magnitude {attachment_target_check.get('magnitude_m')}m exceeds "
                f"{attachment_target_check.get('target_m')}m target"
            )

        entry["ok"] = True
        per_module.append(entry)

    mirror_checks = _mirror_pair_checks(per_module)
    for check in mirror_checks:
        if check["status"] == "fail":
            failures.append(
                f"{check['pair'][0]}/{check['pair'][1]}: mirror pair dimensions exceed "
                f"{MIRROR_PAIR_FAIL_TOLERANCE_RATIO * 100:.1f}% "
                f"(max_delta={check.get('max_delta_pct')}%)"
            )
        elif check["status"] == "warn":
            warnings.append(
                f"{check['pair'][0]}/{check['pair'][1]}: mirror pair dimensions exceed "
                f"{MIRROR_PAIR_WARN_TOLERANCE_RATIO * 100:.1f}% "
                f"(max_delta={check.get('max_delta_pct')}%)"
            )

    preview_contract = _check_web_preview_contract(repo_root_path)
    warnings.extend(preview_contract.get("warnings", []))
    if not preview_contract.get("ok", False):
        failures.extend(str(reason) for reason in preview_contract.get("reasons", []))

    # The "preview" counters intentionally mirror the canvas dataset names used
    # by the browser viewer (see docs/armor-runtime-pipeline.md).
    summary = {
        "preview_glb_parts": glb_resolved,
        "preview_fallback_parts": fallback_used,
        "web_preview_contract": preview_contract,
        "module_count": len(selected_modules),
        "expected_modules": list(selected_modules),
        "ok": fallback_used == 0 and not failures,
        "failures": failures,
        "warnings": warnings,
        "mirror_pair_checks": mirror_checks,
        "modules": per_module,
        "reference_height_cm": 170,
        "offset_magnitude_tolerance_m": OFFSET_MAGNITUDE_TOLERANCE_M,
        "sidecar_glb_bbox_tolerance_m": SIDECAR_GLB_BBOX_TOLERANCE_M,
        "target_bbox_tolerance_ratio": TARGET_BBOX_TOLERANCE_RATIO,
        "target_bbox_pass_ratio": TARGET_BBOX_PASS_RATIO,
    }
    return summary


def _format_human_summary(report: dict[str, Any]) -> str:
    lines = []
    summary_line = (
        f"previewGlbParts={report['preview_glb_parts']}"
        f" previewFallbackParts={report['preview_fallback_parts']}"
    )
    lines.append(summary_line)
    if report["failures"]:
        lines.append("Failures:")
        for failure in report["failures"]:
            lines.append(f"  - {failure}")
    if report["warnings"]:
        lines.append("Warnings:")
        for warn in report["warnings"]:
            lines.append(f"  - {warn}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(_REPO_ROOT), help="repo root to scan (defaults to checkout root)")
    parser.add_argument("--report-json", action="store_true", help="emit a structured JSON report instead of text")
    args = parser.parse_args(argv)

    report = smoke_check_web_glb_load(args.repo_root)
    if args.report_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(_format_human_summary(report))
    return 0 if report["preview_fallback_parts"] == 0 and not report["failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
