"""Runtime package normalization for Quest/Web suit viewers."""

from __future__ import annotations

import copy
import json
import struct
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from .armor_fit_contract import (
    body_surface_fit_policy_for_part,
    build_body_fit_contract,
    clamp_surface_offset_for_part,
    visual_layer_slot_summary,
)
from .modeler_blueprints import _reference_target_dimensions
from .uv_contracts import resolve_uv_contract, serialize_uv_contract


DEFAULT_VISUAL_LAYER_CONTRACT = "base-suit-overlay.v1"
DEFAULT_REQUIRED_LAYERS = ["base_suit_surface", "armor_overlay_parts"]
DEFAULT_REQUIRED_OVERLAY_PARTS = ["back", "chest", "helmet"]
GLB_MAGIC = b"glTF"
GLB_VERSION = 2
GLB_JSON_CHUNK_TYPE = 0x4E4F534A
MODELER_SIDECAR_CONTRACT_VERSIONS = {
    "modeler-part-sidecar.v1",
    "modeler-part-variant-sidecar.v1",
    "modeler-topping-sidecar.v1",
}
MODELER_SIDECAR_COORDINATE_FRAMES = {
    "glTF Y-up; x=lateral, y=vertical, z=outward",
    "glTF Y-up export; authored x=lateral, y=vertical, z=outward",
    "parent-module local authored frame; glTF Y-up export",
    "vrm_humanoid_local_y_up_z_front",
}
PER_PART_TEXTURE_CONTRACT_VERSION = "web-forge-per-part-texture.v1"


