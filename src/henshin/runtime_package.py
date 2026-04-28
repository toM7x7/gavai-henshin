"""Runtime package normalization for Quest/Web suit viewers."""

from __future__ import annotations

import copy
from typing import Any


DEFAULT_VISUAL_LAYER_CONTRACT = "base-suit-overlay.v1"
DEFAULT_REQUIRED_LAYERS = ["base_suit_surface", "armor_overlay_parts"]
DEFAULT_REQUIRED_OVERLAY_PARTS = ["back", "chest", "helmet"]


def build_runtime_suit_package(
    *,
    suitspec: dict[str, Any],
    manifest: dict[str, Any] | None = None,
    visual_layers: dict[str, Any] | None = None,
    render_contract: dict[str, Any] | None = None,
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
    contract = _normalize_render_contract(render_contract, overlay_parts)
    layers = _normalize_visual_layers(visual_layers, normalized_suitspec, overlay_parts)
    visible_overlay_parts = [
        part
        for part in overlay_parts
        if _part_has_runtime_surface(normalized_manifest.get("parts", {}).get(part, {}))
    ]
    missing_required = [
        part for part in contract["required_overlay_parts"] if part not in visible_overlay_parts
    ]
    return {
        "contract_version": contract["contract_version"],
        "suitspec": normalized_suitspec,
        "manifest": normalized_manifest,
        "visual_layers": layers,
        "render_contract": contract,
        "runtime_checks": {
            "vrm_only_is_valid": False,
            "required_layers": contract["required_layers"],
            "enabled_overlay_parts": overlay_parts,
            "visible_overlay_parts": visible_overlay_parts,
            "visible_overlay_count": len(visible_overlay_parts),
            "minimum_visible_overlay_parts": contract["minimum_visible_overlay_parts"],
            "missing_required_overlay_parts": missing_required,
            "can_render_runtime_suit": not missing_required
            and len(visible_overlay_parts) >= contract["minimum_visible_overlay_parts"],
        },
    }


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
    return bool(part.get("enabled") is True and str(part.get("asset_ref") or "").strip())


def _clone(value: Any) -> Any:
    return copy.deepcopy(value)
