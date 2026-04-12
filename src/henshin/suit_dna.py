"""Whole-suit design DNA for coherent modular armor generation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any


@dataclass(frozen=True, slots=True)
class SuitDesignDNA:
    manufacturer_family: str = "Aegis Yard modular exo-armor line"
    armor_generation: str = "Field-serviceable Mk-II inspection frame"
    silhouette_keywords: tuple[str, ...] = (
        "visor-led helm",
        "sternum-core chest",
        "modular pauldron shoulders",
        "serviceable limb sleeves",
    )
    panel_language: str = (
        "Stepped hard-surface plates with explicit service cuts, actuator clearances, and replaceable access covers"
    )
    fastener_family: str = "Flush hex-lock fasteners and recessed latch seams on service edges"
    emissive_routing: str = "Thin diagnostic emissive channels reserved for visor, sternum core, and power transfer junctions"
    maintenance_philosophy: str = "Inspection-first modularity; damaged parts can be removed independently by a dock technician"
    damage_policy: str = "Wear is concentrated on leading edges, hatch lips, and tool-contact surfaces; never random noise everywhere"
    material_stack: str = "Ceramic-coated titanium shell over composite subframe with gasketed joints and sacrificial edge trims"
    dock_readiness: str = (
        "When the modules are displayed separately in a maintenance dock, they must still read as one production family with matched panel rhythm, fastener spacing, and emissive hierarchy"
    )


PART_FUNCTION_RULES: dict[str, str] = {
    "helmet": "Read as a sensor crown, visor cassette, comms enclosure, and maintenance-latched shell rather than a decorative helmet prop.",
    "chest": "Read as the power-dense torso shell with sternum access, harness load transfer, and core protection logic.",
    "back": "Read as dorsal service armor with spine channeling, thermal exhaust management, and mount hardware continuity.",
    "left_shoulder": "Read as the left shoulder deflection and mount module with rotation clearance and identification surface logic.",
    "right_shoulder": "Read as the right shoulder deflection and mount module with rotation clearance and identification surface logic.",
    "left_upperarm": "Read as the left upper-arm sleeve with actuator clearance, removable service cover, and strike-face hierarchy.",
    "right_upperarm": "Read as the right upper-arm sleeve with actuator clearance, removable service cover, and strike-face hierarchy.",
    "left_forearm": "Read as the left gauntlet with wrist cuff logic, hardpoint lane, cable routing, and tool-robust surfaces.",
    "right_forearm": "Read as the right gauntlet with wrist cuff logic, hardpoint lane, cable routing, and tool-robust surfaces.",
    "waist": "Read as the abdomen and belt transfer module that bridges torso rigidity with hip articulation and service segmentation.",
    "left_thigh": "Read as the left thigh armor with load-bearing forward face, mount rail continuity, and replacement-friendly segmentation.",
    "right_thigh": "Read as the right thigh armor with load-bearing forward face, mount rail continuity, and replacement-friendly segmentation.",
    "left_shin": "Read as the left shin and ankle transfer shell with front crest hierarchy and grounded gait mechanics.",
    "right_shin": "Read as the right shin and ankle transfer shell with front crest hierarchy and grounded gait mechanics.",
    "left_boot": "Read as the left armored boot with toe-roll mechanics, heel stabilizer logic, and serviceable sole transition.",
    "right_boot": "Read as the right armored boot with toe-roll mechanics, heel stabilizer logic, and serviceable sole transition.",
    "left_hand": "Read as the left hand shell with back-of-hand protection, knuckle articulation lanes, and wrist docking continuity.",
    "right_hand": "Read as the right hand shell with back-of-hand protection, knuckle articulation lanes, and wrist docking continuity.",
}


def _normalize_keywords(value: Any, default: tuple[str, ...]) -> tuple[str, ...]:
    if isinstance(value, str):
        items = [item.strip() for item in value.split(",") if item.strip()]
        return tuple(items) or default
    if isinstance(value, (list, tuple)):
        items = [str(item).strip() for item in value if str(item).strip()]
        return tuple(items) or default
    return default


def _apply_dna_overrides(base: SuitDesignDNA, overrides: dict[str, Any] | None) -> SuitDesignDNA:
    if not isinstance(overrides, dict):
        return base
    payload: dict[str, Any] = {}
    for field in SuitDesignDNA.__dataclass_fields__:
        if field not in overrides:
            continue
        value = overrides[field]
        if field == "silhouette_keywords":
            payload[field] = _normalize_keywords(value, base.silhouette_keywords)
        elif isinstance(value, str) and value.strip():
            payload[field] = value.strip()
    if not payload:
        return base
    return replace(base, **payload)


def resolve_suit_design_dna(suitspec: dict[str, Any]) -> SuitDesignDNA:
    style_tags = {str(tag).strip().lower() for tag in suitspec.get("style_tags") or []}
    dna = SuitDesignDNA()
    if "audit" in style_tags:
        dna = replace(
            dna,
            maintenance_philosophy=(
                "Inspection-first modularity with exposed service logic; every module should look removable and traceable by a dock technician"
            ),
            damage_policy=(
                "Wear appears on access points, leading edges, and repeated maintenance contact surfaces; avoid theatrical grime"
            ),
        )
    if "visor" in style_tags:
        dna = replace(
            dna,
            silhouette_keywords=tuple(dict.fromkeys((*dna.silhouette_keywords, "continuous visor band"))),
        )
    root_overrides = suitspec.get("design_dna")
    generation_overrides = suitspec.get("generation", {}).get("design_dna")
    return _apply_dna_overrides(_apply_dna_overrides(dna, root_overrides), generation_overrides)


def describe_part_function(part: str) -> str:
    return PART_FUNCTION_RULES.get(
        part,
        "Read as a real modular armor component with clear service logic, load path, and docking identity.",
    )


def serialize_suit_design_dna(dna: SuitDesignDNA) -> dict[str, Any]:
    payload = asdict(dna)
    payload["silhouette_keywords"] = list(dna.silhouette_keywords)
    return payload

