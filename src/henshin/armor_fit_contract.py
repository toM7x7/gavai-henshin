"""Body-fit contract for a VRM base suit plus segmented armor parts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


ARMOR_FIT_CONTRACT_VERSION = "armor-body-fit.v1"
RUNTIME_VISUAL_LAYER_CONTRACT_VERSION = "base-suit-overlay.v1"
BASE_SUIT_LAYER_ID = "base_suit_surface"
ARMOR_OVERLAY_LAYER_ID = "armor_overlay_parts"
DEFAULT_VRM_BASELINE_REF = "viewer/assets/vrm/default.vrm"

BASELINE_HEIGHT_CM = 170.0
MIN_SUPPORTED_HEIGHT_CM = 90.0
MAX_SUPPORTED_HEIGHT_CM = 230.0


@dataclass(frozen=True, slots=True)
class ArmorSlotSpec:
    slot_id: str
    body_anchor: str
    mirror_pair: str | None
    coverage: tuple[str, ...]
    min_scale: float
    max_scale: float
    display_label: str
    runtime_part_id: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot_id": self.slot_id,
            "body_anchor": self.body_anchor,
            "mirror_pair": self.mirror_pair,
            "coverage": list(self.coverage),
            "min_scale": self.min_scale,
            "max_scale": self.max_scale,
            "display_label": self.display_label,
            "runtime_part_id": self.runtime_part_id,
        }


def _slot(
    slot_id: str,
    body_anchor: str,
    mirror_pair: str | None,
    coverage: tuple[str, ...],
    min_scale: float,
    max_scale: float,
    display_label: str,
    runtime_part_id: str | None = None,
) -> ArmorSlotSpec:
    return ArmorSlotSpec(
        slot_id=slot_id,
        body_anchor=body_anchor,
        mirror_pair=mirror_pair,
        coverage=coverage,
        min_scale=min_scale,
        max_scale=max_scale,
        display_label=display_label,
        runtime_part_id=runtime_part_id or slot_id,
    )


_SLOT_SPECS = (
    _slot("helmet", "head", None, ("head", "face_clearance", "neck_ring"), 0.86, 1.18, "Helmet"),
    _slot("chest", "upperChest", None, ("sternum", "ribs", "upper_back_clearance"), 0.80, 1.24, "Chest"),
    _slot("back", "upperChest", None, ("scapula", "spine_upper", "rear_power_bus"), 0.80, 1.24, "Back"),
    _slot(
        "shoulder_l",
        "leftShoulder",
        "shoulder_r",
        ("left_deltoid", "left_upperarm_socket"),
        0.78,
        1.28,
        "Left shoulder",
        "left_shoulder",
    ),
    _slot(
        "shoulder_r",
        "rightShoulder",
        "shoulder_l",
        ("right_deltoid", "right_upperarm_socket"),
        0.78,
        1.28,
        "Right shoulder",
        "right_shoulder",
    ),
    _slot(
        "forearm_l",
        "leftLowerArm",
        "forearm_r",
        ("left_radius_ulna", "left_wrist_transition"),
        0.72,
        1.32,
        "Left forearm",
        "left_forearm",
    ),
    _slot(
        "forearm_r",
        "rightLowerArm",
        "forearm_l",
        ("right_radius_ulna", "right_wrist_transition"),
        0.72,
        1.32,
        "Right forearm",
        "right_forearm",
    ),
    _slot(
        "hand_l",
        "leftHand",
        "hand_r",
        ("left_back_of_hand", "left_knuckle_lanes", "left_wrist_dock"),
        0.74,
        1.26,
        "Left hand",
        "left_hand",
    ),
    _slot(
        "hand_r",
        "rightHand",
        "hand_l",
        ("right_back_of_hand", "right_knuckle_lanes", "right_wrist_dock"),
        0.74,
        1.26,
        "Right hand",
        "right_hand",
    ),
    _slot(
        "thigh_l",
        "leftUpperLeg",
        "thigh_r",
        ("left_quadriceps", "left_hamstring_clearance", "left_hip_socket"),
        0.74,
        1.34,
        "Left thigh",
        "left_thigh",
    ),
    _slot(
        "thigh_r",
        "rightUpperLeg",
        "thigh_l",
        ("right_quadriceps", "right_hamstring_clearance", "right_hip_socket"),
        0.74,
        1.34,
        "Right thigh",
        "right_thigh",
    ),
    _slot(
        "shin_l",
        "leftLowerLeg",
        "shin_r",
        ("left_tibia", "left_calf_clearance", "left_ankle_transition"),
        0.72,
        1.34,
        "Left shin",
        "left_shin",
    ),
    _slot(
        "shin_r",
        "rightLowerLeg",
        "shin_l",
        ("right_tibia", "right_calf_clearance", "right_ankle_transition"),
        0.72,
        1.34,
        "Right shin",
        "right_shin",
    ),
    _slot(
        "boot_l",
        "leftFoot",
        "boot_r",
        ("left_foot", "left_ankle_cuff", "left_sole"),
        0.72,
        1.30,
        "Left boot",
        "left_boot",
    ),
    _slot(
        "boot_r",
        "rightFoot",
        "boot_l",
        ("right_foot", "right_ankle_cuff", "right_sole"),
        0.72,
        1.30,
        "Right boot",
        "right_boot",
    ),
    _slot("belt", "hips", None, ("waist", "hips", "lower_spine"), 0.78, 1.24, "Belt", "waist"),
)

ARMOR_SLOT_SPECS: dict[str, ArmorSlotSpec] = {spec.slot_id: spec for spec in _SLOT_SPECS}
MAJOR_ARMOR_SLOTS: tuple[str, ...] = tuple(ARMOR_SLOT_SPECS)
REQUIRED_RUNTIME_SLOTS: tuple[str, ...] = ("helmet", "chest", "back")
MIRROR_SLOT_PAIRS: tuple[tuple[str, str], ...] = (
    ("shoulder_l", "shoulder_r"),
    ("forearm_l", "forearm_r"),
    ("hand_l", "hand_r"),
    ("thigh_l", "thigh_r"),
    ("shin_l", "shin_r"),
    ("boot_l", "boot_r"),
)

SLOT_ALIASES: dict[str, str] = {
    "left_shoulder": "shoulder_l",
    "right_shoulder": "shoulder_r",
    "l_shoulder": "shoulder_l",
    "r_shoulder": "shoulder_r",
    "shoulder_left": "shoulder_l",
    "shoulder_right": "shoulder_r",
    "left_forearm": "forearm_l",
    "right_forearm": "forearm_r",
    "l_forearm": "forearm_l",
    "r_forearm": "forearm_r",
    "forearm_left": "forearm_l",
    "forearm_right": "forearm_r",
    "left_hand": "hand_l",
    "right_hand": "hand_r",
    "l_hand": "hand_l",
    "r_hand": "hand_r",
    "hand_left": "hand_l",
    "hand_right": "hand_r",
    "left_thigh": "thigh_l",
    "right_thigh": "thigh_r",
    "l_thigh": "thigh_l",
    "r_thigh": "thigh_r",
    "thigh_left": "thigh_l",
    "thigh_right": "thigh_r",
    "left_shin": "shin_l",
    "right_shin": "shin_r",
    "l_shin": "shin_l",
    "r_shin": "shin_r",
    "shin_left": "shin_l",
    "shin_right": "shin_r",
    "left_boot": "boot_l",
    "right_boot": "boot_r",
    "l_boot": "boot_l",
    "r_boot": "boot_r",
    "boot_left": "boot_l",
    "boot_right": "boot_r",
    "waist": "belt",
}


def slot_specs_as_dict() -> dict[str, dict[str, Any]]:
    return {slot_id: spec.to_dict() for slot_id, spec in ARMOR_SLOT_SPECS.items()}


def normalize_slot_id(slot_id: str) -> str:
    token = _slot_token(slot_id)
    canonical = SLOT_ALIASES.get(token, token)
    if canonical not in ARMOR_SLOT_SPECS:
        raise ValueError(f"unknown armor slot: {slot_id}")
    return canonical


def recommend_scale_for_height_cm(height_cm: float, slot_id: str) -> float:
    height = _coerce_height_cm(height_cm)
    spec = ARMOR_SLOT_SPECS[normalize_slot_id(slot_id)]
    raw_scale = height / BASELINE_HEIGHT_CM
    return round(_clamp(raw_scale, spec.min_scale, spec.max_scale), 4)


def recommend_slot_scales(
    height_cm: float,
    slots: Iterable[str] | None = None,
) -> dict[str, float]:
    selected_slots = _normalize_slot_collection(slots or MAJOR_ARMOR_SLOTS, fail_on_unknown=True)[0]
    return {slot: recommend_scale_for_height_cm(height_cm, slot) for slot in selected_slots}


def audit_armor_fit_slots(
    slots: Iterable[str],
    *,
    required_slots: Iterable[str] = REQUIRED_RUNTIME_SLOTS,
) -> dict[str, Any]:
    selected_slots, unknown_slots = _normalize_slot_collection(slots, fail_on_unknown=False)
    normalized_required, unknown_required = _normalize_slot_collection(required_slots, fail_on_unknown=False)
    selected_set = set(selected_slots)

    missing_required = [slot for slot in normalized_required if slot not in selected_set]
    missing_mirror_pairs = []
    for slot in selected_slots:
        mirror_pair = ARMOR_SLOT_SPECS[slot].mirror_pair
        if mirror_pair and mirror_pair not in selected_set:
            missing_mirror_pairs.append(
                {
                    "slot": slot,
                    "missing": mirror_pair,
                    "pair": [slot, mirror_pair],
                }
            )

    ok = not (missing_required or missing_mirror_pairs or unknown_slots or unknown_required)
    return {
        "ok": ok,
        "selected_slots": selected_slots,
        "required_slots": normalized_required,
        "missing_required_slots": missing_required,
        "missing_mirror_pairs": missing_mirror_pairs,
        "missing_left_right_pairs": missing_mirror_pairs,
        "unknown_slots": unknown_slots,
        "unknown_required_slots": unknown_required,
    }


def to_runtime_visual_layers(
    height_cm: float,
    selected_slots: Iterable[str] | None = None,
    *,
    required_slots: Iterable[str] = REQUIRED_RUNTIME_SLOTS,
    vrm_baseline_ref: str = DEFAULT_VRM_BASELINE_REF,
    part_id_style: str = "runtime",
    strict: bool = False,
) -> dict[str, Any]:
    slots = _normalize_slot_collection(selected_slots or MAJOR_ARMOR_SLOTS, fail_on_unknown=True)[0]
    required = _normalize_slot_collection(required_slots, fail_on_unknown=True)[0]
    audit = audit_armor_fit_slots(slots, required_slots=required)
    if strict and not audit["ok"]:
        raise ValueError(_audit_error_message(audit))

    selected_parts = [_part_id_for_style(slot, part_id_style) for slot in slots]
    required_parts = [_part_id_for_style(slot, part_id_style) for slot in required]
    scales = recommend_slot_scales(height_cm, slots)
    contract_slots = {
        slot: {
            **ARMOR_SLOT_SPECS[slot].to_dict(),
            "recommended_scale": scales[slot],
        }
        for slot in slots
    }

    height = _coerce_height_cm(height_cm)
    return {
        "contract_version": RUNTIME_VISUAL_LAYER_CONTRACT_VERSION,
        "body_fit_contract": {
            "contract_version": ARMOR_FIT_CONTRACT_VERSION,
            "baseline_height_cm": BASELINE_HEIGHT_CM,
            "height_cm": height,
            "slot_ids": slots,
            "required_slots": required,
            "recommended_scales": scales,
            "slots": contract_slots,
            "audit": audit,
        },
        "base_suit": {
            "layer_id": BASE_SUIT_LAYER_ID,
            "kind": "vrm_body_surface",
            "role": "body_conforming_substrate",
            "render_order": 0,
            "visibility": "required",
            "asset_ref": str(vrm_baseline_ref or DEFAULT_VRM_BASELINE_REF),
            "surface_target": "VRM humanoid mesh or future body surface shell",
            "generation_target": "continuous low-frequency suit material on the human body",
            "not_a_part_catalog_entry": True,
        },
        "armor_overlay": {
            "layer_id": ARMOR_OVERLAY_LAYER_ID,
            "kind": "multi_part_mesh_overlay",
            "role": "visible armor collection",
            "render_order": 10,
            "visibility": "required",
            "asset_role": "mesh.v1 seed/proxy until validated GLB/gltf rebuild",
            "required_parts": required_parts,
            "selected_parts": selected_parts,
            "part_count": len(selected_parts),
            "minimum_visible_parts": len(required_parts),
            "slot_ids": slots,
            "required_slot_ids": required,
            "part_id_style": part_id_style,
            "slot_to_runtime_part": {
                slot: ARMOR_SLOT_SPECS[slot].runtime_part_id
                for slot in slots
            },
            "empty_overlay_policy": "invalid",
        },
    }


def build_body_fit_contract(
    suitspec: dict[str, Any],
    *,
    selected_slots: Iterable[str] | None = None,
    required_slots: Iterable[str] = REQUIRED_RUNTIME_SLOTS,
) -> dict[str, Any]:
    body_profile = suitspec.get("body_profile") if isinstance(suitspec.get("body_profile"), dict) else {}
    height_cm = body_profile.get("height_cm", BASELINE_HEIGHT_CM)
    height = _coerce_height_cm(height_cm)
    selected = _slot_list(selected_slots) if selected_slots is not None else _enabled_module_slots(suitspec)
    audit = audit_armor_fit_slots(selected, required_slots=required_slots)
    ordered_slots = [slot for slot in MAJOR_ARMOR_SLOTS if slot in set(audit["selected_slots"])]
    audit = {**audit, "selected_slots": ordered_slots}
    scales = recommend_slot_scales(height, ordered_slots)
    slots = {
        slot: {
            **ARMOR_SLOT_SPECS[slot].to_dict(),
            "recommended_scale": scales[slot],
        }
        for slot in audit["selected_slots"]
    }
    validation = {
        **audit,
        "can_render_core": not audit["missing_required_slots"] and not audit["unknown_required_slots"],
        "balanced_pairs": not audit["missing_mirror_pairs"],
    }
    return {
        "contract_version": ARMOR_FIT_CONTRACT_VERSION,
        "baseline_height_cm": BASELINE_HEIGHT_CM,
        "height_cm": height,
        "height_scale": round(height / BASELINE_HEIGHT_CM, 4),
        "source": "suitspec.body_profile",
        "selected_parts": selected,
        "selected_slots": audit["selected_slots"],
        "required_slots": audit["required_slots"],
        "recommended_scales": scales,
        "slots": slots,
        "validation": validation,
    }


def visual_layer_slot_summary(body_fit_contract: dict[str, Any]) -> list[dict[str, Any]]:
    slots = body_fit_contract.get("slots") if isinstance(body_fit_contract.get("slots"), dict) else {}
    selected_slots = body_fit_contract.get("selected_slots")
    if not isinstance(selected_slots, list):
        selected_slots = list(slots)
    summary = []
    for slot in selected_slots:
        spec = slots.get(slot)
        if not isinstance(spec, dict):
            continue
        summary.append(
            {
                "slot_id": spec.get("runtime_part_id"),
                "body_fit_slot_id": slot,
                "runtime_part_id": spec.get("runtime_part_id"),
                "body_anchor": spec.get("body_anchor"),
                "mirror_pair": spec.get("mirror_pair"),
                "coverage": list(spec.get("coverage") or []),
                "recommended_scale": spec.get("recommended_scale"),
                "display_label": spec.get("display_label"),
            }
        )
    return summary


def _normalize_slot_collection(
    slots: Iterable[str],
    *,
    fail_on_unknown: bool,
) -> tuple[list[str], list[str]]:
    normalized = []
    unknown = []
    seen = set()
    for raw_slot in _slot_list(slots):
        token = _slot_token(raw_slot)
        canonical = SLOT_ALIASES.get(token, token)
        if canonical not in ARMOR_SLOT_SPECS:
            unknown.append(str(raw_slot))
            continue
        if canonical not in seen:
            seen.add(canonical)
            normalized.append(canonical)
    if fail_on_unknown and unknown:
        raise ValueError(f"unknown armor slots: {unknown}")
    return normalized, unknown


def _slot_list(slots: Iterable[str]) -> list[str]:
    if isinstance(slots, str):
        return [slots]
    return list(slots)


def _enabled_module_slots(suitspec: dict[str, Any]) -> list[str]:
    modules = suitspec.get("modules") if isinstance(suitspec.get("modules"), dict) else {}
    return sorted(
        part_name
        for part_name, module in modules.items()
        if isinstance(module, dict) and module.get("enabled") is True
    )


def _slot_token(slot_id: str) -> str:
    return str(slot_id).strip().lower().replace("-", "_")


def _coerce_height_cm(height_cm: float) -> float:
    try:
        height = round(float(height_cm), 1)
    except (TypeError, ValueError) as exc:
        raise ValueError("height_cm must be a number") from exc
    if not (MIN_SUPPORTED_HEIGHT_CM <= height <= MAX_SUPPORTED_HEIGHT_CM):
        raise ValueError(
            f"height_cm must be between {int(MIN_SUPPORTED_HEIGHT_CM)} and {int(MAX_SUPPORTED_HEIGHT_CM)}"
        )
    return height


def _part_id_for_style(slot_id: str, part_id_style: str) -> str:
    if part_id_style == "canonical":
        return slot_id
    if part_id_style == "runtime":
        return ARMOR_SLOT_SPECS[slot_id].runtime_part_id
    raise ValueError("part_id_style must be 'runtime' or 'canonical'")


def _audit_error_message(audit: dict[str, Any]) -> str:
    parts = []
    if audit["missing_required_slots"]:
        parts.append(f"missing required slots: {audit['missing_required_slots']}")
    if audit["missing_mirror_pairs"]:
        parts.append(f"missing mirror pairs: {audit['missing_mirror_pairs']}")
    if audit["unknown_slots"]:
        parts.append(f"unknown slots: {audit['unknown_slots']}")
    if audit["unknown_required_slots"]:
        parts.append(f"unknown required slots: {audit['unknown_required_slots']}")
    return "; ".join(parts) or "armor fit slot audit failed"


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


__all__ = [
    "ARMOR_FIT_CONTRACT_VERSION",
    "ARMOR_OVERLAY_LAYER_ID",
    "ARMOR_SLOT_SPECS",
    "ArmorSlotSpec",
    "BASELINE_HEIGHT_CM",
    "BASE_SUIT_LAYER_ID",
    "DEFAULT_VRM_BASELINE_REF",
    "MAJOR_ARMOR_SLOTS",
    "MAX_SUPPORTED_HEIGHT_CM",
    "MIN_SUPPORTED_HEIGHT_CM",
    "MIRROR_SLOT_PAIRS",
    "REQUIRED_RUNTIME_SLOTS",
    "RUNTIME_VISUAL_LAYER_CONTRACT_VERSION",
    "SLOT_ALIASES",
    "audit_armor_fit_slots",
    "build_body_fit_contract",
    "normalize_slot_id",
    "recommend_scale_for_height_cm",
    "recommend_slot_scales",
    "slot_specs_as_dict",
    "to_runtime_visual_layers",
    "visual_layer_slot_summary",
]
