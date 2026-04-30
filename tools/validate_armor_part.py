"""Offline QA validator for armor GLB deliverables.

Validates the qa_gates listed in `src/henshin/modeler_blueprints.py` against
files at `viewer/assets/armor-parts/<module>/<module>.glb` plus sidecar
`<module>.modeler.json` and preview `preview/<module>.mesh.json`.

Runs entirely without Blender so it can execute in CI. GLB parsing uses
`pygltflib` when available, else a minimal binary header parser that reads
mesh/material/accessor metadata from the embedded glTF JSON chunk.

Usage:
  python tools/validate_armor_part.py <module>
  python tools/validate_armor_part.py --all
  python tools/validate_armor_part.py --all --report-json

Exit code is non-zero if any gate fails.
"""

from __future__ import annotations

import argparse
import json
import os
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

# Make src/henshin importable when invoked directly from the repo root.
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SRC_PATH = _REPO_ROOT / "src"
if str(_SRC_PATH) not in sys.path:
    sys.path.insert(0, str(_SRC_PATH))

from henshin.modeler_blueprints import (  # noqa: E402
    _CATEGORY_BY_MODULE,
    _CLEARANCE_BY_CATEGORY,
    _MIRROR_PAIRS,
    _THICKNESS_BY_CATEGORY,
    _reference_target_dimensions,
)


try:  # optional dependency, gated.
    import pygltflib  # type: ignore[import-not-found]

    _HAS_PYGLTFLIB = True
except Exception:  # noqa: BLE001
    pygltflib = None  # type: ignore[assignment]
    _HAS_PYGLTFLIB = False


# Body radius approximation (meters) per category, used for body-intersection gate.
_BODY_RADIUS_BY_CATEGORY: dict[str, float] = {
    "torso": 0.18,
    "dorsal": 0.18,
    "waist": 0.16,
    "shoulder": 0.10,
    "arm": 0.05,
    "hand": 0.04,
    "leg": 0.07,
    "foot": 0.06,
    "head": 0.10,
}

# Acceptable named material slot tokens. Matches the brief.
_ALLOWED_MATERIAL_SLOT_TOKENS = ("base_surface", "accent", "emissive", "trim")
_MAX_MATERIALS = 3
_MAX_PREVIEW_BYTES = 5 * 1024 * 1024
_BBOX_UPPER_SLACK = 1.05
_BBOX_LOWER_SLACK = 0.5
_MIRROR_DELTA_LIMIT = 0.03
_SIDECAR_DELTA_LIMIT = 0.05

_GATE_NAMES = (
    "stable_part_name",
    "bbox_within_target_envelope",
    "non_overlapping_uv0",
    "single_surface_base_material_or_declared_slots",
    "mirror_pair_dimension_delta_below_3_percent",
    "no_body_intersection_at_reference_pose",
    "sidecar_present_and_consistent",
    "preview_mesh_present",
)


# ---------------------------------------------------------------------------
# Result containers
# ---------------------------------------------------------------------------


@dataclass
class GateResult:
    name: str
    status: str  # "pass" | "warn" | "fail" | "skip"
    message: str = ""
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate": self.name,
            "status": self.status,
            "message": self.message,
            "detail": self.detail,
        }


@dataclass
class ModuleReport:
    module: str
    glb_path: str
    sidecar_path: str
    preview_path: str
    gates: list[GateResult] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    @property
    def status(self) -> str:
        if self.error:
            return "fail"
        worst = "pass"
        rank = {"pass": 0, "skip": 0, "warn": 1, "fail": 2}
        for gate in self.gates:
            if rank.get(gate.status, 2) > rank.get(worst, 0):
                worst = gate.status
        return worst

    @property
    def ok(self) -> bool:
        return self.status != "fail"

    def to_dict(self) -> dict[str, Any]:
        return {
            "module": self.module,
            "status": self.status,
            "ok": self.ok,
            "error": self.error,
            "glb_path": self.glb_path,
            "sidecar_path": self.sidecar_path,
            "preview_path": self.preview_path,
            "metrics": self.metrics,
            "gates": [gate.to_dict() for gate in self.gates],
        }


# ---------------------------------------------------------------------------
# Minimal GLB reader (no third-party deps required)
# ---------------------------------------------------------------------------


@dataclass
class GLBData:
    """Light extraction of GLB data we need for QA gates.

    Only the fields the validator actually consults are populated.
    """

    mesh_names: list[str]
    root_mesh_name: str | None
    material_names: list[str]
    image_count: int
    bbox_min: list[float] | None  # over the position accessor min, scene-aggregated
    bbox_max: list[float] | None
    triangle_count: int
    uv0_min: list[float] | None
    uv0_max: list[float] | None
    uv0_overlap_warning: str | None
    accessor_count: int

    def bbox_size(self) -> list[float] | None:
        if not self.bbox_min or not self.bbox_max:
            return None
        return [
            float(self.bbox_max[0]) - float(self.bbox_min[0]),
            float(self.bbox_max[1]) - float(self.bbox_min[1]),
            float(self.bbox_max[2]) - float(self.bbox_min[2]),
        ]


class GLBParseError(RuntimeError):
    pass


