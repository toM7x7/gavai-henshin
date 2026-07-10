"""Static Quest whole-suit armor assembly audit.

This script reads the Quest runtime placement contract and audits the assembled
armor as one body-space suit. It intentionally avoids opening Quest or loading
Three.js; the runtime center points and target sizes are enough to catch missing
parts, broken symmetry, implausible body-fit distances, and obvious AABB
interpenetration.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME_SOURCE = REPO_ROOT / "viewer" / "quest-iw-demo" / "quest-demo.js"
DEFAULT_ARMOR_ROOT = REPO_ROOT / "viewer" / "assets" / "armor-parts"
CONTRACT_VERSION = "quest-armor-whole-suit-audit.v1"
HUMAN_ANCHOR_CONTRACT_VERSION = "quest-human-anchor-contract.v1"
AXES = ("x", "y", "z")
AUDIT_SCOPE = {
    "geometry_basis": "target-contract-only",
    "placement_basis": (
        "Quest QUEST_HUMAN_ANCHOR_CONTRACT.center_m runtime centers, falling back to "
        "VR_BODY_PART_POSES plus QUEST_ASSEMBLY_ADJUSTMENTS, plus QUEST_GLB_TARGET_SIZES AABBs"
    ),
    "asset_validation": "existence-only",
    "fit_link_validation": "primary-axis-only",
    "confidence_level": "coarse static CI gate",
    "pass_meaning": (
        "Runtime target placement boxes satisfy coarse whole-suit checks for missing parts, "
        "global extents, symmetry, primary-axis fit distances, and obvious AABB overlaps."
    ),
    "pass_does_not_guarantee": [
        "actual GLB mesh dimensions or bounds",
        "Quest-rendered visual fit",
        "secondary-axis drift on every fit link",
        "motion-time intersections",
        "sub-centimeter micro-adjustment quality",
    ],
}

MIRROR_PAIRS = (
    ("left_shoulder", "right_shoulder"),
    ("left_upperarm", "right_upperarm"),
    ("left_forearm", "right_forearm"),
    ("left_hand", "right_hand"),
    ("left_thigh", "right_thigh"),
    ("left_shin", "right_shin"),
    ("left_boot", "right_boot"),
)

CANONICAL_HUMAN_ANCHOR_PARTS = (
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

PART_NAME_ANCHOR_RULES = {
    "helmet": {
        "human_anchor": "head",
        "body_region": "head",
        "body_chain": "head_torso",
        "chain_order": 0,
        "wear_meaning": "Helmet shell around the head; keep neck and chest clearance readable.",
        "whole_suit_role": "Top anchor for full-suit height and head-to-torso spacing.",
    },
    "chest": {
        "human_anchor": "front_upper_torso",
        "body_region": "torso",
        "body_chain": "head_torso",
        "chain_order": 1,
        "wear_meaning": "Front torso shell over the upper chest and ribcage.",
        "whole_suit_role": "Primary front body-fit anchor for the suit silhouette.",
    },
    "back": {
        "human_anchor": "back_upper_torso",
        "body_region": "torso",
        "body_chain": "head_torso",
        "chain_order": 2,
        "wear_meaning": "Back torso shell behind the upper chest and spine line.",
        "whole_suit_role": "Balances chest depth so the torso reads as wrapped armor, not a flat plate.",
    },
    "waist": {
        "human_anchor": "pelvis_waist",
        "body_region": "pelvis",
        "body_chain": "head_torso",
        "chain_order": 3,
        "wear_meaning": "Belt and waist shell around pelvis/abdomen transition.",
        "whole_suit_role": "Bridge between torso and both leg chains.",
    },
    "shoulder": {
        "human_anchor": "{side}_shoulder_girdle",
        "body_region": "arm",
        "body_chain": "{side}_arm",
        "chain_order": 0,
        "wear_meaning": "Shoulder cap over the deltoid and upper-arm hinge.",
        "whole_suit_role": "Starts the arm chain while preserving torso-to-arm separation.",
    },
    "upperarm": {
        "human_anchor": "{side}_upper_arm",
        "body_region": "arm",
        "body_chain": "{side}_arm",
        "chain_order": 1,
        "wear_meaning": "Upper-arm sleeve between shoulder and elbow zone.",
        "whole_suit_role": "Keeps arm continuity without colliding with torso or forearm.",
    },
    "forearm": {
        "human_anchor": "{side}_forearm",
        "body_region": "arm",
        "body_chain": "{side}_arm",
        "chain_order": 2,
        "wear_meaning": "Forearm guard between elbow and wrist.",
        "whole_suit_role": "Maintains lower-arm line and hand clearance.",
    },
    "hand": {
        "human_anchor": "{side}_hand",
        "body_region": "hand",
        "body_chain": "{side}_arm",
        "chain_order": 3,
        "wear_meaning": "Hand or wrist guard at the end of the arm chain.",
        "whole_suit_role": "Terminus for arm length and wrist spacing.",
    },
    "thigh": {
        "human_anchor": "{side}_upper_leg",
        "body_region": "leg",
        "body_chain": "{side}_leg",
        "chain_order": 0,
        "wear_meaning": "Thigh armor over the upper leg.",
        "whole_suit_role": "Starts the leg chain below the waist while keeping inner-leg clearance.",
    },
    "shin": {
        "human_anchor": "{side}_lower_leg",
        "body_region": "leg",
        "body_chain": "{side}_leg",
        "chain_order": 1,
        "wear_meaning": "Shin armor over the lower leg.",
        "whole_suit_role": "Connects thigh and boot without knee/ankle crowding.",
    },
    "boot": {
        "human_anchor": "{side}_foot_ankle",
        "body_region": "foot",
        "body_chain": "{side}_leg",
        "chain_order": 2,
        "wear_meaning": "Boot shell around foot and ankle.",
        "whole_suit_role": "Grounding endpoint for the leg chain and full-suit stance.",
    },
}

HUMAN_CHAIN_REQUIREMENTS = (
    ("head_torso", ("helmet", "chest", "back", "waist")),
    ("left_arm", ("left_shoulder", "left_upperarm", "left_forearm", "left_hand")),
    ("right_arm", ("right_shoulder", "right_upperarm", "right_forearm", "right_hand")),
    ("left_leg", ("left_thigh", "left_shin", "left_boot")),
    ("right_leg", ("right_thigh", "right_shin", "right_boot")),
)

HUMAN_VERTICAL_ORDER_REQUIREMENTS = {
    "head_torso": ("helmet", "chest", "waist"),
    "left_arm": ("left_shoulder", "left_upperarm", "left_forearm", "left_hand"),
    "right_arm": ("right_shoulder", "right_upperarm", "right_forearm", "right_hand"),
    "left_leg": ("left_thigh", "left_shin", "left_boot"),
    "right_leg": ("right_thigh", "right_shin", "right_boot"),
}
SIDE_SIGN_TOLERANCE_M = 0.02
CENTERLINE_TOLERANCE_M = 0.08
MIN_VERTICAL_ORDER_GAP_M = 0.025

FIT_LINKS = (
    ("helmet_to_chest", "helmet", "chest", "y", -0.03, 0.16),
    ("chest_to_waist", "chest", "waist", "y", -0.02, 0.22),
    ("chest_to_back_depth", "chest", "back", "z", 0.18, 0.55),
    ("left_waist_to_thigh", "waist", "left_thigh", "y", -0.08, 0.12),
    ("right_waist_to_thigh", "waist", "right_thigh", "y", -0.08, 0.12),
    ("left_thigh_to_shin", "left_thigh", "left_shin", "y", -0.09, 0.08),
    ("right_thigh_to_shin", "right_thigh", "right_shin", "y", -0.09, 0.08),
    ("left_shin_to_boot", "left_shin", "left_boot", "y", -0.05, 0.08),
    ("right_shin_to_boot", "right_shin", "right_boot", "y", -0.05, 0.08),
    ("left_shoulder_to_upperarm", "left_shoulder", "left_upperarm", "y", -0.03, 0.12),
    ("right_shoulder_to_upperarm", "right_shoulder", "right_upperarm", "y", -0.03, 0.12),
    ("left_upperarm_to_forearm", "left_upperarm", "left_forearm", "y", -0.05, 0.12),
    ("right_upperarm_to_forearm", "right_upperarm", "right_forearm", "y", -0.05, 0.12),
    ("left_forearm_to_hand", "left_forearm", "left_hand", "y", -0.04, 0.10),
    ("right_forearm_to_hand", "right_forearm", "right_hand", "y", -0.04, 0.10),
    ("thigh_inner_clearance", "left_thigh", "right_thigh", "x", 0.14, 0.45),
    ("shin_inner_clearance", "left_shin", "right_shin", "x", 0.14, 0.46),
    ("boot_inner_clearance", "left_boot", "right_boot", "x", 0.12, 0.44),
)

GLOBAL_EXTENT_RANGES_M = {
    "height": (1.55, 2.10),
    "width": (0.80, 1.45),
    "depth": (0.45, 0.90),
}

SEAM_PAIRS = frozenset(
    frozenset((left, right))
    for _name, left, right, _axis, _min_gap, _max_gap in FIT_LINKS
    if left.startswith("left_") == right.startswith("left_")
    or left.startswith("right_") == right.startswith("right_")
    or left in {"helmet", "chest", "waist"}
)
MAX_ALLOWED_SEAM_DEPTH_M = 0.12
MAX_ALLOWED_SEAM_VOLUME_RATIO = 0.35
OBVIOUS_OVERLAP_MIN_DEPTH_M = 0.02
OBVIOUS_OVERLAP_MIN_VOLUME_RATIO = 0.02


class ContractParseError(ValueError):
    """Raised when a required Quest runtime constant cannot be parsed."""


@dataclass(frozen=True)
class Box:
    part: str
    center: tuple[float, float, float]
    size: tuple[float, float, float]
    min: tuple[float, float, float]
    max: tuple[float, float, float]
    volume: float


def collect_whole_suit_audit(
    runtime_source: str | Path = DEFAULT_RUNTIME_SOURCE,
    armor_root: str | Path | None = DEFAULT_ARMOR_ROOT,
) -> dict[str, Any]:
    """Collect a deterministic JSON-serializable whole-suit audit."""

    runtime_path = Path(runtime_source)
    contract = load_quest_runtime_contract(runtime_path)
    armor_parts = contract["armor_parts"]
    poses = contract["vr_body_part_poses"]
    adjustments = contract["quest_assembly_adjustments"]
    target_sizes = contract["quest_glb_target_sizes"]
    human_anchors = contract["quest_human_anchor_contract"]

    part_records: list[dict[str, Any]] = []
    boxes: dict[str, Box] = {}
    for part in armor_parts:
        pose = poses.get(part)
        size = target_sizes.get(part)
        adjustment = adjustments.get(part, (0.0, 0.0, 0.0))
        human_anchor = human_anchors.get(part, {})
        human_center = human_anchor.get("center_m")
        record: dict[str, Any] = {
            "part": part,
            "has_pose": pose is not None,
            "has_human_anchor_center": human_center is not None,
            "has_target_size": size is not None,
            "assembly_adjustment_m": _round_vec(adjustment),
        }
        if human_center is not None and size is not None:
            center = human_center
            center_source = "QUEST_HUMAN_ANCHOR_CONTRACT.center_m"
        elif pose is not None and size is not None:
            center = tuple(pose[index] + adjustment[index] for index in range(3))
            center_source = "VR_BODY_PART_POSES+QUEST_ASSEMBLY_ADJUSTMENTS"
        else:
            center = None
            center_source = None
        if center is not None and size is not None:
            box = _box_for_part(part, center, size)
            boxes[part] = box
            record.update(
                {
                    "center_m": _round_vec(center),
                    "center_source": center_source,
                    "target_size_m": _round_vec(size),
                    "aabb_m": _box_to_json(box),
                }
            )
        part_records.append(record)

    asset_checks = _collect_asset_checks(armor_parts, armor_root)
    asset_check_summary = _collect_asset_check_summary(asset_checks, armor_root)
    missing_pose_parts = [part for part in armor_parts if part not in poses and part not in human_anchors]
    missing_size_parts = [part for part in armor_parts if part not in target_sizes]
    missing_asset_parts = sorted({item["part"] for item in asset_checks if item["status"] == "missing"})

    fit_distances = _collect_fit_distances(boxes)
    symmetry_checks = _collect_symmetry_checks(boxes)
    global_extents = _collect_global_extents(boxes)
    interpenetrations = _collect_interpenetrations(boxes)
    human_anchor_contract = _collect_human_anchor_contract(armor_parts, boxes, fit_distances, human_anchors)

    failure_reasons = []
    if missing_pose_parts:
        failure_reasons.append("missing runtime body poses")
    if missing_size_parts:
        failure_reasons.append("missing Quest target sizes")
    if missing_asset_parts:
        failure_reasons.append("missing armor assets")
    if any(item["status"] == "fail" for item in fit_distances):
        failure_reasons.append("body-fit distances outside hard range")
    if any(item["status"] == "fail" for item in symmetry_checks):
        failure_reasons.append("left/right symmetry outside hard tolerance")
    if any(isinstance(item, dict) and item.get("status") == "fail" for item in global_extents.values()):
        failure_reasons.append("global suit extents outside human-fit envelope")
    if human_anchor_contract["status"] == "fail":
        failure_reasons.append("human anchor contract incomplete")
    obvious_interpenetrations = [item for item in interpenetrations if item["status"] == "fail"]
    if obvious_interpenetrations:
        failure_reasons.append("obvious non-seam interpenetration")

    warning_reasons = []
    if any(item["status"] == "warn" for item in interpenetrations):
        warning_reasons.append("joint seam overlap above preferred tolerance")

    status = "fail" if failure_reasons else "warn" if warning_reasons else "pass"
    return {
        "contract_version": CONTRACT_VERSION,
        "status": status,
        "ok": status != "fail",
        "failure_reasons": failure_reasons,
        "warning_reasons": warning_reasons,
        "audit_scope": AUDIT_SCOPE,
        "source": {
            "runtime_source": str(runtime_path),
            "armor_root": str(Path(armor_root)) if armor_root is not None else None,
            "runtime_constants": [
                "ARMOR_PARTS",
                "VR_BODY_PART_POSES",
                "QUEST_ASSEMBLY_ADJUSTMENTS",
                "QUEST_HUMAN_ANCHOR_CONTRACT",
                "QUEST_GLB_TARGET_SIZES",
            ],
        },
        "part_count": len([part for part in armor_parts if part in boxes]),
        "expected_part_count": len(armor_parts),
        "missing_pose_parts": missing_pose_parts,
        "missing_target_size_parts": missing_size_parts,
        "missing_asset_parts": missing_asset_parts,
        "global_extents_m": global_extents,
        "human_fit_distances_m": fit_distances,
        "human_anchor_contract": human_anchor_contract,
        "symmetry_checks": symmetry_checks,
        "asset_check_summary": asset_check_summary,
        "asset_checks": asset_checks,
        "interpenetration_checks": interpenetrations,
        "obvious_interpenetrations": obvious_interpenetrations,
        "parts": part_records,
    }


def load_quest_runtime_contract(runtime_source: str | Path) -> dict[str, Any]:
    text = Path(runtime_source).read_text(encoding="utf-8")
    armor_parts = _load_js_const(text, "ARMOR_PARTS")
    poses = _coerce_vec3_map(_load_js_const(text, "VR_BODY_PART_POSES"), "VR_BODY_PART_POSES")
    adjustments = _coerce_vec3_map(
        _load_js_const(text, "QUEST_ASSEMBLY_ADJUSTMENTS"),
        "QUEST_ASSEMBLY_ADJUSTMENTS",
    )
    target_sizes = _coerce_vec3_map(
        _load_js_const(text, "QUEST_GLB_TARGET_SIZES"),
        "QUEST_GLB_TARGET_SIZES",
    )
    human_anchors = _coerce_human_anchor_contract(
        _load_optional_js_const(text, "QUEST_HUMAN_ANCHOR_CONTRACT", {}),
        "QUEST_HUMAN_ANCHOR_CONTRACT",
    )
    if not isinstance(armor_parts, list) or not all(isinstance(part, str) for part in armor_parts):
        raise ContractParseError("ARMOR_PARTS must be a string array.")
    return {
        "armor_parts": armor_parts,
        "vr_body_part_poses": poses,
        "quest_assembly_adjustments": adjustments,
        "quest_human_anchor_contract": human_anchors,
        "quest_glb_target_sizes": target_sizes,
    }


def _load_optional_js_const(text: str, name: str, default: Any) -> Any:
    try:
        return _load_js_const(text, name)
    except ContractParseError as exc:
        if str(exc) == f"Missing required constant: {name}":
            return default
        raise


def _load_js_const(text: str, name: str) -> Any:
    literal = _extract_const_literal(text, name)
    jsonish = _js_literal_to_json(literal)
    try:
        return json.loads(jsonish)
    except json.JSONDecodeError as exc:
        raise ContractParseError(f"Could not parse {name}: {exc}") from exc


def _extract_const_literal(text: str, name: str) -> str:
    match = re.search(rf"\bconst\s+{re.escape(name)}\s*=", text)
    if not match:
        raise ContractParseError(f"Missing required constant: {name}")
    index = match.end()
    while index < len(text) and text[index].isspace():
        index += 1
    if index >= len(text) or text[index] not in "[{":
        raise ContractParseError(f"{name} must be an array or object literal.")

    opener = text[index]
    closer = "]" if opener == "[" else "}"
    depth = 0
    in_string: str | None = None
    escaped = False
    for cursor in range(index, len(text)):
        char = text[cursor]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == in_string:
                in_string = None
            continue
        if char in ('"', "'"):
            in_string = char
            continue
        if char == opener:
            depth += 1
        elif char == closer:
            depth -= 1
            if depth == 0:
                return text[index : cursor + 1]
    raise ContractParseError(f"Unterminated literal for {name}.")


def _js_literal_to_json(literal: str) -> str:
    jsonish = re.sub(r"([{\s,])([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', literal)
    jsonish = re.sub(r",(\s*[}\]])", r"\1", jsonish)
    return jsonish


def _coerce_vec3_map(raw: Any, field_name: str) -> dict[str, tuple[float, float, float]]:
    if not isinstance(raw, dict):
        raise ContractParseError(f"{field_name} must be an object.")
    result: dict[str, tuple[float, float, float]] = {}
    for key, value in raw.items():
        if not isinstance(value, list) or len(value) != 3:
            continue
        try:
            result[str(key)] = (float(value[0]), float(value[1]), float(value[2]))
        except (TypeError, ValueError):
            continue
    return result


def _coerce_human_anchor_contract(raw: Any, field_name: str) -> dict[str, dict[str, Any]]:
    if not isinstance(raw, dict):
        raise ContractParseError(f"{field_name} must be an object.")
    result: dict[str, dict[str, Any]] = {}
    for key, value in raw.items():
        if not isinstance(value, dict):
            continue
        entry: dict[str, Any] = {}
        center = value.get("center_m")
        if isinstance(center, list) and len(center) == 3:
            try:
                entry["center_m"] = (float(center[0]), float(center[1]), float(center[2]))
            except (TypeError, ValueError):
                pass
        for source_key, output_key in (
            ("anchor", "runtime_anchor"),
            ("side", "runtime_side"),
            ("wearIntent", "runtime_wear_intent"),
        ):
            source_value = value.get(source_key)
            if isinstance(source_value, str):
                entry[output_key] = source_value
        if entry:
            result[str(key)] = entry
    return result


def _box_for_part(part: str, center: tuple[float, float, float], size: tuple[float, float, float]) -> Box:
    half = tuple(max(float(size[index]), 0.0) / 2.0 for index in range(3))
    box_min = tuple(center[index] - half[index] for index in range(3))
    box_max = tuple(center[index] + half[index] for index in range(3))
    volume = math.prod(max(float(size[index]), 0.0) for index in range(3))
    return Box(part=part, center=center, size=size, min=box_min, max=box_max, volume=volume)


def _collect_asset_checks(armor_parts: list[str], armor_root: str | Path | None) -> list[dict[str, Any]]:
    if armor_root is None:
        return []
    root = Path(armor_root)
    checks = []
    for part in armor_parts:
        glb = root / part / f"{part}.glb"
        sidecar = root / part / f"{part}.modeler.json"
        missing = []
        if not glb.exists():
            missing.append("glb")
        if not sidecar.exists():
            missing.append("modeler_sidecar")
        checks.append(
            {
                "part": part,
                "status": "missing" if missing else "pass",
                "validation_scope": "existence-only",
                "glb_dimensions_verified": False,
                "note": "Asset pass only means expected files exist; GLB dimensions are not loaded or measured.",
                "missing": missing,
                "glb": str(glb),
                "modeler_sidecar": str(sidecar),
            }
        )
    return checks


def _collect_asset_check_summary(
    asset_checks: list[dict[str, Any]],
    armor_root: str | Path | None,
) -> dict[str, Any]:
    return {
        "enabled": armor_root is not None,
        "validation_scope": "existence-only",
        "glb_dimensions_verified": False,
        "glb_bounds_verified": False,
        "message": (
            "Asset checks verify expected GLB and modeler sidecar paths exist only; "
            "they do not parse GLB geometry, measure mesh bounds, or compare actual mesh dimensions."
        ),
        "checked_part_count": len(asset_checks),
    }


def _collect_fit_distances(boxes: dict[str, Box]) -> list[dict[str, Any]]:
    distances = []
    for name, part_a, part_b, axis, min_gap, max_gap in FIT_LINKS:
        box_a = boxes.get(part_a)
        box_b = boxes.get(part_b)
        if box_a is None or box_b is None:
            distances.append(
                {
                    "name": name,
                    "pair": [part_a, part_b],
                    "axis": axis,
                    "validation_scope": "primary-axis-only",
                    "unchecked_secondary_axes": [candidate for candidate in AXES if candidate != axis],
                    "status": "fail",
                    "reason": "missing placement box",
                }
            )
            continue
        gap = _signed_axis_gap(box_a, box_b, AXES.index(axis))
        status = "pass" if min_gap <= gap <= max_gap else "fail"
        distances.append(
            {
                "name": name,
                "pair": [part_a, part_b],
                "axis": axis,
                "validation_scope": "primary-axis-only",
                "unchecked_secondary_axes": [candidate for candidate in AXES if candidate != axis],
                "secondary_axis_note": (
                    "Pass only covers the named primary axis; secondary axes drift must be checked "
                    "with symmetry, global extents, and Quest photo feedback."
                ),
                "signed_surface_gap_m": _round(gap),
                "accepted_range_m": [_round(min_gap), _round(max_gap)],
                "status": status,
            }
        )
    return distances


def _collect_human_anchor_contract(
    armor_parts: list[str],
    boxes: dict[str, Box],
    fit_distances: list[dict[str, Any]],
    runtime_anchors: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    armor_part_set = set(armor_parts)
    fit_links_by_part = _fit_link_names_by_part(fit_distances)
    anchors = [
        _human_anchor_for_part(part, boxes.get(part), fit_links_by_part.get(part, []), runtime_anchors.get(part, {}))
        for part in armor_parts
    ]
    unknown_parts = [anchor["part"] for anchor in anchors if anchor["inference_status"] == "unknown"]
    missing_required_parts = [
        part for part in CANONICAL_HUMAN_ANCHOR_PARTS if part not in armor_part_set
    ]
    chain_checks = _collect_human_chain_checks(armor_part_set, boxes)
    semantic_failures = [
        failure
        for check in chain_checks
        for failure in check.get("semantic_failures", [])
    ]
    status = (
        "fail"
        if unknown_parts
        or missing_required_parts
        or semantic_failures
        or any(check["status"] == "fail" for check in chain_checks)
        else "pass"
    )
    return {
        "contract_version": HUMAN_ANCHOR_CONTRACT_VERSION,
        "status": status,
        "inference_basis": (
            "runtime-contract+part-name-derived" if runtime_anchors else "part-name-derived"
        ),
        "scope": (
            "Maps Quest runtime part names to intended human anchors and wearable meaning; "
            "it does not inspect GLB mesh shape, skinning, or live body tracking."
        ),
        "global_intent": (
            "Optimize the armor as one humanoid wearable suit: head/torso, left/right arms, "
            "and left/right legs should read as connected body chains rather than independent local parts."
        ),
        "coverage_summary": {
            "required_part_count": len(CANONICAL_HUMAN_ANCHOR_PARTS),
            "known_anchor_count": len([anchor for anchor in anchors if anchor["inference_status"] == "known"]),
            "unknown_anchor_parts": unknown_parts,
            "missing_required_parts": missing_required_parts,
            "covered_body_chains": sorted(
                {anchor["body_chain"] for anchor in anchors if anchor.get("body_chain")}
            ),
            "runtime_anchor_center_count": len(
                [anchor for anchor in anchors if anchor.get("center_source") == "QUEST_HUMAN_ANCHOR_CONTRACT.center_m"]
            ),
        },
        "semantic_failures": semantic_failures,
        "chain_checks": chain_checks,
        "anchors": anchors,
    }


def _human_anchor_for_part(
    part: str,
    box: Box | None,
    fit_link_names: list[str],
    runtime_anchor: dict[str, Any],
) -> dict[str, Any]:
    side, base_name = _split_part_side(part)
    rule = PART_NAME_ANCHOR_RULES.get(base_name)
    if rule is None:
        return {
            "part": part,
            "part_name_base": base_name,
            "side": side,
            "inference_status": "unknown",
            "human_anchor": None,
            "body_region": None,
            "body_chain": None,
            "fit_links": fit_link_names,
            "has_placement_box": box is not None,
            "note": "No local part-name rule maps this part to a human anchor.",
        }

    anchor = {
        "part": part,
        "part_name_base": base_name,
        "side": side,
        "inference_status": "known",
        "human_anchor": _format_side_template(rule["human_anchor"], side),
        "base_human_anchor": rule["human_anchor"].replace("{side}_", ""),
        "body_region": rule["body_region"],
        "body_chain": _format_side_template(rule["body_chain"], side),
        "chain_order": rule["chain_order"],
        "wear_meaning": rule["wear_meaning"],
        "whole_suit_role": rule["whole_suit_role"],
        "fit_links": fit_link_names,
        "has_placement_box": box is not None,
        "mirror_part": _mirror_part_name(part),
    }
    for key in ("runtime_anchor", "runtime_side", "runtime_wear_intent"):
        if runtime_anchor.get(key):
            anchor[key] = runtime_anchor[key]
    if box is not None:
        anchor["center_m"] = _round_vec(box.center)
        anchor["target_size_m"] = _round_vec(box.size)
        if runtime_anchor.get("center_m") is not None:
            anchor["center_source"] = "QUEST_HUMAN_ANCHOR_CONTRACT.center_m"
    if runtime_anchor.get("runtime_side") and runtime_anchor.get("runtime_side") != side:
        anchor["metadata_warning"] = (
            f"runtime side {runtime_anchor.get('runtime_side')} does not match part-name side {side}"
        )
    return anchor


def _split_part_side(part: str) -> tuple[str, str]:
    if part.startswith("left_"):
        return "left", part[len("left_") :]
    if part.startswith("right_"):
        return "right", part[len("right_") :]
    return "center", part


def _format_side_template(value: str, side: str) -> str:
    if "{side}" not in value:
        return value
    if side not in {"left", "right"}:
        return value.replace("{side}", "center")
    return value.replace("{side}", side)


def _mirror_part_name(part: str) -> str | None:
    if part.startswith("left_"):
        return "right_" + part[len("left_") :]
    if part.startswith("right_"):
        return "left_" + part[len("right_") :]
    return None


def _fit_link_names_by_part(fit_distances: list[dict[str, Any]]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for item in fit_distances:
        name = str(item.get("name") or "")
        for part in item.get("pair", []):
            result.setdefault(str(part), []).append(name)
    return result


def _collect_human_chain_checks(
    armor_part_set: set[str],
    boxes: dict[str, Box],
) -> list[dict[str, Any]]:
    checks = []
    for chain, required_parts in HUMAN_CHAIN_REQUIREMENTS:
        present_parts = [part for part in required_parts if part in armor_part_set]
        missing_parts = [part for part in required_parts if part not in armor_part_set]
        missing_placement_parts = [part for part in present_parts if part not in boxes]
        semantic_failures = _collect_chain_semantic_failures(chain, required_parts, boxes)
        ordered_centers = [
            {"part": part, "center_m": _round_vec(boxes[part].center)}
            for part in required_parts
            if part in boxes
        ]
        checks.append(
            {
                "body_chain": chain,
                "required_parts": list(required_parts),
                "present_parts": present_parts,
                "missing_parts": missing_parts,
                "missing_placement_parts": missing_placement_parts,
                "ordered_centers_m": ordered_centers,
                "semantic_failures": semantic_failures,
                "status": "fail" if missing_parts or missing_placement_parts or semantic_failures else "pass",
            }
        )
    return checks


def _collect_chain_semantic_failures(
    chain: str,
    required_parts: tuple[str, ...],
    boxes: dict[str, Box],
) -> list[str]:
    failures: list[str] = []
    for part in required_parts:
        box = boxes.get(part)
        if box is None:
            continue
        side, _base_name = _split_part_side(part)
        if side == "left" and box.center[0] >= -SIDE_SIGN_TOLERANCE_M:
            failures.append(f"{part} x should be negative for a left-side wearable anchor")
        elif side == "right" and box.center[0] <= SIDE_SIGN_TOLERANCE_M:
            failures.append(f"{part} x should be positive for a right-side wearable anchor")
        elif side == "center" and abs(box.center[0]) > CENTERLINE_TOLERANCE_M:
            failures.append(f"{part} x should stay near the body centerline")

    vertical_order = HUMAN_VERTICAL_ORDER_REQUIREMENTS.get(chain, ())
    for upper, lower in zip(vertical_order, vertical_order[1:]):
        upper_box = boxes.get(upper)
        lower_box = boxes.get(lower)
        if upper_box is None or lower_box is None:
            continue
        if upper_box.center[1] <= lower_box.center[1] + MIN_VERTICAL_ORDER_GAP_M:
            failures.append(f"{upper} should sit above {lower} on the human body y-axis")

    chest = boxes.get("chest")
    back = boxes.get("back")
    if chain == "head_torso" and chest is not None and back is not None and chest.center[2] >= back.center[2]:
        failures.append("chest should sit in front of back on the human body z-axis")
    return failures


def _signed_axis_gap(box_a: Box, box_b: Box, axis_index: int) -> float:
    if box_a.center[axis_index] <= box_b.center[axis_index]:
        return box_b.min[axis_index] - box_a.max[axis_index]
    return box_a.min[axis_index] - box_b.max[axis_index]


def _collect_symmetry_checks(boxes: dict[str, Box]) -> list[dict[str, Any]]:
    checks = []
    for left, right in MIRROR_PAIRS:
        left_box = boxes.get(left)
        right_box = boxes.get(right)
        if left_box is None or right_box is None:
            checks.append(
                {
                    "pair": [left, right],
                    "status": "fail",
                    "reason": "missing placement box",
                }
            )
            continue
        center_delta = {
            "mirror_x_error": abs(left_box.center[0] + right_box.center[0]),
            "y_delta": abs(left_box.center[1] - right_box.center[1]),
            "z_delta": abs(left_box.center[2] - right_box.center[2]),
        }
        size_delta = {
            axis: abs(left_box.size[index] - right_box.size[index])
            for index, axis in enumerate(AXES)
        }
        status = (
            "fail"
            if center_delta["mirror_x_error"] > 0.035
            or center_delta["y_delta"] > 0.025
            or center_delta["z_delta"] > 0.025
            or max(size_delta.values()) > 0.010
            else "pass"
        )
        checks.append(
            {
                "pair": [left, right],
                "center_delta_m": {key: _round(value) for key, value in center_delta.items()},
                "size_delta_m": {key: _round(value) for key, value in size_delta.items()},
                "tolerances_m": {
                    "mirror_x_error": 0.035,
                    "y_delta": 0.025,
                    "z_delta": 0.025,
                    "size_axis_delta": 0.010,
                },
                "status": status,
            }
        )
    return checks


def _collect_global_extents(boxes: dict[str, Box]) -> dict[str, Any]:
    if not boxes:
        return {
            key: {"status": "fail", "reason": "no placement boxes"}
            for key in GLOBAL_EXTENT_RANGES_M
        }
    mins = [min(box.min[index] for box in boxes.values()) for index in range(3)]
    maxs = [max(box.max[index] for box in boxes.values()) for index in range(3)]
    values = {
        "width": maxs[0] - mins[0],
        "height": maxs[1] - mins[1],
        "depth": maxs[2] - mins[2],
    }
    extents: dict[str, Any] = {}
    for key, value in values.items():
        min_value, max_value = GLOBAL_EXTENT_RANGES_M[key]
        extents[key] = {
            "value_m": _round(value),
            "accepted_range_m": [_round(min_value), _round(max_value)],
            "status": "pass" if min_value <= value <= max_value else "fail",
        }
    extents["aabb_m"] = {
        "min": _round_vec(mins),
        "max": _round_vec(maxs),
    }
    return extents


def _collect_interpenetrations(boxes: dict[str, Box]) -> list[dict[str, Any]]:
    checks = []
    for part_a, part_b in itertools.combinations(sorted(boxes), 2):
        box_a = boxes[part_a]
        box_b = boxes[part_b]
        depths = [
            min(box_a.max[index], box_b.max[index]) - max(box_a.min[index], box_b.min[index])
            for index in range(3)
        ]
        if not all(depth > 0 for depth in depths):
            continue
        volume = math.prod(depths)
        min_volume = max(min(box_a.volume, box_b.volume), 1e-9)
        volume_ratio = volume / min_volume
        max_depth = max(depths)
        seam_pair = frozenset((part_a, part_b)) in SEAM_PAIRS
        if seam_pair:
            status = (
                "warn"
                if max_depth > MAX_ALLOWED_SEAM_DEPTH_M
                or volume_ratio > MAX_ALLOWED_SEAM_VOLUME_RATIO
                else "pass"
            )
            classification = "joint_seam_overlap"
        else:
            status = (
                "fail"
                if max_depth >= OBVIOUS_OVERLAP_MIN_DEPTH_M
                and volume_ratio >= OBVIOUS_OVERLAP_MIN_VOLUME_RATIO
                else "pass"
            )
            classification = "obvious_interpenetration" if status == "fail" else "minor_overlap"
        checks.append(
            {
                "pair": [part_a, part_b],
                "classification": classification,
                "overlap_depth_m": {
                    axis: _round(depths[index])
                    for index, axis in enumerate(AXES)
                },
                "max_overlap_depth_m": _round(max_depth),
                "overlap_volume_m3": _round(volume, digits=7),
                "min_part_volume_ratio": _round(volume_ratio, digits=4),
                "status": status,
            }
        )
    return checks


def _box_to_json(box: Box) -> dict[str, Any]:
    return {
        "min": _round_vec(box.min),
        "max": _round_vec(box.max),
        "volume_m3": _round(box.volume, digits=7),
    }


def _round(value: float, digits: int = 4) -> float:
    rounded = round(float(value), digits)
    return 0.0 if rounded == -0.0 else rounded


def _round_vec(values: Iterable[float], digits: int = 4) -> list[float]:
    return [_round(value, digits=digits) for value in values]


def render_markdown_report(audit: dict[str, Any]) -> str:
    scope = audit.get("audit_scope", {})
    asset_summary = audit.get("asset_check_summary", {})
    anchor_contract = audit.get("human_anchor_contract", {})
    lines = [
        "# Quest Whole-Suit Armor Audit",
        "",
        f"- Status: `{audit.get('status')}`",
        f"- Contract: `{audit.get('contract_version')}`",
        f"- Scope: `{scope.get('geometry_basis', 'target-contract-only')}`",
        f"- Confidence: {scope.get('confidence_level', 'coarse static CI gate')}",
        "",
        "## What pass means",
        "",
        str(scope.get("pass_meaning", AUDIT_SCOPE["pass_meaning"])),
        "",
        "## What pass does not guarantee",
        "",
    ]
    for limitation in scope.get("pass_does_not_guarantee", []):
        lines.append(f"- {limitation}")
    lines.extend(
        [
            "",
            "## Asset checks",
            "",
            f"- Scope: `{asset_summary.get('validation_scope', 'existence-only')}`",
            f"- GLB dimensions verified: `{str(asset_summary.get('glb_dimensions_verified', False)).lower()}`",
            f"- Note: {asset_summary.get('message', '')}",
            "",
            "## Fit links",
            "",
            (
                "Human-fit distances are primary-axis checks. A pass on a link does not prove that "
                "the secondary axes are visually aligned; use Quest photos for micro-adjustments."
            ),
            "",
            "| Link | Pair | Axis | Status |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in audit.get("human_fit_distances_m", []):
        pair = " / ".join(item.get("pair", []))
        lines.append(
            f"| {item.get('name')} | {pair} | {item.get('axis')} | {item.get('status')} |"
        )
    lines.extend(
        [
            "",
            "## Human anchor contract",
            "",
            f"- Status: `{anchor_contract.get('status')}`",
            f"- Basis: `{anchor_contract.get('inference_basis', 'part-name-derived')}`",
            f"- Intent: {anchor_contract.get('global_intent', '')}",
            "",
            "| Part | Human anchor | Chain | Meaning |",
            "| --- | --- | --- | --- |",
        ]
    )
    for item in anchor_contract.get("anchors", []):
        lines.append(
            "| {part} | {anchor} | {chain} | {meaning} |".format(
                part=item.get("part"),
                anchor=item.get("human_anchor") or "unknown",
                chain=item.get("body_chain") or "unknown",
                meaning=item.get("wear_meaning") or item.get("note") or "",
            )
        )
    lines.extend(
        [
            "",
            "## Summary",
            "",
            f"- Parts: {audit.get('part_count')} / {audit.get('expected_part_count')}",
            f"- Missing assets: {', '.join(audit.get('missing_asset_parts', [])) or 'none'}",
            f"- Obvious interpenetrations: {len(audit.get('obvious_interpenetrations', []))}",
            "",
        ]
    )
    return "\n".join(lines)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-source", type=Path, default=DEFAULT_RUNTIME_SOURCE)
    parser.add_argument("--armor-root", type=Path, default=DEFAULT_ARMOR_ROOT)
    parser.add_argument("--skip-asset-check", action="store_true")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--output", type=Path, help="Write JSON to this path instead of stdout.")
    parser.add_argument("--compact", action="store_true", help="Emit compact JSON.")
    parser.add_argument(
        "--fail-on",
        choices=("fail", "warn", "never"),
        default="fail",
        help="Exit non-zero for this status threshold.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    audit = collect_whole_suit_audit(
        runtime_source=args.runtime_source,
        armor_root=None if args.skip_asset_check else args.armor_root,
    )
    if args.format == "markdown":
        payload = render_markdown_report(audit)
    else:
        payload = json.dumps(
            audit,
            ensure_ascii=False,
            indent=None if args.compact else 2,
            sort_keys=True,
        )
    if not args.compact or args.format == "markdown":
        payload += "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    else:
        sys.stdout.write(payload)

    if args.fail_on == "never":
        return 0
    if audit["status"] == "fail":
        return 1
    if args.fail_on == "warn" and audit["status"] == "warn":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
