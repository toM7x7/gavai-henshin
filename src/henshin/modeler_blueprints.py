"""Modeler-facing armor part blueprint contracts."""

from __future__ import annotations

from typing import Any


BLUEPRINT_CONTRACT_VERSION = "modeler-part-blueprint.v1"
REFERENCE_HEIGHT_CM = 170
REFERENCE_UNIT = "meter_in_vrm_preview_space"
PREVIEW_CONTRACT = {
    "preview_role": "proxy_envelope_only",
    "do_not_model": ["transparent blue boxes", "stand pole", "floor grid", "height guide"],
    "authoring_target": "GLB/glTF hard-surface armor fitted to VRM body",
    "handoff_status": "draft_ready_requires_silhouette_review",
    "blocking_gates": ["fit_clearance", "pivot_axis", "material_slots", "silhouette_review"],
}

_CLEARANCE_BY_CATEGORY = {
    "head": 0.018,
    "torso": 0.024,
    "dorsal": 0.026,
    "waist": 0.022,
    "shoulder": 0.028,
    "arm": 0.018,
    "hand": 0.014,
    "leg": 0.02,
    "foot": 0.018,
}

_THICKNESS_BY_CATEGORY = {
    "head": 0.035,
    "torso": 0.045,
    "dorsal": 0.05,
    "waist": 0.034,
    "shoulder": 0.038,
    "arm": 0.028,
    "hand": 0.02,
    "leg": 0.03,
    "foot": 0.032,
}

_TRIANGLE_BUDGET_BY_CATEGORY = {
    "head": 1800,
    "torso": 1800,
    "dorsal": 1600,
    "waist": 1200,
    "shoulder": 900,
    "arm": 1100,
    "hand": 700,
    "leg": 1100,
    "foot": 900,
}

_MIRROR_PAIRS = {
    "left_shoulder": "right_shoulder",
    "right_shoulder": "left_shoulder",
    "left_upperarm": "right_upperarm",
    "right_upperarm": "left_upperarm",
    "left_forearm": "right_forearm",
    "right_forearm": "left_forearm",
    "left_hand": "right_hand",
    "right_hand": "left_hand",
    "left_thigh": "right_thigh",
    "right_thigh": "left_thigh",
    "left_shin": "right_shin",
    "right_shin": "left_shin",
    "left_boot": "right_boot",
    "right_boot": "left_boot",
}

_CATEGORY_BY_MODULE = {
    "helmet": "head",
    "chest": "torso",
    "back": "dorsal",
    "waist": "waist",
    "left_shoulder": "shoulder",
    "right_shoulder": "shoulder",
    "left_upperarm": "arm",
    "right_upperarm": "arm",
    "left_forearm": "arm",
    "right_forearm": "arm",
    "left_hand": "hand",
    "right_hand": "hand",
    "left_thigh": "leg",
    "right_thigh": "leg",
    "left_shin": "leg",
    "right_shin": "leg",
    "left_boot": "foot",
    "right_boot": "foot",
}

_WAVE_BY_MODULE = {
    "chest": "wave_1_core",
    "back": "wave_1_core",
    "waist": "wave_1_core",
    "left_shoulder": "wave_1_arm_seams",
    "right_shoulder": "wave_1_arm_seams",
    "left_upperarm": "wave_1_arm_seams",
    "right_upperarm": "wave_1_arm_seams",
    "left_forearm": "wave_1_arm_seams",
    "right_forearm": "wave_1_arm_seams",
    "left_thigh": "wave_2_lower_body",
    "right_thigh": "wave_2_lower_body",
    "left_shin": "wave_2_lower_body",
    "right_shin": "wave_2_lower_body",
    "left_boot": "wave_2_lower_body",
    "right_boot": "wave_2_lower_body",
    "helmet": "wave_3_head_hands",
    "left_hand": "wave_3_head_hands",
    "right_hand": "wave_3_head_hands",
}