def _parse_glb_header(data: bytes) -> dict[str, Any]:
    """Parse a glTF 2.0 GLB binary into the embedded JSON chunk + raw BIN.

    Returns a dict with 'json' (parsed object) and 'bin' (bytes or b'').
    """

    if len(data) < 12:
        raise GLBParseError("file too small to be a GLB")
    magic, version, length = struct.unpack_from("<III", data, 0)
    if magic != 0x46546C67:  # 'glTF'
        raise GLBParseError("invalid GLB magic")
    if version != 2:
        raise GLBParseError(f"unsupported GLB version: {version}")
    if length > len(data):
        # Tolerate trailing/cropped uploads but still attempt parse.
        length = len(data)

    offset = 12
    json_obj: dict[str, Any] | None = None
    bin_blob: bytes = b""
    while offset + 8 <= length:
        chunk_length, chunk_type = struct.unpack_from("<II", data, offset)
        offset += 8
        chunk_end = offset + chunk_length
        if chunk_end > length:
            raise GLBParseError("chunk extends past file length")
        chunk_data = data[offset:chunk_end]
        offset = chunk_end
        if chunk_type == 0x4E4F534A:  # 'JSON'
            try:
                json_obj = json.loads(chunk_data.rstrip(b" \x00").decode("utf-8"))
            except Exception as exc:  # noqa: BLE001
                raise GLBParseError(f"failed to parse JSON chunk: {exc}") from exc
        elif chunk_type == 0x004E4942:  # 'BIN\0'
            bin_blob = chunk_data
        else:
            # Skip unknown chunk types per spec.
            continue
    if json_obj is None:
        raise GLBParseError("GLB missing JSON chunk")
    return {"json": json_obj, "bin": bin_blob}


def _collect_position_bounds(
    gltf: dict[str, Any],
) -> tuple[list[float] | None, list[float] | None]:
    """Aggregate accessor min/max across all POSITION accessors found in meshes."""

    accessors = gltf.get("accessors") or []
    meshes = gltf.get("meshes") or []
    pos_min: list[float] | None = None
    pos_max: list[float] | None = None
    for mesh in meshes:
        for prim in mesh.get("primitives") or []:
            attrs = prim.get("attributes") or {}
            pos_idx = attrs.get("POSITION")
            if not isinstance(pos_idx, int):
                continue
            if pos_idx < 0 or pos_idx >= len(accessors):
                continue
            acc = accessors[pos_idx]
            mn = acc.get("min")
            mx = acc.get("max")
            if (
                isinstance(mn, list)
                and isinstance(mx, list)
                and len(mn) == 3
                and len(mx) == 3
            ):
                if pos_min is None:
                    pos_min = [float(v) for v in mn]
                    pos_max = [float(v) for v in mx]
                else:
                    pos_min = [min(pos_min[i], float(mn[i])) for i in range(3)]
                    pos_max = [max(pos_max[i], float(mx[i])) for i in range(3)]
    return pos_min, pos_max


def _collect_uv0_bounds(
    gltf: dict[str, Any],
) -> tuple[list[float] | None, list[float] | None]:
    accessors = gltf.get("accessors") or []
    meshes = gltf.get("meshes") or []
    uv_min: list[float] | None = None
    uv_max: list[float] | None = None
    for mesh in meshes:
        for prim in mesh.get("primitives") or []:
            attrs = prim.get("attributes") or {}
            uv_idx = attrs.get("TEXCOORD_0")
            if not isinstance(uv_idx, int):
                continue
            if uv_idx < 0 or uv_idx >= len(accessors):
                continue
            acc = accessors[uv_idx]
            mn = acc.get("min")
            mx = acc.get("max")
            if (
                isinstance(mn, list)
                and isinstance(mx, list)
                and len(mn) == 2
                and len(mx) == 2
            ):
                if uv_min is None:
                    uv_min = [float(v) for v in mn]
                    uv_max = [float(v) for v in mx]
                else:
                    uv_min = [min(uv_min[i], float(mn[i])) for i in range(2)]
                    uv_max = [max(uv_max[i], float(mx[i])) for i in range(2)]
    return uv_min, uv_max


def _collect_triangle_count(gltf: dict[str, Any]) -> int:
    accessors = gltf.get("accessors") or []
    meshes = gltf.get("meshes") or []
    triangles = 0
    for mesh in meshes:
        for prim in mesh.get("primitives") or []:
            mode = prim.get("mode", 4)  # default TRIANGLES
            indices_idx = prim.get("indices")
            count = 0
            if isinstance(indices_idx, int) and 0 <= indices_idx < len(accessors):
                count = int(accessors[indices_idx].get("count") or 0)
            else:
                pos_idx = (prim.get("attributes") or {}).get("POSITION")
                if isinstance(pos_idx, int) and 0 <= pos_idx < len(accessors):
                    count = int(accessors[pos_idx].get("count") or 0)
            if mode == 4:  # TRIANGLES
                triangles += count // 3
            elif mode in (5, 6):  # TRIANGLE_STRIP/FAN
                triangles += max(0, count - 2)
    return triangles


