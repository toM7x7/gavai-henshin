"""Structured UV engineering contracts for modular armor textures."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any


@dataclass(frozen=True, slots=True)
class UVContract:
    fill_ratio_target: tuple[int, int] = (82, 96)
    blank_area_max_percent: int = 10
    seam_safe_margin_percent: tuple[int, int] = (3, 5)
    symmetry_rule: str = (
        "Preserve bilateral logic on the dominant front-facing islands and keep mirrored surface lanes mechanically readable."
    )
    primary_motif_zone: str = "Place the highest-value visual identity on the forward-facing load-bearing islands."
    low_frequency_zone: str = "Keep seam borders, wrap edges, and fold-under surfaces low-frequency and materially calm."
    panel_flow_direction: str = "Run major panel splits along the load path and along the natural wrap direction of the part."
    forbidden_detail_zone: str = (
        "Do not place dense greeble, sharp emissive cuts, or decals in distortion-heavy corners, seam borders, or hidden underlaps."
    )
    island_layout_rule: str = (
        "Treat each UV island as an engineering surface. Do not paint cast shadows, camera perspective, or floating object silhouettes."
    )


BASE_CONTRACT = UVContract()


def _helmet_contract() -> UVContract:
    return replace(
        BASE_CONTRACT,
        fill_ratio_target=(88, 96),
        seam_safe_margin_percent=(4, 5),
        symmetry_rule="Keep visor band, brow line, and crown lanes centered so the helmet reads as a production-symmetric shell.",
        primary_motif_zone="Visor band, brow ridge, and frontal crown islands carry the identity of the suit line.",
        low_frequency_zone="Rear seam strip, neck ring, and extreme left/right wrap edges stay low-frequency for distortion tolerance.",
        panel_flow_direction="Panel rhythm flows from brow to crown to occipital shell, with uninterrupted visor framing.",
        forbidden_detail_zone="Avoid high-contrast features on the rear seam, neck edge, and extreme wrap edges.",
    )


def _chest_contract() -> UVContract:
    return replace(
        BASE_CONTRACT,
        fill_ratio_target=(90, 96),
        seam_safe_margin_percent=(4, 5),
        symmetry_rule="Keep sternum line, pectoral masses, and anchor plates left-right coherent around the centerline.",
        primary_motif_zone="Sternum core, upper pectoral shields, and central service hatches define the identity.",
        low_frequency_zone="Under-arm borders, lower side wraps, and outer seams remain calm to survive deformation and occlusion.",
        panel_flow_direction="Panel flow should reinforce the sternum axis and rib-to-shoulder load transfer.",
        forbidden_detail_zone="Do not cluster emissives or tiny fasteners near side seams and under-arm wrap boundaries.",
    )


def _back_contract() -> UVContract:
    return replace(
        BASE_CONTRACT,
        fill_ratio_target=(84, 94),
        symmetry_rule="Keep spine channel, mount rails, and dorsal service cuts aligned to the vertical center axis.",
        primary_motif_zone="Spine channel and dorsal equipment mounts carry the visual identity.",
        low_frequency_zone="Side wrap edges and lower lumbar border remain low-frequency to avoid wrap noise.",
        panel_flow_direction="Surface logic runs vertically along the spine with secondary bands feeding into shoulder and waist mounts.",
    )


def _shoulder_contract(side: str) -> UVContract:
    return replace(
        BASE_CONTRACT,
        fill_ratio_target=(82, 92),
        seam_safe_margin_percent=(4, 5),
        symmetry_rule=f"The {side} shoulder must read as one half of a mirrored pair, with the dominant crest centered on the cap island.",
        primary_motif_zone="Cap plate, forward strike face, and upper mount ring define the module identity.",
        low_frequency_zone="Rear wrap edge and under-cap junction remain simple for seam tolerance.",
        panel_flow_direction="Panel splits should wrap from collar mount to outer cap to rear deflection plane.",
        forbidden_detail_zone="Do not place dense vents or micro-emissives on the rear cap seam or under-cap fold.",
    )


def _upperarm_contract(side: str) -> UVContract:
    return replace(
        BASE_CONTRACT,
        fill_ratio_target=(82, 92),
        primary_motif_zone=f"{side.capitalize()} upper-arm forward strike face and tool-side armor lane carry identity.",
        low_frequency_zone="Inner arm seam lane and upper/lower cuff edges stay low-frequency.",
        panel_flow_direction="Longitudinal panel lanes should follow the sleeve wrap direction and elbow clearance.",
    )


def _forearm_contract(side: str) -> UVContract:
    return replace(
        BASE_CONTRACT,
        fill_ratio_target=(84, 94),
        primary_motif_zone=f"{side.capitalize()} forearm dorsal plate, wrist cuff, and hardpoint lane define the module.",
        low_frequency_zone="Inner seam, wrist edge, and elbow-side fold remain low-frequency.",
        panel_flow_direction="Panel flow should follow the gauntlet axis and terminate cleanly into the wrist cuff.",
        forbidden_detail_zone="Do not put dense detail where the wrist roll or inner seam will distort most.",
    )


def _waist_contract() -> UVContract:
    return replace(
        BASE_CONTRACT,
        fill_ratio_target=(84, 94),
        symmetry_rule="Keep abdomen guard and belt modules coherent around the centerline while allowing service segmentation.",
        primary_motif_zone="Front abdomen band, buckle-equivalent hardpoint, and side transfer plates define identity.",
        low_frequency_zone="Extreme left/right wrap edges and underside belt return stay calm.",
        panel_flow_direction="Use horizontal banding with controlled vertical breaks for flex and service access.",
    )


def _thigh_contract(side: str) -> UVContract:
    return replace(
        BASE_CONTRACT,
        fill_ratio_target=(84, 94),
        primary_motif_zone=f"{side.capitalize()} thigh forward strike face and outer service rail define the module.",
        low_frequency_zone="Inner thigh seam and top/bottom cuff edges remain low-frequency.",
        panel_flow_direction="Panel lines follow the limb axis and knee approach, not random diagonal decoration.",
    )


def _shin_contract(side: str) -> UVContract:
    return replace(
        BASE_CONTRACT,
        fill_ratio_target=(84, 94),
        primary_motif_zone=f"{side.capitalize()} shin front plate, ankle transfer line, and upper knee approach define identity.",
        low_frequency_zone="Back seam, ankle fold, and side wrap edges remain calm.",
        panel_flow_direction="Surface logic tapers from knee approach into shin crest and then into ankle transition.",
    )


def _boot_contract(side: str) -> UVContract:
    return replace(
        BASE_CONTRACT,
        fill_ratio_target=(82, 92),
        primary_motif_zone=f"{side.capitalize()} toe cap, instep shield, and heel stabilizer carry the visual identity.",
        low_frequency_zone="Sole edge, ankle fold, and deep side wraps stay low-frequency.",
        panel_flow_direction="Panel breaks must respect gait direction, toe roll, and heel stabilizer logic.",
        forbidden_detail_zone="Avoid delicate detail at the sole edge, ankle crease, and tight lateral wraps.",
    )


def _hand_contract(side: str) -> UVContract:
    return replace(
        BASE_CONTRACT,
        fill_ratio_target=(82, 90),
        primary_motif_zone=f"{side.capitalize()} back-of-hand shield and knuckle lanes define the module.",
        low_frequency_zone="Finger side seams, palm wrap edges, and wrist return remain calm.",
        panel_flow_direction="Back-of-hand lanes should run wrist to knuckle with clean finger segmentation.",
        forbidden_detail_zone="Do not place tiny insignia or high-contrast cuts on finger seam edges or palm folds.",
    )


DEFAULT_UV_CONTRACTS: dict[str, UVContract] = {
    "helmet": _helmet_contract(),
    "chest": _chest_contract(),
    "back": _back_contract(),
    "left_shoulder": _shoulder_contract("left"),
    "right_shoulder": _shoulder_contract("right"),
    "left_upperarm": _upperarm_contract("left"),
    "right_upperarm": _upperarm_contract("right"),
    "left_forearm": _forearm_contract("left"),
    "right_forearm": _forearm_contract("right"),
    "waist": _waist_contract(),
    "left_thigh": _thigh_contract("left"),
    "right_thigh": _thigh_contract("right"),
    "left_shin": _shin_contract("left"),
    "right_shin": _shin_contract("right"),
    "left_boot": _boot_contract("left"),
    "right_boot": _boot_contract("right"),
    "left_hand": _hand_contract("left"),
    "right_hand": _hand_contract("right"),
}


def _coerce_range(value: Any, default: tuple[int, int]) -> tuple[int, int]:
    if (
        isinstance(value, (list, tuple))
        and len(value) == 2
        and all(isinstance(item, (int, float)) for item in value)
    ):
        return (int(value[0]), int(value[1]))
    return default


def _apply_uv_overrides(base: UVContract, overrides: dict[str, Any] | None) -> UVContract:
    if not isinstance(overrides, dict):
        return base
    payload: dict[str, Any] = {}
    for field in UVContract.__dataclass_fields__:
        if field not in overrides:
            continue
        value = overrides[field]
        if field in {"fill_ratio_target", "seam_safe_margin_percent"}:
            payload[field] = _coerce_range(value, getattr(base, field))
        elif field == "blank_area_max_percent" and isinstance(value, (int, float)):
            payload[field] = int(value)
        elif isinstance(value, str) and value.strip():
            payload[field] = value.strip()
    if not payload:
        return base
    return replace(base, **payload)


def resolve_uv_contract(suitspec: dict[str, Any], part: str) -> UVContract:
    base = DEFAULT_UV_CONTRACTS.get(part, BASE_CONTRACT)
    root_overrides = suitspec.get("uv_contracts", {}).get(part)
    module_overrides = suitspec.get("modules", {}).get(part, {}).get("uv_contract")
    return _apply_uv_overrides(_apply_uv_overrides(base, root_overrides), module_overrides)


def serialize_uv_contract(contract: UVContract) -> dict[str, Any]:
    payload = asdict(contract)
    payload["fill_ratio_target"] = list(contract.fill_ratio_target)
    payload["seam_safe_margin_percent"] = list(contract.seam_safe_margin_percent)
    return payload