def build_modeler_blueprint_catalog(
    part_catalog: dict[str, Any],
    *,
    selected_modules: list[str] | None = None,
    module_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return quantitative armor-part specs for external model production."""

    selected = (
        None
        if selected_modules is None
        else {str(module).strip() for module in selected_modules if str(module).strip()}
    )
    overrides = module_overrides if isinstance(module_overrides, dict) else {}
    source_parts = part_catalog.get("parts") if isinstance(part_catalog.get("parts"), list) else []
    parts = []
    for part in source_parts:
        if not isinstance(part, dict):
            continue
        module = _module_id(part)
        if not module:
            continue
        if selected is not None and module not in selected:
            continue
        module_override = overrides.get(module)
        if not isinstance(module_override, dict):
            module_override = None
        parts.append(_part_blueprint(part, module_override=module_override))
    return {
        "contract_version": BLUEPRINT_CONTRACT_VERSION,
        "catalog_id": part_catalog.get("catalog_id"),
        "reference_body": {
            "height_cm": REFERENCE_HEIGHT_CM,
            "unit": REFERENCE_UNIT,
            "pose": "Forge display A-pose for review; runtime attaches to VRM humanoid bones.",
        },
        "preview_contract": dict(PREVIEW_CONTRACT),
        "coordinate_system": {
            "local_y": "proximal_to_distal_or_vertical_fit_axis",
            "local_z": "visible_outward_surface",
            "origin": "part_center_after_transforms_applied",
            "scale_rule": "apply transforms before GLB export; runtime may uniformly scale by wearer height",
        },
        "deliverables": {
            "source": "viewer/assets/armor-parts/<module>/source/<module>.blend",
            "runtime": "viewer/assets/armor-parts/<module>/<module>.glb",
            "sidecar": "viewer/assets/armor-parts/<module>/<module>.modeler.json",
            "preview": "viewer/assets/armor-parts/<module>/preview/<module>.mesh.json",
            "texture_directory": "viewer/assets/armor-parts/<module>/textures/",
            "texture_provider_profile": "nano_banana",
            "textures": ["base_color", "emissive_mask", "normal_optional", "roughness_optional"],
            "review_views": ["front", "side", "back", "three_quarter"],
        },
        "qa_gates": [
            "stable_part_name",
            "bbox_within_target_envelope",
            "non_overlapping_uv0",
            "single_surface_base_material_or_declared_slots",
            "mirror_pair_dimension_delta_below_3_percent",
            "no_body_intersection_at_reference_pose",
        ],
        "part_count": len(parts),
        "parts": parts,
    }


def _part_blueprint(part: dict[str, Any], *, module_override: dict[str, Any] | None = None) -> dict[str, Any]:
    module = _module_id(part)
    category = str(part.get("category") or _CATEGORY_BY_MODULE.get(module, "armor"))
    normalized_category = _CATEGORY_BY_MODULE.get(module, category)
    metrics = _asset_metrics(part)
    bbox = _bbox_dimensions(metrics)
    fit = _effective_dict(part, module_override, "fit")
    anchor = _effective_dict(part, module_override, "vrm_anchor")
    asset_ref = _effective_str(module_override, "asset_ref", f"viewer/assets/meshes/{module}.mesh.json")
    attachment_slot = _effective_str(module_override, "attachment_slot", str(part.get("socket") or module))
    return {
        "module": module,
        "part_id": part.get("part_id"),
        "display_name": part.get("display_name") or module,
        "category": normalized_category,
        "preview_role": PREVIEW_CONTRACT["preview_role"],
        "handoff_status": PREVIEW_CONTRACT["handoff_status"],
        "side": part.get("side") or "center",
        "socket": attachment_slot,
        "wave": _WAVE_BY_MODULE.get(module, "wave_later"),
        "mirror_of": _MIRROR_PAIRS.get(module),
        "fit_reference": {
            "shape": fit.get("shape"),
            "source": fit.get("source"),
            "attach": fit.get("attach"),
            "offset_y": fit.get("offsetY", 0),
            "z_offset": fit.get("zOffset", 0),
            "scale": fit.get("scale"),
            "follow": fit.get("follow"),
            "min_scale": fit.get("minScale"),
        },
        "vrm_attachment": {
            "primary_bone": anchor.get("bone"),
            "offset_m": anchor.get("offset", [0, 0, 0]),
            "rotation_deg": anchor.get("rotation", [0, 0, 0]),
            "fallback_bones": part.get("bone_fallbacks") or [],
        },
        "target_envelope": {
            "unit": REFERENCE_UNIT,
            "source_bbox_m": bbox,
            "source_bbox_role": "seed_proxy_measurement_not_authoring_target",
            "authoring_target_m": _reference_target_dimensions(module),
            "authoring_target_basis": "Forge reference VRM metrics at 170cm; use as first-pass external model envelope",
            "clearance_from_body_m": _CLEARANCE_BY_CATEGORY.get(normalized_category, 0.02),
            "shell_thickness_target_m": _THICKNESS_BY_CATEGORY.get(normalized_category, 0.03),
            "fit_scale": fit.get("scale"),
            "min_scale": fit.get("minScale"),
        },
        "mesh_requirements": {
            "runtime_format": "glTF 2.0 GLB",
            "preview_format": "mesh.v1",
            "max_triangles": _TRIANGLE_BUDGET_BY_CATEGORY.get(normalized_category, 1200),
            "max_materials": 3,
            "apply_transforms": True,
            "pivot": "centered; no hidden DCC offsets",
            "naming": f"armor_{module}_v001",
        },
        "uv_requirements": {
            "uv0_required": True,
            "base_color_px": 2048,
            "emissive_mask_px": 2048,
            "non_overlap": True,
            "texel_density": "consistent inside mirror pair and adjacent seam pair",
            "seam_priority": _seam_priority(module),
        },
        "runtime_bindings": {
            "asset_ref": asset_ref,
            "external_glb_target": f"viewer/assets/armor-parts/{module}/{module}.glb",
            "source_target": f"viewer/assets/armor-parts/{module}/source/{module}.blend",
            "texture_target_dir": f"viewer/assets/armor-parts/{module}/textures/",
            "texture_path": f"SuitSpec.modules.{module}.texture_path",
            "material_slots": part.get("material_slot_bindings") or [],
        },
        "modeler_notes": _modeler_notes(module, normalized_category),
    }


def _module_id(part: dict[str, Any]) -> str:
    return str(part.get("module") or "").strip()


def _asset_metrics(part: dict[str, Any]) -> dict[str, Any]:
    asset = part.get("asset") if isinstance(part.get("asset"), dict) else {}
    metrics = asset.get("metrics") if isinstance(asset.get("metrics"), dict) else {}
    return metrics


def _effective_dict(
    part: dict[str, Any],
    module_override: dict[str, Any] | None,
    key: str,
) -> dict[str, Any]:
    override_value = module_override.get(key) if isinstance(module_override, dict) else None
    if isinstance(override_value, dict):
        return override_value
    part_value = part.get(key)
    return part_value if isinstance(part_value, dict) else {}


def _effective_str(module_override: dict[str, Any] | None, key: str, fallback: str) -> str:
    value = module_override.get(key) if isinstance(module_override, dict) else None
    text = str(value or "").strip()
    return text or fallback


def _bbox_dimensions(metrics: dict[str, Any]) -> dict[str, float | None]:
    bbox_min = metrics.get("local_bbox_min") if isinstance(metrics.get("local_bbox_min"), list) else []
    bbox_max = metrics.get("local_bbox_max") if isinstance(metrics.get("local_bbox_max"), list) else []
    if len(bbox_min) < 3 or len(bbox_max) < 3:
        return {"x": None, "y": None, "z": None}
    return {
        "x": _round_m(float(bbox_max[0]) - float(bbox_min[0])),
        "y": _round_m(float(bbox_max[1]) - float(bbox_min[1])),
        "z": _round_m(float(bbox_max[2]) - float(bbox_min[2])),
    }


def _round_m(value: float) -> float:
    return round(max(value, 0.0), 4)


def _reference_target_dimensions(module: str) -> dict[str, float]:
    shoulder = 0.68
    torso = 0.78
    head = 0.20
    upper_arm = 0.34
    forearm = 0.34
    thigh = 0.46
    shin = 0.46
    dimensions = {
        "helmet": (shoulder * 0.42, max(head * 1.7, 0.28), shoulder * 0.38),
        "chest": (shoulder * 0.94, torso * 0.64, shoulder * 0.24),
        "back": (shoulder * 0.88, torso * 0.66, shoulder * 0.2),
        "waist": (shoulder * 0.72, torso * 0.22, shoulder * 0.28),
        "left_shoulder": (shoulder * 0.28, shoulder * 0.18, shoulder * 0.24),
        "right_shoulder": (shoulder * 0.28, shoulder * 0.18, shoulder * 0.24),
        "left_upperarm": (shoulder * 0.16, upper_arm * 0.86, shoulder * 0.16),
        "right_upperarm": (shoulder * 0.16, upper_arm * 0.86, shoulder * 0.16),
        "left_forearm": (shoulder * 0.15, forearm * 0.82, shoulder * 0.15),
        "right_forearm": (shoulder * 0.15, forearm * 0.82, shoulder * 0.15),
        "left_hand": (shoulder * 0.17, shoulder * 0.12, shoulder * 0.2),
        "right_hand": (shoulder * 0.17, shoulder * 0.12, shoulder * 0.2),
        "left_thigh": (shoulder * 0.2, thigh * 0.86, shoulder * 0.19),
        "right_thigh": (shoulder * 0.2, thigh * 0.86, shoulder * 0.19),
        "left_shin": (shoulder * 0.17, shin * 0.86, shoulder * 0.17),
        "right_shin": (shoulder * 0.17, shin * 0.86, shoulder * 0.17),
        "left_boot": (shoulder * 0.18, shoulder * 0.13, shoulder * 0.42),
        "right_boot": (shoulder * 0.18, shoulder * 0.13, shoulder * 0.42),
    }.get(module, (shoulder * 0.2, shoulder * 0.2, shoulder * 0.2))
    return {"x": _round_m(dimensions[0]), "y": _round_m(dimensions[1]), "z": _round_m(dimensions[2])}


def _seam_priority(module: str) -> list[str]:
    seams = {
        "helmet": ["helmet_to_neck", "visor"],
        "chest": ["chest_to_back", "chest_to_waist", "shoulder_socket"],
        "back": ["back_to_chest", "backpack_mount"],
        "waist": ["waist_to_chest", "waist_to_thigh"],
        "left_shoulder": ["shoulder_to_upperarm"],
        "right_shoulder": ["shoulder_to_upperarm"],
        "left_upperarm": ["shoulder_to_upperarm", "upperarm_to_forearm"],
        "right_upperarm": ["shoulder_to_upperarm", "upperarm_to_forearm"],
        "left_forearm": ["upperarm_to_forearm", "forearm_to_hand"],
        "right_forearm": ["upperarm_to_forearm", "forearm_to_hand"],
        "left_hand": ["forearm_to_hand"],
        "right_hand": ["forearm_to_hand"],
        "left_thigh": ["waist_to_thigh", "thigh_to_shin"],
        "right_thigh": ["waist_to_thigh", "thigh_to_shin"],
        "left_shin": ["thigh_to_shin", "shin_to_boot"],
        "right_shin": ["thigh_to_shin", "shin_to_boot"],
        "left_boot": ["shin_to_boot", "sole_clearance"],
        "right_boot": ["shin_to_boot", "sole_clearance"],
    }
    return seams.get(module, ["outer_silhouette"])


def _modeler_notes(module: str, category: str) -> list[str]:
    notes = [
        "Preserve the body-conforming base suit as the inner layer; this part sits above it.",
        "Leave enough negative space for the VRM body surface and animation deformation.",
        "Keep the readable tokusatsu silhouette bright and non-hostile.",
    ]
    if category in {"arm", "leg"}:
        notes.append("Use segmented hard panels instead of one rigid tube when bending visibility matters.")
    if module in {"chest", "back", "waist"}:
        notes.append(
            "Treat torso pieces as a connected shell set; seams must read cleanly from front and mirror views."
        )
    if category == "head":
        notes.append("Keep visor and helmet shell as separable material zones for later emissive mask work.")
    return notes