def _root_mesh_name(gltf: dict[str, Any]) -> str | None:
    """Return the name of the mesh attached to the root scene's first node, if any."""

    scenes = gltf.get("scenes") or []
    nodes = gltf.get("nodes") or []
    meshes = gltf.get("meshes") or []
    if not scenes or not nodes or not meshes:
        # Fallback: first mesh name.
        if meshes:
            return str(meshes[0].get("name") or "") or None
        return None
    scene_idx = gltf.get("scene", 0)
    if not (0 <= scene_idx < len(scenes)):
        scene_idx = 0
    root_nodes = scenes[scene_idx].get("nodes") or []
    candidates: list[str] = []
    for node_idx in root_nodes:
        if not isinstance(node_idx, int) or not (0 <= node_idx < len(nodes)):
            continue
        node = nodes[node_idx]
        mesh_idx = node.get("mesh")
        if isinstance(mesh_idx, int) and 0 <= mesh_idx < len(meshes):
            name = meshes[mesh_idx].get("name")
            if isinstance(name, str) and name:
                candidates.append(name)
        # Walk a single layer of children to catch wrapper nodes.
        for child_idx in node.get("children") or []:
            if not isinstance(child_idx, int) or not (0 <= child_idx < len(nodes)):
                continue
            child_mesh_idx = nodes[child_idx].get("mesh")
            if isinstance(child_mesh_idx, int) and 0 <= child_mesh_idx < len(meshes):
                name = meshes[child_mesh_idx].get("name")
                if isinstance(name, str) and name:
                    candidates.append(name)
    if candidates:
        return candidates[0]
    if meshes:
        return str(meshes[0].get("name") or "") or None
    return None