def build_runtime_suit_package(
    *,
    suitspec: dict[str, Any],
    manifest: dict[str, Any] | None = None,
    visual_layers: dict[str, Any] | None = None,
    render_contract: dict[str, Any] | None = None,
    model_quality_gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the normalized package a runtime should consume.

    SuitSpec remains the editing/forge working contract. SuitManifest remains the
    runtime canonical contract. This package is the narrow import shape for
    Quest/Web/Unity adapters so they do not each rediscover merge rules.
    """

    normalized_suitspec = _clone(suitspec)
    normalized_manifest = merge_suitspec_surface_into_manifest(
        manifest or {},
        normalized_suitspec,
    )
    overlay_parts = _enabled_overlay_parts(normalized_suitspec)
    body_fit_contract = build_body_fit_contract(normalized_suitspec, selected_slots=overlay_parts)
    contract = _normalize_render_contract(render_contract, overlay_parts)
    layers = _normalize_visual_layers(visual_layers, normalized_suitspec, overlay_parts)
    layers.setdefault("armor_overlay", {})["body_fit_slots"] = visual_layer_slot_summary(body_fit_contract)
    render_placements = build_render_placements(normalized_suitspec, body_fit_contract)
    variant_render_placements = _normalize_variant_render_placements(
        _variant_render_placement_sources(normalized_suitspec, layers),
        overlay_parts=overlay_parts,
    )
    selected_variant_keys = _selected_variant_keys_from_render_placements(render_placements)
    selected_variant_render_placements = _selected_variant_render_placements(
        selected_variant_keys,
        variant_render_placements,
    )
    variant_placement_snapshot = _variant_placement_snapshot(
        selected_variant_keys=selected_variant_keys,
        render_placements=render_placements,
        variant_render_placements=variant_render_placements,
    )
    armor_overlay = layers.setdefault("armor_overlay", {})
    armor_overlay["render_placements"] = _clone(render_placements)
    armor_overlay["selected_variant_keys"] = _clone(selected_variant_keys)
    armor_overlay["variant_render_placements"] = _clone(variant_render_placements)
    armor_overlay["selected_variant_render_placements"] = _clone(selected_variant_render_placements)
    armor_overlay["variant_placement_snapshot"] = _clone(variant_placement_snapshot)
    per_part_texture_contracts = _runtime_per_part_texture_contracts(
        normalized_suitspec,
        layers,
        overlay_parts=overlay_parts,
        render_placements=render_placements,
    )
    armor_overlay["per_part_texture_contract"] = PER_PART_TEXTURE_CONTRACT_VERSION
    armor_overlay["per_part_texture_contracts"] = _clone(per_part_texture_contracts)
    contract["render_placement_contract"] = "runtime-render-placement.v1"
    contract["render_placement_parts"] = sorted(render_placements)
    contract["variant_render_placement_contract"] = "runtime-render-placement.v1"
    contract["variant_render_placement_parts"] = sorted(variant_render_placements)
    contract["selected_variant_render_placement_parts"] = sorted(selected_variant_render_placements)
    contract["per_part_texture_contract"] = PER_PART_TEXTURE_CONTRACT_VERSION
    contract["per_part_texture_contract_parts"] = sorted(per_part_texture_contracts)
    surface_checks = {
        part: _runtime_surface_check(normalized_manifest.get("parts", {}).get(part, {}))
        for part in overlay_parts
    }
    visible_overlay_parts = [part for part in overlay_parts if surface_checks[part]["ok"]]
    runtime_surface_failures = {
        part: check for part, check in surface_checks.items() if not check["ok"]
    }
    missing_required = [
        part for part in contract["required_overlay_parts"] if part not in visible_overlay_parts
    ]
    fit_validation = body_fit_contract["validation"]
    quality_gate = _clone(model_quality_gate) if isinstance(model_quality_gate, dict) else None
    quality_status = str((quality_gate or {}).get("status") or "unknown")
    texture_lock_allowed = bool((quality_gate or {}).get("texture_lock_allowed"))
    return {
        "contract_version": contract["contract_version"],
        "suitspec": normalized_suitspec,
        "manifest": normalized_manifest,
        "visual_layers": layers,
        "render_contract": contract,
        "render_placements": render_placements,
        "selected_variant_keys": selected_variant_keys,
        "selected_variant_render_placements": selected_variant_render_placements,
        "variant_placement_snapshot": variant_placement_snapshot,
        "per_part_texture_contracts": per_part_texture_contracts,
        "body_fit_contract": body_fit_contract,
        "model_quality_gate": quality_gate,
        "runtime_checks": {
            "vrm_only_is_valid": False,
            "required_layers": contract["required_layers"],
            "enabled_overlay_parts": overlay_parts,
            "visible_overlay_parts": visible_overlay_parts,
            "visible_overlay_count": len(visible_overlay_parts),
            "runtime_surface_failures": runtime_surface_failures,
            "runtime_surface_failure_count": len(runtime_surface_failures),
            "invalid_overlay_parts": sorted(runtime_surface_failures),
            "minimum_visible_overlay_parts": contract["minimum_visible_overlay_parts"],
            "missing_required_overlay_parts": missing_required,
            "body_fit_contract_version": body_fit_contract["contract_version"],
            "missing_required_body_fit_slots": fit_validation["missing_required_slots"],
            "missing_mirror_pairs": fit_validation["missing_mirror_pairs"],
            "body_fit_core_ready": fit_validation["can_render_core"],
            "body_fit_pairs_balanced": fit_validation["balanced_pairs"],
            "selected_variant_render_placement_parts": sorted(selected_variant_render_placements),
            "missing_selected_variant_render_placements": variant_placement_snapshot["missing_selected_variant_render_placements"],
            "variant_render_placement_mismatches": variant_placement_snapshot["mismatched_selected_variant_render_placements"],
            "per_part_texture_contract_parts": sorted(per_part_texture_contracts),
            "model_quality_gate_status": quality_status,
            "model_quality_ready": quality_status == "pass",
            "texture_lock_allowed": texture_lock_allowed,
            "can_render_runtime_suit": fit_validation["can_render_core"]
            and not missing_required
            and len(visible_overlay_parts) >= contract["minimum_visible_overlay_parts"],
        },
    }


def _runtime_per_part_texture_contracts(
    suitspec: dict[str, Any],
    layers: dict[str, Any],
    *,
    overlay_parts: list[str],
    render_placements: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    normalized: dict[str, dict[str, Any]] = {}
    for source in _runtime_per_part_texture_contract_sources(suitspec, layers):
        if not isinstance(source, dict):
            continue
        for part in overlay_parts:
            record = source.get(part)
            if not isinstance(record, dict):
                continue
            normalized[part] = _normalize_runtime_part_texture_contract(
                part,
                record,
                suitspec=suitspec,
                render_placement=render_placements.get(part, {}),
            )
    for part in overlay_parts:
        normalized.setdefault(
            part,
            _runtime_inferred_part_texture_contract(
                part,
                suitspec=suitspec,
                render_placement=render_placements.get(part, {}),
            ),
        )
    return dict(sorted(normalized.items()))


def _runtime_per_part_texture_contract_sources(
    suitspec: dict[str, Any],
    layers: dict[str, Any],
) -> list[Any]:
    generation = suitspec.get("generation") if isinstance(suitspec.get("generation"), dict) else {}
    surface_hints = generation.get("surface_design_hints") if isinstance(generation.get("surface_design_hints"), dict) else {}
    job_defaults = generation.get("job_defaults") if isinstance(generation.get("job_defaults"), dict) else {}
    job_hints = job_defaults.get("surface_design_hints") if isinstance(job_defaults.get("surface_design_hints"), dict) else {}
    surface_plan = generation.get("surface_plan") if isinstance(generation.get("surface_plan"), dict) else {}
    plan_overlay = surface_plan.get("armor_overlay") if isinstance(surface_plan.get("armor_overlay"), dict) else {}
    layer_overlay = layers.get("armor_overlay") if isinstance(layers.get("armor_overlay"), dict) else {}
    return [
        surface_hints.get("per_part_texture_contracts"),
        job_hints.get("per_part_texture_contracts"),
        plan_overlay.get("per_part_texture_contracts"),
        layer_overlay.get("per_part_texture_contracts"),
    ]


def _normalize_runtime_part_texture_contract(
    part: str,
    record: dict[str, Any],
    *,
    suitspec: dict[str, Any],
    render_placement: dict[str, Any],
) -> dict[str, Any]:
    normalized = _clone(record)
    inferred = _runtime_inferred_part_texture_contract(
        part,
        suitspec=suitspec,
        render_placement=render_placement,
    )
    normalized["contract_version"] = str(normalized.get("contract_version") or PER_PART_TEXTURE_CONTRACT_VERSION)
    normalized["part"] = part
    for key in ("provider_profile", "texture_prompt_contract", "texture_mode", "selected_variant_key", "asset_ref"):
        if not normalized.get(key):
            normalized[key] = inferred.get(key)
    for key in ("shape_role", "uv_availability", "uv_policy", "material_hints"):
        if not isinstance(normalized.get(key), dict):
            normalized[key] = inferred[key]
        else:
            normalized[key] = _merge_missing_dict(normalized[key], inferred[key])
    if not str(normalized.get("texture_prompt") or "").strip():
        normalized["texture_prompt"] = inferred["texture_prompt"]
    return normalized


def _runtime_inferred_part_texture_contract(
    part: str,
    *,
    suitspec: dict[str, Any],
    render_placement: dict[str, Any],
) -> dict[str, Any]:
    modules = suitspec.get("modules") if isinstance(suitspec.get("modules"), dict) else {}
    module = modules.get(part) if isinstance(modules.get(part), dict) else {}
    asset_ref = str(render_placement.get("asset_ref") or module.get("asset_ref") or "")
    sidecar = _modeler_sidecar_from_asset_ref(asset_ref) or {}
    surface_check = _runtime_surface_check({"enabled": True, "asset_ref": asset_ref})
    asset_case = _texture_asset_surface_case(asset_ref, sidecar, surface_check)
    policy = body_surface_fit_policy_for_part(part) or {}
    uv_contract = serialize_uv_contract(resolve_uv_contract(suitspec, part))
    qa = sidecar.get("qa_self_report") if isinstance(sidecar.get("qa_self_report"), dict) else {}
    uv0_status = str(qa.get("non_overlapping_uv0") or asset_case["uv0_status"]).strip().lower()
    material_zones = sidecar.get("material_zones") if isinstance(sidecar.get("material_zones"), list) else []
    material_notes = sidecar.get("surface_material_hints") if isinstance(sidecar.get("surface_material_hints"), dict) else {}
    selected_variant_key = str(render_placement.get("selected_variant_key") or "")
    shape_role = {
        "contract_version": "part-shape-role.v1",
        "surface_role": policy.get("role") or "",
        "body_anchor": render_placement.get("body_anchor"),
        "coverage": [],
        "target_contact": policy.get("target_contact"),
        "fit_basis": "runtime_render_placement+body_surface_fit_policy",
    }
    uv_availability = {
        "texture_mode": "mesh_uv",
        "asset_ref": asset_ref,
        "asset_format": asset_case["asset_format"],
        "asset_surface_case": asset_case["asset_surface_case"],
        "uv0_status": uv0_status,
        "uv0_source": "modeler_sidecar.qa_self_report.non_overlapping_uv0" if qa else asset_case["uv0_source"],
        "uv_guide_expected": True,
        "surface_check_ok": surface_check["ok"],
        "surface_failure_reasons": list(surface_check["reasons"]),
        "can_generate_mesh_uv_texture": asset_case["can_generate_mesh_uv_texture"] and uv0_status not in {"fail", "failed", "missing", "not_applicable", "unavailable"},
    }
    uv_policy = {
        "contract_version": "part-uv-policy.v1",
        "source_contract": "uv_contracts.resolve_uv_contract",
        "fill_ratio_target": uv_contract.get("fill_ratio_target"),
        "blank_area_max_percent": uv_contract.get("blank_area_max_percent"),
        "seam_safe_margin_percent": uv_contract.get("seam_safe_margin_percent"),
        "primary_motif_zone": uv_contract.get("primary_motif_zone"),
        "low_frequency_zone": uv_contract.get("low_frequency_zone"),
        "panel_flow_direction": uv_contract.get("panel_flow_direction"),
        "forbidden_detail_zone": uv_contract.get("forbidden_detail_zone"),
        "island_layout_rule": uv_contract.get("island_layout_rule"),
    }
    material_hints = {
        "contract_version": "part-material-hints.v1",
        "material_zones": [str(zone) for zone in material_zones if str(zone).strip()] or ["base_surface", "accent", "emissive", "trim"],
        "surface_material_hints": _clone(material_notes),
        "motif_surface_zone": "",
        "default_material_language": "Bright hard-shell base surface, controlled accent trim, thin emissive masks, and dark separation material.",
    }
    prompt = (
        f"Per-part texture target: {part} with selected variant {selected_variant_key or 'base'}. "
        f"Asset surface case: {uv_availability['asset_surface_case']} ({uv_availability['asset_format']}); "
        f"Shape role: {shape_role['surface_role'] or 'armor_overlay_part'}; contact intent: {shape_role.get('target_contact') or 'body-following overlay'}. "
        f"UV availability: uv0={uv_availability['uv0_status']}, mesh_uv_allowed={uv_availability['can_generate_mesh_uv_texture']}. "
        f"UV policy: primary motif zone={uv_policy.get('primary_motif_zone')}; low-frequency zone={uv_policy.get('low_frequency_zone')}; panel flow={uv_policy.get('panel_flow_direction')}. "
        f"Material zones: {', '.join(material_hints['material_zones'])}. Preserve whole-suit palette, motif continuity, and provider discipline."
    )
    return {
        "contract_version": PER_PART_TEXTURE_CONTRACT_VERSION,
        "part": part,
        "provider_profile": "nano_banana",
        "texture_prompt_contract": "nanobanana-texture-prompt.v1",
        "texture_mode": "mesh_uv",
        "selected_variant_key": selected_variant_key,
        "asset_ref": asset_ref,
        "shape_role": shape_role,
        "uv_availability": uv_availability,
        "uv_policy": uv_policy,
        "material_hints": material_hints,
        "texture_prompt": prompt,
    }


def _texture_asset_surface_case(
    asset_ref: str,
    sidecar: dict[str, Any],
    surface_check: dict[str, Any],
) -> dict[str, Any]:
    ref = str(asset_ref or "").strip()
    path = _asset_ref_path(ref).lower()
    reasons = surface_check.get("reasons") if isinstance(surface_check.get("reasons"), list) else []
    if not ref:
        return {
            "asset_format": "missing",
            "asset_surface_case": "uv_unavailable_no_asset_ref",
            "uv0_status": "missing",
            "uv0_source": "asset_ref_missing",
            "can_generate_mesh_uv_texture": False,
        }
    if path.endswith(".mesh.json") or path.endswith(".json"):
        return {
            "asset_format": "mesh_json",
            "asset_surface_case": "mesh_json_seed_proxy_no_authoritative_uv",
            "uv0_status": "not_applicable",
            "uv0_source": "mesh_json_seed_proxy",
            "can_generate_mesh_uv_texture": False,
        }
    if path.endswith(".glb"):
        if surface_check.get("ok") is False and reasons:
            return {
                "asset_format": "glb",
                "asset_surface_case": "glb_fallback_unavailable_for_final_texture",
                "uv0_status": "unavailable",
                "uv0_source": "runtime_surface_gate",
                "can_generate_mesh_uv_texture": False,
            }
        if sidecar:
            return {
                "asset_format": "glb",
                "asset_surface_case": "glb_with_modeler_sidecar_uv_contract",
                "uv0_status": "unknown",
                "uv0_source": "modeler_sidecar_available",
                "can_generate_mesh_uv_texture": True,
            }
        return {
            "asset_format": "glb",
            "asset_surface_case": "glb_without_local_sidecar_uv_unknown",
            "uv0_status": "unknown",
            "uv0_source": "glb_without_local_sidecar",
            "can_generate_mesh_uv_texture": True,
        }
    return {
        "asset_format": "other",
        "asset_surface_case": "uv_unavailable_unknown_asset_format",
        "uv0_status": "missing",
        "uv0_source": "unknown_asset_format",
        "can_generate_mesh_uv_texture": False,
    }


def _merge_missing_dict(source: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    merged = _clone(source)
    for key, value in fallback.items():
        if key not in merged or merged.get(key) in (None, "", []):
            merged[key] = _clone(value)
    return merged


def build_render_placements(
    suitspec: dict[str, Any],
    body_fit_contract: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Build the per-part placement contract shared by Web and Quest runtimes.

    The current Web preview already reads SuitSpec module fit and modeler
    sidecar data. Quest historically used its own fixed tables. This contract
    gives Quest and future adapters the same source of truth: body anchor,
    sidecar offset, source bbox, and target size. Runtime-specific rigs may
    still transform this into their local coordinate space, but they should not
    rediscover asset scale or attachment intent independently.
    """

    modules = suitspec.get("modules") if isinstance(suitspec.get("modules"), dict) else {}
    generation = suitspec.get("generation") if isinstance(suitspec.get("generation"), dict) else {}
    slot_by_part = _body_fit_slots_by_runtime_part(body_fit_contract)
    placements: dict[str, dict[str, Any]] = {}
    for part_name, module in modules.items():
        if not isinstance(module, dict) or module.get("enabled") is not True:
            continue
        slot = slot_by_part.get(part_name, {})
        asset_ref = str(module.get("asset_ref") or "")
        module_sidecar = _validated_modeler_sidecar(
            module.get("modeler_sidecar"),
            source=f"inline modeler_sidecar for {part_name}",
        )
        sidecar = module_sidecar or _modeler_sidecar_from_asset_ref(asset_ref) or {}
        vrm_anchor = module.get("vrm_anchor") if isinstance(module.get("vrm_anchor"), dict) else {}
        vrm_attachment = (
            sidecar.get("vrm_attachment")
            if isinstance(sidecar.get("vrm_attachment"), dict)
            else {}
        )
        offset = _vector3(vrm_anchor.get("offset"), fallback=_vector3(vrm_attachment.get("offset_m")))
        rotation = _vector3(vrm_anchor.get("rotation"), fallback=_vector3(vrm_attachment.get("rotation_deg")))
        source_bbox = _bbox_from_any(sidecar.get("bbox_m"))
        explicit_target_size = (
            _bbox_from_any(sidecar.get("target_envelope_m"))
            or _bbox_from_any(sidecar.get("target_bbox_m"))
            or _bbox_from_any(sidecar.get("max_bbox_m"))
        )
        reference_target_size = _reference_target_for_variant_part(part_name, sidecar)
        fit_target_size = _target_from_fit(module.get("fit"))
        target_size = explicit_target_size or reference_target_size or source_bbox or fit_target_size
        body_anchor = slot.get("body_anchor") or vrm_anchor.get("bone") or vrm_attachment.get("primary_bone")
        quest_offset = _quest_offset_from_vrm(offset)
        surface_anchor = _surface_anchor_for_part(
            part_name,
            slot=slot,
            body_anchor=body_anchor,
            offset=offset,
            quest_offset=quest_offset,
            sidecar=sidecar,
        )
        placements[part_name] = {
            "contract_version": "runtime-render-placement.v1",
            "part": part_name,
            "asset_ref": asset_ref,
            "selected_variant_key": _selected_variant_key_for_part(part_name, module, sidecar, generation),
            "attachment_slot": str(module.get("attachment_slot") or part_name),
            "body_fit_slot_id": slot.get("body_fit_slot_id"),
            "body_anchor": body_anchor,
            "coordinate_space": "vrm_humanoid_local_y_up_z_front",
            "quest_coordinate_space": "quest_rig_local_y_up_z_back",
            "offset_m": offset,
            "quest_rig_offset_m": quest_offset,
            "surface_anchor": surface_anchor,
            "body_surface_clearance_m": surface_anchor.get("clearance_m"),
            "body_surface_clearance_source": surface_anchor.get("clearance_source"),
            "shell_thickness_target_m": surface_anchor.get("shell_thickness_target_m"),
            "surface_offset_clamped_m": surface_anchor.get("offset_clamped_m"),
            "quest_surface_offset_clamped_m": surface_anchor.get("quest_rig_offset_clamped_m"),
            "rotation_deg": rotation,
            "source_bbox_m": source_bbox,
            "target_size_m": target_size,
            "target_size_array_m": _bbox_to_array(target_size),
            "target_size_source": _target_size_source(
                explicit_target_size=explicit_target_size,
                reference_target_size=reference_target_size,
                source_bbox=source_bbox,
                fit_target_size=fit_target_size,
            ),
            "scale_policy": "fit_source_bbox_to_target_size_m",
            "modeler_sidecar_variant_key": sidecar.get("variant_key"),
            "modeler_coordinate_frame": sidecar.get("coordinate_frame"),
            "placement_note": (
                "Web and Quest should use this record before falling back to legacy fixed tables."
            ),
        }
    return dict(sorted(placements.items()))


def _variant_render_placement_sources(
    suitspec: dict[str, Any],
    layers: dict[str, Any],
) -> list[Any]:
    generation = suitspec.get("generation") if isinstance(suitspec.get("generation"), dict) else {}
    layer_overlay = layers.get("armor_overlay") if isinstance(layers.get("armor_overlay"), dict) else {}
    generation_layers = (
        generation.get("visual_layers")
        if isinstance(generation.get("visual_layers"), dict)
        else {}
    )
    generation_overlay = (
        generation_layers.get("armor_overlay")
        if isinstance(generation_layers.get("armor_overlay"), dict)
        else {}
    )
    generation_pipeline = (
        generation.get("asset_pipeline")
        if isinstance(generation.get("asset_pipeline"), dict)
        else {}
    )
    return [
        layer_overlay.get("variant_render_placements"),
        generation.get("variant_render_placements"),
        generation_overlay.get("variant_render_placements"),
        generation_pipeline.get("variant_render_placements"),
    ]


def _normalize_variant_render_placements(
    sources: list[Any],
    *,
    overlay_parts: list[str],
) -> dict[str, dict[str, dict[str, Any]]]:
    overlay_part_set = set(overlay_parts)
    normalized: dict[str, dict[str, dict[str, Any]]] = {}
    for source in sources:
        if not isinstance(source, dict):
            continue
        for part_name, value in source.items():
            part = str(part_name or "").strip()
            if not part or part not in overlay_part_set:
                continue
            records = _normalize_variant_render_placement_table(part, value)
            if not records:
                continue
            part_records = normalized.setdefault(part, {})
            part_records.update(records)
    return {
        part: dict(sorted(records.items()))
        for part, records in sorted(normalized.items())
        if records
    }


def _normalize_variant_render_placement_table(
    part_name: str,
    value: Any,
) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    if _is_runtime_render_placement_record(value):
        item = _normalize_variant_render_placement_record(part_name, None, value)
        if item:
            records[item[0]] = item[1]
        return records
    values = value if isinstance(value, list) else []
    if isinstance(value, dict):
        values = list(value.items())
    for item in values:
        if isinstance(item, tuple):
            key, record = item
        else:
            key, record = None, item
        normalized = _normalize_variant_render_placement_record(part_name, key, record)
        if normalized:
            records[normalized[0]] = normalized[1]
    return records


def _normalize_variant_render_placement_record(
    part_name: str,
    key: Any,
    value: Any,
) -> tuple[str, dict[str, Any]] | None:
    if not _is_runtime_render_placement_record(value):
        return None
    record = _clone(value)
    record_part = str(record.get("part") or part_name or "").strip()
    if record_part != part_name:
        return None
    selected_key = _normalize_variant_key(
        part_name,
        record.get("selected_variant_key") or record.get("variant_key") or key,
    )
    if not selected_key:
        return None
    record["contract_version"] = str(record.get("contract_version") or "runtime-render-placement.v1")
    record["part"] = part_name
    record["selected_variant_key"] = selected_key
    return selected_key, record


def _is_runtime_render_placement_record(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and (
            str(value.get("contract_version") or "") == "runtime-render-placement.v1"
            or "target_size_array_m" in value
            or "target_size_m" in value
            or "offset_m" in value
            or "rotation_deg" in value
        )
    )


def _selected_variant_keys_from_render_placements(
    render_placements: dict[str, dict[str, Any]],
) -> dict[str, str]:
    selected: dict[str, str] = {}
    for part, placement in render_placements.items():
        if not isinstance(placement, dict):
            continue
        key = _normalize_variant_key(part, placement.get("selected_variant_key"))
        if key:
            selected[part] = key
    return dict(sorted(selected.items()))


def _selected_variant_render_placements(
    selected_variant_keys: dict[str, str],
    variant_render_placements: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, dict[str, Any]]:
    selected: dict[str, dict[str, Any]] = {}
    for part, key in selected_variant_keys.items():
        placement = variant_render_placements.get(part, {}).get(key)
        if isinstance(placement, dict):
            selected[part] = _clone(placement)
    return dict(sorted(selected.items()))


def _variant_placement_snapshot(
    *,
    selected_variant_keys: dict[str, str],
    render_placements: dict[str, dict[str, Any]],
    variant_render_placements: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, Any]:
    parts: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    mismatched: list[str] = []
    for part, render_placement in sorted(render_placements.items()):
        selected_key = selected_variant_keys.get(part, "")
        variant_placement = variant_render_placements.get(part, {}).get(selected_key)
        status = "matched"
        if not selected_key:
            status = "not_variant_selected"
        elif not isinstance(variant_placement, dict):
            status = "missing_variant_render_placement"
            missing.append(part)
        else:
            variant_key = _normalize_variant_key(part, variant_placement.get("selected_variant_key"))
            if variant_key != selected_key:
                status = "selected_variant_key_mismatch"
                mismatched.append(part)
            elif not _asset_refs_match(render_placement, variant_placement):
                status = "asset_ref_mismatch"
                mismatched.append(part)
        parts[part] = {
            "part": part,
            "selected_variant_key": selected_key,
            "render_placement_path": f"render_placements.{part}",
            "variant_render_placement_path": (
                f"visual_layers.armor_overlay.variant_render_placements.{part}.{selected_key}"
                if selected_key
                else None
            ),
            "render_asset_ref": str(render_placement.get("asset_ref") or "") if isinstance(render_placement, dict) else "",
            "variant_asset_ref": (
                str(variant_placement.get("asset_ref") or "") if isinstance(variant_placement, dict) else ""
            ),
            "matches_current_render_placement": status == "matched",
            "status": status,
        }
    return {
        "contract_version": "runtime-variant-placement-snapshot.v1",
        "selection_source": "render_placements.selected_variant_key",
        "variant_render_placement_contract": "runtime-render-placement.v1",
        "selected_variant_keys": _clone(selected_variant_keys),
        "parts": parts,
        "selected_variant_render_placement_parts": sorted(
            part
            for part, record in parts.items()
            if record["matches_current_render_placement"]
        ),
        "missing_selected_variant_render_placements": sorted(missing),
        "mismatched_selected_variant_render_placements": sorted(mismatched),
        "replay_diff_basis": (
            "Replay should compare Web preview selected placement, Quest recall render_placements, "
            "and this selected variant table path before accepting a recorded alignment."
        ),
    }


def _asset_refs_match(render_placement: Any, variant_placement: Any) -> bool:
    if not isinstance(render_placement, dict) or not isinstance(variant_placement, dict):
        return False
    render_raw = str(render_placement.get("asset_ref") or "")
    variant_raw = str(variant_placement.get("asset_ref") or "")
    if not render_raw or not variant_raw:
        return True
    render_asset = _portable_asset_ref(render_raw)
    variant_asset = _portable_asset_ref(variant_raw)
    return render_asset == variant_asset


def _selected_variant_key_for_part(
    part_name: str,
    module: dict[str, Any],
    sidecar: dict[str, Any],
    generation: dict[str, Any],
) -> str:
    selected_keys = generation.get("selected_variant_keys") if isinstance(generation.get("selected_variant_keys"), dict) else {}
    resolutions = (
        generation.get("variant_asset_resolution")
        if isinstance(generation.get("variant_asset_resolution"), dict)
        else {}
    )
    resolution = resolutions.get(part_name) if isinstance(resolutions.get(part_name), dict) else {}
    candidates = (
        selected_keys.get(part_name) if isinstance(selected_keys, dict) else None,
        resolution.get("selected_variant_key"),
        module.get("selected_variant_key"),
        module.get("variant_key"),
        sidecar.get("variant_key"),
        _variant_key_from_asset_ref(part_name, str(module.get("asset_ref") or "")),
    )
    for candidate in candidates:
        key = _normalize_variant_key(part_name, candidate)
        if key:
            return key
    return ""


def _normalize_variant_key(part_name: str, value: Any) -> str:
    module = str(part_name or "").strip()
    raw = str(value or "").strip()
    if not module or not raw:
        return ""
    if ":" in raw:
        key_module, slug = raw.split(":", 1)
        if key_module.strip() != module:
            return ""
    else:
        slug = raw
    slug = slug.strip()
    if not slug or any(char in slug for char in ("/", "\\", ":")):
        return ""
    if not all(char.isalnum() or char in {"_", "-"} for char in slug):
        return ""
    return f"{module}:{slug}"


def _variant_key_from_asset_ref(part_name: str, asset_ref: str) -> str:
    normalized = asset_ref.replace("\\", "/")
    marker = f"/{part_name}/variants/"
    if marker not in normalized:
        return ""
    slug = normalized.split(marker, 1)[1].split("/", 1)[0]
    return _normalize_variant_key(part_name, slug)


def _surface_anchor_for_part(
    part_name: str,
    *,
    slot: dict[str, Any],
    body_anchor: Any,
    offset: list[float],
    quest_offset: list[float],
    sidecar: dict[str, Any],
) -> dict[str, Any]:
    policy = body_surface_fit_policy_for_part(part_name) or {}
    clearance = _surface_number(sidecar.get("clearance_m"))
    shell_thickness = _surface_number(sidecar.get("shell_thickness_target_m"))
    target_contact, target_contact_source = _surface_target_contact(sidecar, policy)
    return {
        "contract_version": "runtime-body-surface-anchor.v1",
        "part": part_name,
        "body_fit_slot_id": slot.get("body_fit_slot_id"),
        "body_anchor": body_anchor,
        "coordinate_space": "vrm_humanoid_local_y_up_z_front",
        "quest_coordinate_space": "quest_rig_local_y_up_z_back",
        "surface_policy": policy.get("contract_version"),
        "surface_role": policy.get("role"),
        "target_contact": target_contact,
        "target_contact_source": target_contact_source,
        "offset_m": list(offset),
        "offset_clamped_m": clamp_surface_offset_for_part(part_name, offset, space="vrm"),
        "quest_rig_offset_m": list(quest_offset),
        "quest_rig_offset_clamped_m": clamp_surface_offset_for_part(part_name, quest_offset, space="quest"),
        "vrm_offset_clamp_m": policy.get("vrm_offset_clamp_m") or {},
        "quest_offset_clamp_m": policy.get("quest_offset_clamp_m") or {},
        "clearance_m": clearance,
        "clearance_source": "modeler_sidecar.clearance_m" if clearance is not None else "missing",
        "shell_thickness_target_m": shell_thickness,
        "shell_thickness_source": (
            "modeler_sidecar.shell_thickness_target_m" if shell_thickness is not None else "missing"
        ),
        "placement_basis": "body_fit_slot+modeler_sidecar+body_surface_fit_policy",
    }


def _surface_target_contact(
    sidecar: dict[str, Any],
    policy: dict[str, Any],
) -> tuple[str | None, str]:
    body_follow = (
        sidecar.get("body_follow_profile")
        if isinstance(sidecar.get("body_follow_profile"), dict)
        else {}
    )
    sidecar_contact = str(body_follow.get("target_contact") or "").strip()
    if sidecar_contact:
        return sidecar_contact, "modeler_sidecar.body_follow_profile.target_contact"
    policy_contact = str(policy.get("target_contact") or "").strip()
    if policy_contact:
        return policy_contact, "body_surface_fit_policy.target_contact"
    return None, "missing"


def _surface_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number < 0:
        return None
    return round(number, 6)


def merge_suitspec_surface_into_manifest(
    manifest: dict[str, Any],
    suitspec: dict[str, Any],
) -> dict[str, Any]:
    """Project current SuitSpec module surface fields into a manifest copy."""

    normalized = _clone(manifest)
    parts = normalized.setdefault("parts", {})
    if not isinstance(parts, dict):
        parts = {}
        normalized["parts"] = parts
    modules = suitspec.get("modules") if isinstance(suitspec.get("modules"), dict) else {}
    for part_name, module in modules.items():
        if not isinstance(module, dict):
            continue
        part = parts.setdefault(part_name, {})
        if not isinstance(part, dict):
            part = {}
            parts[part_name] = part
        part["enabled"] = bool(module.get("enabled", False))
        for key in ("asset_ref", "material_ref", "texture_path", "attachment_slot", "fit", "vrm_anchor"):
            if key in module:
                part[key] = _clone(module[key])
    return normalized


def _normalize_render_contract(
    render_contract: dict[str, Any] | None,
    overlay_parts: list[str],
) -> dict[str, Any]:
    source = _clone(render_contract or {})
    required_parts = list(source.get("required_overlay_parts") or DEFAULT_REQUIRED_OVERLAY_PARTS)
    selected_parts = list(source.get("selected_overlay_parts") or overlay_parts)
    minimum_visible = int(source.get("minimum_visible_overlay_parts") or len(required_parts))
    return {
        **source,
        "contract_version": str(source.get("contract_version") or DEFAULT_VISUAL_LAYER_CONTRACT),
        "required_layers": list(source.get("required_layers") or DEFAULT_REQUIRED_LAYERS),
        "vrm_only_is_valid": False,
        "base_suit_surface_required": True,
        "armor_overlay_required": True,
        "required_overlay_parts": required_parts,
        "selected_overlay_parts": selected_parts,
        "overlay_part_count": len(selected_parts),
        "minimum_visible_overlay_parts": minimum_visible,
        "missing_required_overlay_parts": [
            part for part in required_parts if part not in selected_parts
        ],
    }


def _normalize_visual_layers(
    visual_layers: dict[str, Any] | None,
    suitspec: dict[str, Any],
    overlay_parts: list[str],
) -> dict[str, Any]:
    source = _clone(visual_layers or {})
    body_profile = suitspec.get("body_profile") if isinstance(suitspec.get("body_profile"), dict) else {}
    base_suit = source.get("base_suit") if isinstance(source.get("base_suit"), dict) else {}
    armor_overlay = source.get("armor_overlay") if isinstance(source.get("armor_overlay"), dict) else {}
    return {
        **source,
        "contract_version": str(source.get("contract_version") or DEFAULT_VISUAL_LAYER_CONTRACT),
        "base_suit": {
            **base_suit,
            "layer_id": str(base_suit.get("layer_id") or DEFAULT_REQUIRED_LAYERS[0]),
            "kind": str(base_suit.get("kind") or "vrm_body_surface"),
            "visibility": str(base_suit.get("visibility") or "required"),
            "asset_ref": str(
                base_suit.get("asset_ref")
                or body_profile.get("vrm_baseline_ref")
                or "viewer/assets/vrm/default.vrm"
            ),
        },
        "armor_overlay": {
            **armor_overlay,
            "layer_id": str(armor_overlay.get("layer_id") or DEFAULT_REQUIRED_LAYERS[1]),
            "kind": str(armor_overlay.get("kind") or "multi_part_mesh_overlay"),
            "visibility": str(armor_overlay.get("visibility") or "required"),
            "selected_parts": list(armor_overlay.get("selected_parts") or overlay_parts),
            "part_count": len(list(armor_overlay.get("selected_parts") or overlay_parts)),
        },
    }


def _enabled_overlay_parts(suitspec: dict[str, Any]) -> list[str]:
    modules = suitspec.get("modules") if isinstance(suitspec.get("modules"), dict) else {}
    return sorted(
        part_name
        for part_name, module in modules.items()
        if isinstance(module, dict) and module.get("enabled") is True
    )


def _part_has_runtime_surface(part: dict[str, Any]) -> bool:
    return _runtime_surface_check(part)["ok"]


def _runtime_surface_check(part: dict[str, Any]) -> dict[str, Any]:
    asset_ref = str(part.get("asset_ref") or "").strip() if isinstance(part, dict) else ""
    reasons: list[str] = []
    local_path: Path | None = None

    if not isinstance(part, dict) or part.get("enabled") is not True:
        reasons.append("part is not enabled")
    elif not asset_ref:
        reasons.append("asset_ref is missing")
    elif _is_remote_asset_ref(asset_ref):
        pass
    elif _asset_ref_path(asset_ref).lower().endswith(".glb"):
        local_path = _resolve_local_asset_path(asset_ref)
        reasons.extend(_local_glb_failure_reasons(local_path))
        if not reasons:
            reasons.extend(_present_sidecar_failure_reasons(local_path.with_suffix(".modeler.json")))
        reasons = _sanitize_local_asset_reasons(reasons, asset_ref, local_path)

    result: dict[str, Any] = {
        "ok": not reasons,
        "asset_ref": asset_ref,
        "reasons": reasons,
    }
    return result


def _sanitize_local_asset_reasons(
    reasons: list[str],
    asset_ref: str,
    local_path: Path,
) -> list[str]:
    public_ref = _portable_asset_ref(asset_ref)
    sidecar_public_ref = str(Path(public_ref).with_suffix(".modeler.json")).replace("\\", "/")
    replacements = {
        local_path.as_posix(): public_ref,
        local_path.with_suffix(".modeler.json").as_posix(): sidecar_public_ref,
    }
    sanitized: list[str] = []
    for reason in reasons:
        text = str(reason)
        for local, public in replacements.items():
            text = text.replace(local, public)
        sanitized.append(text)
    return sanitized


def _portable_asset_ref(asset_ref: str) -> str:
    ref = _asset_ref_path(asset_ref) or str(asset_ref or "asset_ref")
    normalized = ref.replace("\\", "/")
    if normalized.startswith("/") or (len(normalized) >= 3 and normalized[1] == ":" and normalized[2] == "/"):
        return Path(normalized).name or "asset_ref"
    return normalized


def _is_remote_asset_ref(asset_ref: str) -> bool:
    ref = str(asset_ref or "").strip()
    if ref.startswith("//"):
        return True
    parsed = urlparse(ref)
    scheme = parsed.scheme.lower()
    if not scheme or scheme == "file":
        return False
    if len(scheme) == 1 and len(ref) > 1 and ref[1] == ":":
        return False
    return True


def _asset_ref_path(asset_ref: str) -> str:
    parsed = urlparse(asset_ref)
    return unquote(parsed.path if parsed.scheme else asset_ref).replace("\\", "/")


def _resolve_local_asset_path(asset_ref: str) -> Path:
    parsed = urlparse(asset_ref)
    if parsed.scheme.lower() == "file":
        raw_path = unquote(parsed.path)
        if raw_path.startswith("/") and len(raw_path) >= 3 and raw_path[2] == ":":
            raw_path = raw_path[1:]
        path = Path(raw_path)
    else:
        path = Path(asset_ref)
    if path.is_absolute():
        return path

    cwd_candidate = (Path.cwd() / path).resolve()
    if cwd_candidate.is_file():
        return cwd_candidate
    return (_repo_root() / path).resolve()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _local_glb_failure_reasons(glb_path: Path) -> list[str]:
    if not glb_path.is_file():
        return [f"local GLB asset missing: {glb_path.as_posix()}"]

    try:
        data = glb_path.read_bytes()
    except OSError as exc:
        return [f"local GLB asset unreadable: {glb_path.as_posix()}: {exc}"]

    reasons: list[str] = []
    if len(data) < 20:
        return [f"GLB too small for header and first chunk: {glb_path.as_posix()}"]

    magic, version, declared_length = struct.unpack_from("<4sII", data, 0)
    if magic != GLB_MAGIC:
        reasons.append(f"GLB magic must be glTF: {glb_path.as_posix()}")
    if version != GLB_VERSION:
        reasons.append(f"GLB version must be 2: {glb_path.as_posix()}")
    if declared_length != len(data):
        reasons.append(f"GLB declared length must match file size: {glb_path.as_posix()}")

    chunk_length, chunk_type = struct.unpack_from("<II", data, 12)
    if chunk_type != GLB_JSON_CHUNK_TYPE:
        reasons.append(f"GLB first chunk must be JSON: {glb_path.as_posix()}")
    if chunk_length <= 0 or 20 + chunk_length > len(data):
        reasons.append(f"GLB first chunk length is invalid: {glb_path.as_posix()}")
    else:
        try:
            gltf_json = json.loads(data[20 : 20 + chunk_length].decode("utf-8").strip(" \t\r\n\0"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            reasons.append(f"GLB JSON chunk unreadable: {glb_path.as_posix()}: {exc}")
        else:
            asset_version = gltf_json.get("asset", {}).get("version") if isinstance(gltf_json, dict) else None
            if asset_version != "2.0":
                reasons.append(f"GLB asset.version must be 2.0: {glb_path.as_posix()}")
    return reasons


def _modeler_sidecar_failure_reasons(payload: Any, source: str) -> list[str]:
    if not isinstance(payload, dict):
        return [f"modeler sidecar must be a JSON object: {source}"]

    contract_version = str(payload.get("contract_version") or "").strip()
    if contract_version and contract_version not in MODELER_SIDECAR_CONTRACT_VERSIONS:
        return [f"modeler sidecar contract_version is not recognized: {source}"]

    coordinate_frame = str(payload.get("coordinate_frame") or "").strip()
    if coordinate_frame and coordinate_frame not in MODELER_SIDECAR_COORDINATE_FRAMES:
        return [f"modeler sidecar coordinate_frame is not recognized: {source}"]
    return []


def _validated_modeler_sidecar(payload: Any, source: str) -> dict[str, Any] | None:
    if not isinstance(payload, dict) or _modeler_sidecar_failure_reasons(payload, source):
        return None
    return payload


def _present_sidecar_failure_reasons(sidecar_path: Path) -> list[str]:
    if not sidecar_path.is_file():
        return []
    try:
        payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"modeler sidecar unreadable: {sidecar_path.as_posix()}: {exc}"]
    return _modeler_sidecar_failure_reasons(payload, sidecar_path.as_posix())


def _modeler_sidecar_from_asset_ref(asset_ref: str) -> dict[str, Any] | None:
    ref = str(asset_ref or "").strip()
    if not ref or _is_remote_asset_ref(ref) or not _asset_ref_path(ref).lower().endswith(".glb"):
        return None
    sidecar_path = _resolve_local_asset_path(ref).with_suffix(".modeler.json")
    if not sidecar_path.is_file() or _present_sidecar_failure_reasons(sidecar_path):
        return None
    try:
        payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return _validated_modeler_sidecar(payload, source=sidecar_path.as_posix())


def _body_fit_slots_by_runtime_part(body_fit_contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    slots = body_fit_contract.get("slots") if isinstance(body_fit_contract.get("slots"), dict) else {}
    mapped: dict[str, dict[str, Any]] = {}
    for slot_id, slot in slots.items():
        if not isinstance(slot, dict):
            continue
        runtime_part_id = str(slot.get("runtime_part_id") or slot_id)
        mapped[runtime_part_id] = {
            "body_fit_slot_id": str(slot_id),
            "runtime_part_id": runtime_part_id,
            "body_anchor": slot.get("body_anchor"),
            "mirror_pair": slot.get("mirror_pair"),
            "coverage": list(slot.get("coverage") or []),
            "recommended_scale": slot.get("recommended_scale"),
        }
    return mapped


def _vector3(value: Any, *, fallback: list[float] | None = None) -> list[float]:
    if isinstance(value, (list, tuple)) and len(value) >= 3:
        values = []
        for index in range(3):
            try:
                values.append(round(float(value[index]), 6))
            except (TypeError, ValueError):
                break
        if len(values) == 3:
            return values
    if fallback is not None:
        return list(fallback)
    return [0.0, 0.0, 0.0]


def _quest_offset_from_vrm(offset: list[float]) -> list[float]:
    values = _vector3(offset)
    # Modeler/Web data uses +Z as body-front. The current Quest rig has its
    # fixed body table facing the opposite local Z convention, so mirror Z once
    # at the runtime package boundary instead of per-viewer rediscovery.
    return [values[0], values[1], round(-values[2], 6)]


def _bbox_from_any(value: Any) -> dict[str, float] | None:
    if not isinstance(value, dict):
        return None
    source = value.get("size") if isinstance(value.get("size"), dict) else value
    result: dict[str, float] = {}
    for axis in ("x", "y", "z"):
        try:
            number = float(source.get(axis))
        except (AttributeError, TypeError, ValueError):
            return None
        if number <= 0:
            return None
        result[axis] = round(number, 6)
    return result


def _target_from_fit(fit: Any) -> dict[str, float] | None:
    if not isinstance(fit, dict):
        return None
    for key in ("targetSize", "target_size", "scale", "minScale"):
        values = fit.get(key)
        if not isinstance(values, (list, tuple)) or len(values) < 3:
            continue
        try:
            x, y, z = (float(values[0]), float(values[1]), float(values[2]))
        except (TypeError, ValueError):
            continue
        if x > 0 and y > 0 and z > 0:
            return {"x": round(x, 6), "y": round(y, 6), "z": round(z, 6)}
    return None


def _reference_target_for_variant_part(part_name: str, sidecar: dict[str, Any]) -> dict[str, float] | None:
    if not isinstance(sidecar, dict):
        return None
    if str(sidecar.get("asset_kind") or "").strip() != "variant":
        return None
    if sidecar.get("preserves_canonical_part") is not True:
        return None
    target = _reference_target_dimensions(part_name)
    return _bbox_from_any(target)


def _target_size_source(
    *,
    explicit_target_size: dict[str, float] | None,
    reference_target_size: dict[str, float] | None,
    source_bbox: dict[str, float] | None,
    fit_target_size: dict[str, float] | None,
) -> str:
    if explicit_target_size is not None:
        return "modeler_sidecar_target"
    if reference_target_size is not None:
        return "blueprint_canonical_envelope"
    if source_bbox is not None:
        return "modeler_source_bbox"
    if fit_target_size is not None:
        return "module_fit"
    return "missing"


def _bbox_to_array(value: dict[str, float] | None) -> list[float] | None:
    if not isinstance(value, dict):
        return None
    try:
        return [round(float(value[axis]), 6) for axis in ("x", "y", "z")]
    except (KeyError, TypeError, ValueError):
        return None


def _clone(value: Any) -> Any:
    return copy.deepcopy(value)


__all__ = [
    "DEFAULT_REQUIRED_LAYERS",
    "DEFAULT_REQUIRED_OVERLAY_PARTS",
    "DEFAULT_VISUAL_LAYER_CONTRACT",
    "build_render_placements",
    "build_runtime_suit_package",
    "merge_suitspec_surface_into_manifest",
]