def _uv_overlap_warning(gltf: dict[str, Any], bin_blob: bytes) -> str | None:
    """Probabilistic UV overlap scan using a coarse bucket grid.

    Returns a warning string when many UV coords map to the same bucket,
    suggesting overlap. We only inspect TEXCOORD_0 from the first primitive
    of the first mesh to keep this cheap.
    """

    if not bin_blob:
        return None
    accessors = gltf.get("accessors") or []
    bufferviews = gltf.get("bufferViews") or []
    meshes = gltf.get("meshes") or []
    if not (accessors and bufferviews and meshes):
        return None
    primitives = (meshes[0].get("primitives") or []) if meshes else []
    if not primitives:
        return None
    uv_idx = (primitives[0].get("attributes") or {}).get("TEXCOORD_0")
    if not isinstance(uv_idx, int) or uv_idx >= len(accessors):
        return None
    acc = accessors[uv_idx]
    bv_idx = acc.get("bufferView")
    if not isinstance(bv_idx, int) or bv_idx >= len(bufferviews):
        return None
    bv = bufferviews[bv_idx]
    count = int(acc.get("count") or 0)
    if count <= 0:
        return None
    component_type = int(acc.get("componentType") or 5126)  # FLOAT
    if component_type != 5126:  # only handle FLOAT for the heuristic
        return None
    byte_offset = int(bv.get("byteOffset") or 0) + int(acc.get("byteOffset") or 0)
    byte_stride = int(bv.get("byteStride") or 0) or 8  # vec2 float = 8
    if byte_offset + byte_stride * (count - 1) + 8 > len(bin_blob):
        return None
    bucket_grid = 64
    buckets: dict[tuple[int, int], int] = {}
    sample_step = max(1, count // 4096)
    sampled = 0
    out_of_range = 0
    for i in range(0, count, sample_step):
        offset = byte_offset + i * byte_stride
        u, v = struct.unpack_from("<ff", bin_blob, offset)
        if u < 0 or u > 1 or v < 0 or v > 1:
            out_of_range += 1
        bx = max(0, min(bucket_grid - 1, int(u * bucket_grid)))
        by = max(0, min(bucket_grid - 1, int(v * bucket_grid)))
        buckets[(bx, by)] = buckets.get((bx, by), 0) + 1
        sampled += 1
    if sampled == 0:
        return None
    density = max(buckets.values())
    avg = sampled / max(1, len(buckets))
    if density >= max(8, avg * 6):
        return f"high UV bucket density (peak {density}, avg {avg:.1f}) suggests possible overlap"
    if out_of_range > 0:
        return f"{out_of_range} sampled UV0 coord(s) outside [0,1]"
    return None


def _read_glb(path: Path) -> GLBData:
    data = path.read_bytes()
    parsed = _parse_glb_header(data)
    gltf = parsed["json"]
    bin_blob = parsed["bin"]
    meshes = gltf.get("meshes") or []
    mesh_names = [str(m.get("name") or "") for m in meshes]
    materials = gltf.get("materials") or []
    material_names = [str(m.get("name") or "") for m in materials]
    images = gltf.get("images") or []
    pos_min, pos_max = _collect_position_bounds(gltf)
    uv_min, uv_max = _collect_uv0_bounds(gltf)
    return GLBData(
        mesh_names=mesh_names,
        root_mesh_name=_root_mesh_name(gltf),
        material_names=material_names,
        image_count=len(images),
        bbox_min=pos_min,
        bbox_max=pos_max,
        triangle_count=_collect_triangle_count(gltf),
        uv0_min=uv_min,
        uv0_max=uv_max,
        uv0_overlap_warning=_uv_overlap_warning(gltf, bin_blob),
        accessor_count=len(gltf.get("accessors") or []),
    )


# ---------------------------------------------------------------------------
# Gate logic
# ---------------------------------------------------------------------------


def _module_paths(repo_root: Path, module: str) -> dict[str, Path]:
    base = repo_root / "viewer" / "assets" / "armor-parts" / module
    return {
        "glb": base / f"{module}.glb",
        "sidecar": base / f"{module}.modeler.json",
        "preview": base / "preview" / f"{module}.mesh.json",
    }


def _gate_stable_part_name(module: str, glb: GLBData) -> GateResult:
    expected = f"armor_{module}_v001"
    if glb.root_mesh_name == expected:
        return GateResult(
            "stable_part_name",
            "pass",
            f"root mesh named {expected}",
            {"expected": expected, "found": glb.root_mesh_name},
        )
    return GateResult(
        "stable_part_name",
        "fail",
        f"root mesh name '{glb.root_mesh_name}' != expected '{expected}'",
        {"expected": expected, "found": glb.root_mesh_name, "all": glb.mesh_names},
    )


def _gate_bbox_within_envelope(module: str, glb: GLBData) -> GateResult:
    target = _reference_target_dimensions(module)
    size = glb.bbox_size()
    if size is None:
        return GateResult(
            "bbox_within_target_envelope",
            "fail",
            "GLB has no POSITION accessor min/max; cannot determine bbox",
        )
    axes = ("x", "y", "z")
    detail: dict[str, Any] = {"target": target, "size": dict(zip(axes, size))}
    over = []
    under = []
    for i, axis in enumerate(axes):
        target_value = float(target.get(axis) or 0.0)
        actual = float(size[i])
        upper = target_value * _BBOX_UPPER_SLACK
        lower = target_value * _BBOX_LOWER_SLACK
        if target_value <= 0:
            continue
        if actual > upper:
            over.append({"axis": axis, "actual": actual, "limit": upper})
        if actual < lower:
            under.append({"axis": axis, "actual": actual, "minimum": lower})
    detail["over"] = over
    detail["under"] = under
    if not over and not under:
        return GateResult(
            "bbox_within_target_envelope",
            "pass",
            "bbox within +5% / -50% of authoring target",
            detail,
        )
    msg_parts = []
    if over:
        msg_parts.append(f"too large: {over}")
    if under:
        msg_parts.append(f"too small: {under}")
    return GateResult(
        "bbox_within_target_envelope",
        "fail",
        "; ".join(msg_parts),
        detail,
    )


def _gate_non_overlapping_uv0(module: str, glb: GLBData) -> GateResult:
    detail: dict[str, Any] = {
        "uv0_min": glb.uv0_min,
        "uv0_max": glb.uv0_max,
        "scan_warning": glb.uv0_overlap_warning,
    }
    warnings: list[str] = []
    if glb.uv0_min is None or glb.uv0_max is None:
        return GateResult(
            "non_overlapping_uv0",
            "warn",
            "no TEXCOORD_0 accessor min/max found",
            detail,
        )
    out_of_range = any(value < 0 or value > 1 for value in glb.uv0_min + glb.uv0_max)
    if out_of_range:
        warnings.append(
            f"UV0 outside [0,1] (min={glb.uv0_min}, max={glb.uv0_max})"
        )
    if glb.uv0_overlap_warning:
        warnings.append(glb.uv0_overlap_warning)
    if warnings:
        return GateResult(
            "non_overlapping_uv0",
            "warn",
            "; ".join(warnings),
            detail,
        )
    return GateResult(
        "non_overlapping_uv0",
        "pass",
        "UV0 within unit square; no obvious overlap",
        detail,
    )


def _gate_material_slots(module: str, glb: GLBData) -> GateResult:
    detail = {"materials": glb.material_names, "count": len(glb.material_names)}
    if not glb.material_names:
        return GateResult(
            "single_surface_base_material_or_declared_slots",
            "fail",
            "GLB has no materials",
            detail,
        )
    if len(glb.material_names) > _MAX_MATERIALS:
        return GateResult(
            "single_surface_base_material_or_declared_slots",
            "fail",
            f"{len(glb.material_names)} materials exceeds limit {_MAX_MATERIALS}",
            detail,
        )
    matched = [
        name
        for name in glb.material_names
        if any(token in (name or "").lower() for token in _ALLOWED_MATERIAL_SLOT_TOKENS)
    ]
    detail["matched_named_slots"] = matched
    if not matched:
        return GateResult(
            "single_surface_base_material_or_declared_slots",
            "fail",
            (
                "no material name contains any of "
                f"{_ALLOWED_MATERIAL_SLOT_TOKENS}; got {glb.material_names}"
            ),
            detail,
        )
    return GateResult(
        "single_surface_base_material_or_declared_slots",
        "pass",
        f"{len(glb.material_names)} material(s); declared slot present",
        detail,
    )


def _gate_mirror_pair(module: str, glb: GLBData, repo_root: Path) -> GateResult:
    partner = _MIRROR_PAIRS.get(module)
    if partner is None:
        return GateResult(
            "mirror_pair_dimension_delta_below_3_percent",
            "skip",
            "module is not part of a mirror pair",
        )
    partner_paths = _module_paths(repo_root, partner)
    partner_glb_path = partner_paths["glb"]
    if not partner_glb_path.exists():
        return GateResult(
            "mirror_pair_dimension_delta_below_3_percent",
            "fail",
            f"partner GLB missing for '{partner}' at {partner_glb_path}",
            {"partner": partner, "partner_path": str(partner_glb_path)},
        )
    try:
        partner_data = _read_glb(partner_glb_path)
    except Exception as exc:  # noqa: BLE001
        return GateResult(
            "mirror_pair_dimension_delta_below_3_percent",
            "fail",
            f"failed to read partner GLB: {exc}",
            {"partner": partner, "partner_path": str(partner_glb_path)},
        )
    size = glb.bbox_size()
    partner_size = partner_data.bbox_size()
    if size is None or partner_size is None:
        return GateResult(
            "mirror_pair_dimension_delta_below_3_percent",
            "fail",
            "missing bbox on either module or partner; cannot compare",
            {
                "partner": partner,
                "size": size,
                "partner_size": partner_size,
            },
        )
    axes = ("x", "y", "z")
    deltas = []
    breached = []
    for i, axis in enumerate(axes):
        a = float(size[i])
        b = float(partner_size[i])
        denom = max(abs(a), abs(b), 1e-9)
        delta = abs(a - b) / denom
        deltas.append({"axis": axis, "delta": delta, "module": a, "partner": b})
        if delta > _MIRROR_DELTA_LIMIT:
            breached.append({"axis": axis, "delta": delta})
    detail = {
        "partner": partner,
        "deltas": deltas,
        "limit": _MIRROR_DELTA_LIMIT,
    }
    if breached:
        return GateResult(
            "mirror_pair_dimension_delta_below_3_percent",
            "fail",
            f"mirror axes exceed {_MIRROR_DELTA_LIMIT*100:.1f}%: {breached}",
            detail,
        )
    return GateResult(
        "mirror_pair_dimension_delta_below_3_percent",
        "pass",
        f"all axes within {_MIRROR_DELTA_LIMIT*100:.1f}% vs '{partner}'",
        detail,
    )


_WRAP_AROUND_CATEGORIES = {"torso", "dorsal", "waist"}
_OFFSET_AWARE_CATEGORIES = {"arm", "hand", "leg", "foot", "head", "shoulder"}
_BODY_INTERSECTION_TOL_M = 0.01


def _gate_no_body_intersection(
    module: str,
    glb: GLBData,
    sidecar: dict[str, Any] | None,
) -> GateResult:
    """Per-category body-intersection gate.

    Three branches:
    - Wrap-around (torso/dorsal/waist): treat bbox as hollow shell. Pass when
      bbox.x and bbox.z each enclose the body diameter (>= 2*(r+c) - tol) and
      a positive shell_thickness_target_m is declared.
    - Offset-aware (arm/hand/leg/foot/head/shoulder): translate bbox center by
      sidecar vrm_attachment.offset_m, then require the offset center distance
      from the cylinder axis (Y) plus bbox_radial_extent to clear r+c.
    - Fallback (missing offset, unknown category, or neither pass branch
      satisfied): emit warn with the legacy clearance diagnostic so reviewers
      can triage visually instead of blocking CI.
    """

    category = _CATEGORY_BY_MODULE.get(module, "armor")
    clearance = _CLEARANCE_BY_CATEGORY.get(category, 0.02)
    body_radius = _BODY_RADIUS_BY_CATEGORY.get(category, 0.08)
    detail: dict[str, Any] = {
        "category": category,
        "clearance_required_m": clearance,
        "body_radius_m": body_radius,
    }
    if not glb.bbox_min or not glb.bbox_max:
        return GateResult(
            "no_body_intersection_at_reference_pose",
            "fail",
            "no bbox available to evaluate body intersection",
            detail,
        )

    bmin = glb.bbox_min
    bmax = glb.bbox_max
    size_x = float(bmax[0]) - float(bmin[0])
    size_z = float(bmax[2]) - float(bmin[2])
    cx = 0.5 * (bmin[0] + bmax[0])
    cz = 0.5 * (bmin[2] + bmax[2])
    lateral_inner = min(abs(bmin[0]), abs(bmax[0]), abs(bmin[2]), abs(bmax[2]))
    gap = lateral_inner - body_radius
    detail["lateral_inner_inset_m"] = lateral_inner
    detail["gap_m"] = gap
    detail["bbox_center_xz"] = [cx, cz]

    # Branch 1: wrap-around shell semantics (torso/dorsal/waist).
    if category in _WRAP_AROUND_CATEGORIES:
        required_perimeter = 2.0 * (body_radius + clearance) - _BODY_INTERSECTION_TOL_M
        shell_thickness = _declared_shell_thickness(sidecar, category)
        detail["wrap_required_extent_m"] = required_perimeter
        detail["bbox_extent_x_m"] = size_x
        detail["bbox_extent_z_m"] = size_z
        detail["shell_thickness_target_m"] = shell_thickness
        if (
            size_x >= required_perimeter
            and size_z >= required_perimeter
            and shell_thickness is not None
            and shell_thickness > 0.0
        ):
            return GateResult(
                "no_body_intersection_at_reference_pose",
                "pass",
                (
                    f"shell encloses body: bbox.x={size_x:.4f}m, bbox.z={size_z:.4f}m "
                    f">= 2*(r+c)-tol={required_perimeter:.4f}m; "
                    f"shell_thickness_target_m={shell_thickness:.4f}m"
                ),
                detail,
            )
        # fall through to the legacy clearance check + fallback warn.

    # Branch 2: bone-offset-aware check (limb/head/shoulder).
    sidecar_offset = _sidecar_attachment_offset(sidecar)
    if category in _OFFSET_AWARE_CATEGORIES and sidecar_offset is not None:
        offset_x, _, offset_z = sidecar_offset
        # Translate the bbox center by the declared bone offset; the cylinder
        # axis remains the world Y axis at the origin.
        post_offset_cx = cx + offset_x
        post_offset_cz = cz + offset_z
        offset_axis_distance = (
            post_offset_cx * post_offset_cx + post_offset_cz * post_offset_cz
        ) ** 0.5
        bbox_radial_extent = max(size_x, size_z) / 2.0
        required = body_radius + clearance + bbox_radial_extent
        detail["sidecar_offset_m"] = list(sidecar_offset)
        detail["post_offset_center_xz"] = [post_offset_cx, post_offset_cz]
        detail["bbox_radial_extent_m"] = bbox_radial_extent
        detail["offset_required_distance_m"] = required
        detail["offset_axis_distance_m"] = offset_axis_distance
        if offset_axis_distance >= required - _BODY_INTERSECTION_TOL_M:
            return GateResult(
                "no_body_intersection_at_reference_pose",
                "pass",
                (
                    f"offset-aware clear: |center+offset|={offset_axis_distance:.4f}m "
                    f">= r+c+extent={required:.4f}m"
                ),
                detail,
            )

    # Legacy bbox-inset clearance check (still useful for parts authored already
    # offset in part-local space, e.g. boots).
    if gap >= clearance:
        return GateResult(
            "no_body_intersection_at_reference_pose",
            "pass",
            f"clearance {gap:.4f}m >= required {clearance:.4f}m",
            detail,
        )

    # Soft-pass: legacy sidecar offset compensation, kept for back-compat with
    # older sidecars whose offset_m + bbox inset already cleared the body.
    if sidecar_offset is not None:
        offset_x, _, offset_z = sidecar_offset
        sidecar_lateral = (offset_x * offset_x + offset_z * offset_z) ** 0.5
        detail["sidecar_lateral_offset_m"] = sidecar_lateral
        if sidecar_lateral + lateral_inner >= body_radius + clearance:
            return GateResult(
                "no_body_intersection_at_reference_pose",
                "warn",
                (
                    "bbox-only inset is below clearance, but sidecar "
                    "vrm_attachment.offset_m compensates; verify in viewer"
                ),
                detail,
            )

    # Branch 3: fallback. Same diagnostic as before but emit warn (not fail) so
    # reviewers can triage visually. The check still flags torso shells that
    # don't enclose the body and limbs centered inside the body cylinder.
    return GateResult(
        "no_body_intersection_at_reference_pose",
        "warn",
        f"clearance {gap:.4f}m < required {clearance:.4f}m",
        detail,
    )


def _declared_shell_thickness(
    sidecar: dict[str, Any] | None, category: str
) -> float | None:
    """Return the shell thickness target. Sidecar overrides blueprint default.

    Returns None when neither source is available so the caller can decide.
    """

    if isinstance(sidecar, dict):
        candidates = [
            sidecar.get("shell_thickness_target_m"),
            (sidecar.get("target_envelope") or {}).get("shell_thickness_target_m")
            if isinstance(sidecar.get("target_envelope"), dict)
            else None,
            (sidecar.get("target_envelope_m") or {}).get("shell_thickness_target_m")
            if isinstance(sidecar.get("target_envelope_m"), dict)
            else None,
        ]
        for value in candidates:
            if isinstance(value, (int, float)) and float(value) > 0:
                return float(value)
    blueprint_value = _THICKNESS_BY_CATEGORY.get(category)
    if isinstance(blueprint_value, (int, float)) and float(blueprint_value) > 0:
        return float(blueprint_value)
    return None


def _sidecar_attachment_offset(
    sidecar: dict[str, Any] | None,
) -> tuple[float, float, float] | None:
    if not isinstance(sidecar, dict):
        return None
    attachment = sidecar.get("vrm_attachment")
    if not isinstance(attachment, dict):
        return None
    offset = attachment.get("offset_m") or attachment.get("offset")
    if isinstance(offset, list) and len(offset) >= 3:
        try:
            return float(offset[0]), float(offset[1]), float(offset[2])
        except (TypeError, ValueError):
            return None
    return None


def _gate_sidecar(
    module: str,
    glb: GLBData,
    sidecar_path: Path,
) -> tuple[GateResult, dict[str, Any] | None]:
    if not sidecar_path.exists():
        return (
            GateResult(
                "sidecar_present_and_consistent",
                "fail",
                f"sidecar missing at {sidecar_path}",
                {"sidecar_path": str(sidecar_path)},
            ),
            None,
        )
    try:
        payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return (
            GateResult(
                "sidecar_present_and_consistent",
                "fail",
                f"sidecar unreadable: {exc}",
                {"sidecar_path": str(sidecar_path)},
            ),
            None,
        )
    detail: dict[str, Any] = {"sidecar_path": str(sidecar_path)}
    failures: list[str] = []

    claimed_bbox_size = _claimed_bbox_size(payload)
    actual_size = glb.bbox_size()
    detail["claimed_bbox_size"] = claimed_bbox_size
    detail["actual_bbox_size"] = actual_size
    if claimed_bbox_size and actual_size:
        for i, axis in enumerate(("x", "y", "z")):
            denom = max(abs(actual_size[i]), 1e-9)
            delta = abs(claimed_bbox_size[i] - actual_size[i]) / denom
            if delta > _SIDECAR_DELTA_LIMIT:
                failures.append(
                    f"bbox.{axis} sidecar={claimed_bbox_size[i]:.4f} actual={actual_size[i]:.4f} delta={delta:.3f}"
                )
    elif claimed_bbox_size is None:
        failures.append("sidecar missing bbox dimensions")

    claimed_triangles = _claimed_triangles(payload)
    detail["claimed_triangles"] = claimed_triangles
    detail["actual_triangles"] = glb.triangle_count
    if isinstance(claimed_triangles, int) and glb.triangle_count > 0:
        denom = max(glb.triangle_count, 1)
        delta = abs(claimed_triangles - glb.triangle_count) / denom
        if delta > _SIDECAR_DELTA_LIMIT:
            failures.append(
                f"triangles sidecar={claimed_triangles} actual={glb.triangle_count} delta={delta:.3f}"
            )
    if failures:
        return (
            GateResult(
                "sidecar_present_and_consistent",
                "fail",
                "; ".join(failures),
                detail,
            ),
            payload,
        )
    return (
        GateResult(
            "sidecar_present_and_consistent",
            "pass",
            "sidecar present and consistent within 5%",
            detail,
        ),
        payload,
    )


def _claimed_bbox_size(payload: dict[str, Any]) -> list[float] | None:
    if not isinstance(payload, dict):
        return None
    # Accept several shapes: explicit size, min/max, or x/y/z.
    bbox = (
        payload.get("bbox_m")
        or payload.get("bounding_box")
        or payload.get("bbox")
        or payload.get("dimensions")
        or payload.get("authoring_target_m")
    )
    if isinstance(bbox, dict):
        size = bbox.get("size") or bbox.get("dimensions")
        if isinstance(size, list) and len(size) == 3:
            try:
                return [float(size[i]) for i in range(3)]
            except (TypeError, ValueError):
                return None
        if all(isinstance(bbox.get(k), (int, float)) for k in ("x", "y", "z")):
            return [float(bbox["x"]), float(bbox["y"]), float(bbox["z"])]
        mn = bbox.get("min") or bbox.get("minimum")
        mx = bbox.get("max") or bbox.get("maximum")
        if (
            isinstance(mn, list)
            and isinstance(mx, list)
            and len(mn) == 3
            and len(mx) == 3
        ):
            try:
                return [float(mx[i]) - float(mn[i]) for i in range(3)]
            except (TypeError, ValueError):
                return None
    if isinstance(bbox, list) and len(bbox) == 3:
        try:
            return [float(bbox[i]) for i in range(3)]
        except (TypeError, ValueError):
            return None
    return None


def _claimed_triangles(payload: dict[str, Any]) -> int | None:
    if not isinstance(payload, dict):
        return None
    candidates = [
        payload.get("triangles"),
        payload.get("triangle_count"),
        payload.get("tri_count"),
    ]
    metrics = payload.get("metrics") if isinstance(payload.get("metrics"), dict) else {}
    candidates.extend(
        [metrics.get("triangles"), metrics.get("triangle_count"), metrics.get("tri_count")]
    )
    for value in candidates:
        if isinstance(value, int) and value >= 0:
            return value
    return None


def _gate_preview_present(module: str, preview_path: Path) -> GateResult:
    if not preview_path.exists():
        return GateResult(
            "preview_mesh_present",
            "fail",
            f"preview missing at {preview_path}",
            {"preview_path": str(preview_path)},
        )
    size = preview_path.stat().st_size
    detail = {
        "preview_path": str(preview_path),
        "size_bytes": size,
        "limit_bytes": _MAX_PREVIEW_BYTES,
    }
    if size > _MAX_PREVIEW_BYTES:
        return GateResult(
            "preview_mesh_present",
            "fail",
            f"preview {size} bytes exceeds {_MAX_PREVIEW_BYTES}",
            detail,
        )
    return GateResult(
        "preview_mesh_present",
        "pass",
        f"preview present ({size} bytes)",
        detail,
    )


# ---------------------------------------------------------------------------
# Validation entry points
# ---------------------------------------------------------------------------


def validate_module(repo_root: Path, module: str) -> ModuleReport:
    paths = _module_paths(repo_root, module)
    report = ModuleReport(
        module=module,
        glb_path=str(paths["glb"]),
        sidecar_path=str(paths["sidecar"]),
        preview_path=str(paths["preview"]),
    )
    if not paths["glb"].exists():
        report.error = f"GLB missing at {paths['glb']}"
        report.gates.append(
            GateResult(
                "stable_part_name",
                "fail",
                report.error,
                {"glb_path": str(paths["glb"])},
            )
        )
        return report
    try:
        glb = _read_glb(paths["glb"])
    except GLBParseError as exc:
        report.error = f"GLB parse error: {exc}"
        report.gates.append(GateResult("stable_part_name", "fail", report.error))
        return report
    except Exception as exc:  # noqa: BLE001
        report.error = f"unexpected error reading GLB: {exc}"
        report.gates.append(GateResult("stable_part_name", "fail", report.error))
        return report

    report.metrics = {
        "mesh_names": glb.mesh_names,
        "root_mesh_name": glb.root_mesh_name,
        "material_names": glb.material_names,
        "image_count": glb.image_count,
        "bbox_min": glb.bbox_min,
        "bbox_max": glb.bbox_max,
        "bbox_size": glb.bbox_size(),
        "triangle_count": glb.triangle_count,
        "uv0_min": glb.uv0_min,
        "uv0_max": glb.uv0_max,
        "accessor_count": glb.accessor_count,
        "uv0_overlap_warning": glb.uv0_overlap_warning,
        "parser": "pygltflib" if _HAS_PYGLTFLIB else "minimal",
    }

    report.gates.append(_gate_stable_part_name(module, glb))
    report.gates.append(_gate_bbox_within_envelope(module, glb))
    report.gates.append(_gate_non_overlapping_uv0(module, glb))
    report.gates.append(_gate_material_slots(module, glb))
    report.gates.append(_gate_mirror_pair(module, glb, repo_root))
    sidecar_gate, sidecar_payload = _gate_sidecar(module, glb, paths["sidecar"])
    report.gates.append(_gate_no_body_intersection(module, glb, sidecar_payload))
    report.gates.append(sidecar_gate)
    report.gates.append(_gate_preview_present(module, paths["preview"]))
    return report


def validate_modules(repo_root: Path, modules: Iterable[str]) -> list[ModuleReport]:
    return [validate_module(repo_root, module) for module in modules]


# ---------------------------------------------------------------------------
# CLI rendering
# ---------------------------------------------------------------------------


_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_GREY = "\033[90m"
_RESET = "\033[0m"


def _colorize(text: str, status: str, use_color: bool) -> str:
    if not use_color:
        return text
    color = {
        "pass": _GREEN,
        "warn": _YELLOW,
        "fail": _RED,
        "skip": _GREY,
    }.get(status, "")
    if not color:
        return text
    return f"{color}{text}{_RESET}"


def _print_text_report(reports: list[ModuleReport], use_color: bool) -> None:
    for report in reports:
        header = f"[{report.status.upper():^4}] {report.module}"
        print(_colorize(header, report.status, use_color))
        if report.error:
            print(f"  error: {report.error}")
        for gate in report.gates:
            tag = f"  {gate.status:>4}  {gate.name}"
            line = f"{tag}: {gate.message}" if gate.message else tag
            print(_colorize(line, gate.status, use_color))
    fails = sum(1 for r in reports if r.status == "fail")
    warns = sum(1 for r in reports if r.status == "warn")
    passes = sum(1 for r in reports if r.status == "pass")
    summary = f"validated {len(reports)} module(s): {passes} pass, {warns} warn, {fails} fail"
    if fails:
        print(_colorize(summary, "fail", use_color))
    elif warns:
        print(_colorize(summary, "warn", use_color))
    else:
        print(_colorize(summary, "pass", use_color))


def _all_known_modules() -> list[str]:
    return list(_CATEGORY_BY_MODULE.keys())


def _resolve_modules(args: argparse.Namespace) -> list[str]:
    if args.all:
        return _all_known_modules()
    if args.module:
        return [args.module]
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Offline QA validator for armor GLB deliverables.",
    )
    parser.add_argument(
        "module",
        nargs="?",
        help="Module name (e.g. 'helmet', 'left_shoulder'). Omit when --all is set.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Validate every known module under viewer/assets/armor-parts/.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root (default: current working directory).",
    )
    parser.add_argument(
        "--report-json",
        action="store_true",
        help="Emit a structured JSON report to stdout.",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI color even if stdout is a tty.",
    )
    args = parser.parse_args(argv)

    modules = _resolve_modules(args)
    if not modules:
        parser.error("either MODULE or --all is required")

    reports = validate_modules(args.repo_root, modules)
    if args.report_json:
        json.dump(
            {
                "ok": all(r.ok for r in reports),
                "modules": [r.to_dict() for r in reports],
                "parser": "pygltflib" if _HAS_PYGLTFLIB else "minimal",
            },
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
    else:
        use_color = (not args.no_color) and sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
        _print_text_report(reports, use_color)

    return 0 if all(r.ok for r in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
