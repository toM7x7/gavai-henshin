"""Procedural shape specs for 18 tokusatsu hero armor modules.

Drives Blender modeling. Read-only data. Pairs with
`src/henshin/modeler_blueprints.py`. All units are meters in the
module-local frame: origin at part pivot center, +X wearer-left,
+Y proximal-to-distal/up, +Z outward visible surface.

Right-side modules declare `mirror_of: "left_*"`; the Blender pipeline
mirrors by negating x.

Wave 1 silhouette overhaul: uses `body_wrap_arc` curved-shell primitive on
torso/limb modules so panels wrap the body cylinder instead of reading as
flat tiles. Targets follow `_blueprint_snapshot.json::authoring_target_m`.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


SPEC_CONTRACT_VERSION = "armor-part-spec.v1"

MATERIAL_PALETTE: dict[str, str] = {
    "base_surface": "#E8EEF5",
    "accent": "#1B6FE0",
    "emissive": "#2EE6FF",
    "trim": "#1A2230",
}

_CLEARANCE_M = {
    "head": 0.018, "torso": 0.024, "dorsal": 0.026, "waist": 0.022,
    "shoulder": 0.028, "arm": 0.018, "hand": 0.014, "leg": 0.02,
    "foot": 0.018,
}
_THICKNESS_M = {
    "head": 0.035, "torso": 0.045, "dorsal": 0.05, "waist": 0.034,
    "shoulder": 0.038, "arm": 0.028, "hand": 0.02, "leg": 0.03,
    "foot": 0.032,
}
_TRI_BUDGET = {
    "head": 1800, "torso": 1800, "dorsal": 1600, "waist": 1200,
    "shoulder": 900, "arm": 1100, "hand": 700, "leg": 1100, "foot": 900,
}

_BASE_MOTIF_LINKS: dict[str, dict[str, str]] = {
    "helmet": {"name": "head_crest_line", "surface_zone": "emissive"},
    "chest": {"name": "chest_v_stripe", "surface_zone": "emissive"},
    "back": {"name": "spine_line", "surface_zone": "accent"},
    "waist": {"name": "belt_band", "surface_zone": "accent"},
    "left_shoulder": {"name": "shoulder_arc", "surface_zone": "accent"},
    "right_shoulder": {"name": "shoulder_arc", "surface_zone": "accent"},
    "left_upperarm": {"name": "arm_stripe", "surface_zone": "accent"},
    "right_upperarm": {"name": "arm_stripe", "surface_zone": "accent"},
    "left_forearm": {"name": "wrist_band", "surface_zone": "accent"},
    "right_forearm": {"name": "wrist_band", "surface_zone": "accent"},
    "left_hand": {"name": "knuckle_glow", "surface_zone": "emissive"},
    "right_hand": {"name": "knuckle_glow", "surface_zone": "emissive"},
    "left_thigh": {"name": "thigh_stripe", "surface_zone": "accent"},
    "right_thigh": {"name": "thigh_stripe", "surface_zone": "accent"},
    "left_shin": {"name": "shin_v", "surface_zone": "emissive"},
    "right_shin": {"name": "shin_v", "surface_zone": "emissive"},
    "left_boot": {"name": "boot_instep_glow", "surface_zone": "emissive"},
    "right_boot": {"name": "boot_instep_glow", "surface_zone": "emissive"},
}

_ATTACHMENT_OFFSET_TARGETS_M: dict[str, float] = {
    "helmet": 0.08,
    "chest": 0.08,
    "back": 0.08,
    "waist": 0.06,
    "shoulder": 0.04,
    "upperarm": 0.04,
    "forearm": 0.04,
    "hand": 0.04,
    "thigh": 0.04,
    "shin": 0.04,
    "boot": 0.06,
}


def _shoulder_slots(side_x: float) -> list[dict[str, Any]]:
    return [
        {
            "topping_slot": "shoulder_fin",
            "slot_transform": {"anchor": [side_x * 0.07, 0.0, 0.08], "rotation_deg": [0, 0, 0]},
            "max_bbox_m": {"x": 0.10, "y": 0.12, "z": 0.040},
            "conflicts_with": ["edge_trim"],
        },
        {
            "topping_slot": "edge_trim",
            "slot_transform": {"anchor": [side_x * 0.04, 0.0, 0.10], "rotation_deg": [0, 0, 0]},
            "max_bbox_m": {"x": 0.16, "y": 0.04, "z": 0.020},
            "conflicts_with": [],
        },
    ]


def _shin_slots(side_x: float) -> list[dict[str, Any]]:
    return [
        {
            "topping_slot": "shin_spike",
            "slot_transform": {"anchor": [side_x * 0.0, 0.04, 0.06], "rotation_deg": [0, 0, 0]},
            "max_bbox_m": {"x": 0.06, "y": 0.12, "z": 0.040},
            "conflicts_with": ["ankle_cuff_trim"],
        },
        {
            "topping_slot": "ankle_cuff_trim",
            "slot_transform": {"anchor": [side_x * 0.0, -0.16, 0.0], "rotation_deg": [0, 0, 0]},
            "max_bbox_m": {"x": 0.10, "y": 0.04, "z": 0.020},
            "conflicts_with": [],
        },
    ]


def _thigh_slots(side_x: float) -> list[dict[str, Any]]:
    return [
        {
            "topping_slot": "hip_side_fin",
            "slot_transform": {"anchor": [side_x * 0.05, 0.11, 0.06], "rotation_deg": [0, 0, 0]},
            "max_bbox_m": {"x": 0.045, "y": 0.12, "z": 0.035},
            "conflicts_with": ["knee_lip_trim"],
        },
        {
            "topping_slot": "knee_lip_trim",
            "slot_transform": {"anchor": [side_x * 0.0, -0.17, 0.06], "rotation_deg": [0, 0, 0]},
            "max_bbox_m": {"x": 0.09, "y": 0.035, "z": 0.025},
            "conflicts_with": [],
        },
    ]


def _boot_slots(side_x: float) -> list[dict[str, Any]]:
    return [
        {
            "topping_slot": "toe_fin",
            "slot_transform": {"anchor": [side_x * 0.0, 0.0, 0.13], "rotation_deg": [0, 0, 0]},
            "max_bbox_m": {"x": 0.075, "y": 0.035, "z": 0.045},
            "conflicts_with": ["heel_spur"],
        },
        {
            "topping_slot": "heel_spur",
            "slot_transform": {"anchor": [side_x * 0.0, 0.0, -0.13], "rotation_deg": [0, 0, 0]},
            "max_bbox_m": {"x": 0.075, "y": 0.035, "z": 0.045},
            "conflicts_with": [],
        },
    ]


_TOPPING_SLOT_DEFAULTS: dict[str, list[dict[str, Any]]] = {
    "helmet": [
        {
            "topping_slot": "crest",
            "slot_transform": {"anchor": [0.0, 0.16, 0.0], "rotation_deg": [0, 0, 0]},
            "max_bbox_m": {"x": 0.08, "y": 0.12, "z": 0.06},
            "conflicts_with": ["visor_trim"],
        },
        {
            "topping_slot": "visor_trim",
            "slot_transform": {"anchor": [0.0, 0.04, 0.10], "rotation_deg": [0, 0, 0]},
            "max_bbox_m": {"x": 0.20, "y": 0.04, "z": 0.02},
            "conflicts_with": [],
        },
    ],
    "chest": [
        {
            "topping_slot": "chest_core",
            "slot_transform": {"anchor": [0.0, 0.04, 0.07], "rotation_deg": [0, 0, 0]},
            "max_bbox_m": {"x": 0.14, "y": 0.12, "z": 0.035},
            "conflicts_with": ["rib_trim"],
        },
        {
            "topping_slot": "rib_trim",
            "slot_transform": {"anchor": [0.0, -0.10, 0.07], "rotation_deg": [0, 0, 0]},
            "max_bbox_m": {"x": 0.40, "y": 0.04, "z": 0.025},
            "conflicts_with": [],
        },
    ],
    "back": [
        {
            "topping_slot": "spine_ridge",
            "slot_transform": {"anchor": [0.0, 0.0, -0.07], "rotation_deg": [0, 0, 0]},
            "max_bbox_m": {"x": 0.12, "y": 0.20, "z": 0.040},
            "conflicts_with": ["rear_core"],
        },
        {
            "topping_slot": "rear_core",
            "slot_transform": {"anchor": [0.0, 0.0, -0.05], "rotation_deg": [0, 0, 0]},
            "max_bbox_m": {"x": 0.18, "y": 0.18, "z": 0.030},
            "conflicts_with": [],
        },
    ],
    "waist": [
        {
            "topping_slot": "belt_buckle",
            "slot_transform": {"anchor": [0.0, 0.0, 0.08], "rotation_deg": [0, 0, 0]},
            "max_bbox_m": {"x": 0.16, "y": 0.08, "z": 0.035},
            "conflicts_with": [],
        },
        {
            "topping_slot": "side_clip",
            "slot_transform": {"anchor": [0.18, 0.0, 0.0], "rotation_deg": [0, 0, 0]},
            "max_bbox_m": {"x": 0.06, "y": 0.06, "z": 0.030},
            "conflicts_with": [],
        },
    ],
    "left_shoulder": _shoulder_slots(side_x=1.0),
    "right_shoulder": _shoulder_slots(side_x=-1.0),
    "left_thigh": _thigh_slots(side_x=1.0),
    "right_thigh": _thigh_slots(side_x=-1.0),
    "left_shin": _shin_slots(side_x=1.0),
    "right_shin": _shin_slots(side_x=-1.0),
    "left_boot": _boot_slots(side_x=1.0),
    "right_boot": _boot_slots(side_x=-1.0),
}

_ENVELOPE = {
    "helmet":         {"x": 0.2856, "y": 0.34,   "z": 0.2584},
    "chest":          {"x": 0.6392, "y": 0.4992, "z": 0.1632},
    "back":           {"x": 0.5984, "y": 0.5148, "z": 0.136},
    "waist":          {"x": 0.4896, "y": 0.1716, "z": 0.1904},
    "left_shoulder":  {"x": 0.1904, "y": 0.1224, "z": 0.1632},
    "left_upperarm":  {"x": 0.1088, "y": 0.2924, "z": 0.1088},
    "left_forearm":   {"x": 0.102,  "y": 0.2788, "z": 0.102},
    "left_hand":      {"x": 0.1156, "y": 0.0816, "z": 0.136},
    "left_thigh":     {"x": 0.136,  "y": 0.3956, "z": 0.1292},
    "left_shin":      {"x": 0.1156, "y": 0.3956, "z": 0.1156},
    "left_boot":      {"x": 0.1224, "y": 0.0884, "z": 0.2856},
}


def _attachment_offset_key(module: str) -> str:
    if module.startswith("left_"):
        return module[len("left_"):]
    if module.startswith("right_"):
        return module[len("right_"):]
    return module


def _topping_slots_for(module: str) -> list[dict[str, Any]]:
    slots = deepcopy(_TOPPING_SLOT_DEFAULTS.get(module, []))
    for slot in slots:
        slot["parent_module"] = module
    return slots


def _panel(
    name: str,
    primitive: str,
    anchor: tuple[float, float, float],
    size: tuple[float, float, float],
    *,
    rotation_deg: tuple[float, float, float] = (0.0, 0.0, 0.0),
    bevel_m: float = 0.004,
    material_zone: str = "base_surface",
    emissive_grooves: list[dict[str, Any]] | None = None,
    comment: str = "",
    **extras: Any,
) -> dict[str, Any]:
    """Standard panel spec. ``extras`` carry primitive-specific keys
    (arc_deg, front_bulge, segments, thickness_z, etc.) and are merged in."""
    panel: dict[str, Any] = {
        "name": name,
        "primitive": primitive,
        "anchor": list(anchor),
        "size": list(size),
        "rotation_deg": list(rotation_deg),
        "bevel_m": bevel_m,
        "material_zone": material_zone,
        "emissive_grooves": list(emissive_grooves or []),
        "comment": comment,
    }
    for k, v in extras.items():
        panel[k] = v
    return panel


def _groove(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    *,
    width_m: float = 0.012,
    depth_m: float = 0.004,
) -> dict[str, Any]:
    return {
        "start": list(start),
        "end": list(end),
        "width_m": width_m,
        "depth_m": depth_m,
    }


def _base(
    module: str,
    category: str,
    wave: str,
    *,
    mirror_of: str | None = None,
    side: str = "center",
) -> dict[str, Any]:
    envelope_key = mirror_of if mirror_of else module
    envelope = _ENVELOPE[envelope_key]
    return {
        "module": module,
        "category": category,
        "wave": wave,
        "mirror_of": mirror_of,
        "side": side,
        "target_envelope_m": dict(envelope),
        "clearance_m": _CLEARANCE_M[category],
        "shell_thickness_m": _THICKNESS_M[category],
        "tri_budget": _TRI_BUDGET[category],
        "material_zones_palette": dict(MATERIAL_PALETTE),
        "variant_key": f"{module}:base",
        "part_family": "silver_hero",
        "base_motif_link": dict(_BASE_MOTIF_LINKS[module]),
        "topping_slots": _topping_slots_for(module),
        "attachment_offset_target_m": _ATTACHMENT_OFFSET_TARGETS_M[_attachment_offset_key(module)],
    }


def _helmet_spec() -> dict[str, Any]:
    # target_envelope_m: x=0.2856, y=0.34, z=0.2584
    spec = _base("helmet", "head", "wave_3_head_hands")
    ex, ey, ez = _ENVELOPE["helmet"]["x"], _ENVELOPE["helmet"]["y"], _ENVELOPE["helmet"]["z"]
    panels = [
        _panel("helmet_dome", "rounded_box",
            anchor=(0.0, 0.025, 0.0),
            size=(ex * 0.98, ey * 0.92, ez * 0.98),
            bevel_m=0.000, material_zone="base_surface",
            organic_rounding=True,
            segments=28, rings=14,
            comment="Main dome volume; ellipsoid removes the cube-box read while keeping target depth."),
        _panel("helmet_visor_band", "trim_ridge",
            anchor=(0.0, ey * 0.06, ez * 0.42),
            size=(ex * 0.84, ey * 0.16, 0.022),
            bevel_m=0.003, material_zone="emissive",
            comment="Visor band emissive strip across forehead."),
        _panel("helmet_crest_fin", "rounded_box",
            anchor=(0.0, ey * 0.36, 0.0),
            size=(0.018, ey * 0.42, ez * 0.78),
            bevel_m=0.003, material_zone="accent",
            comment="Top crest fin; thin tall plate front-to-back."),
        _panel("helmet_ear_vent_left", "trim_ridge",
            anchor=(ex * 0.44, -0.02, 0.0),
            size=(0.020, ey * 0.30, ez * 0.46),
            bevel_m=0.003, material_zone="trim",
            comment="Left ear vent dark trim."),
        _panel("helmet_ear_vent_right", "trim_ridge",
            anchor=(-ex * 0.44, -0.02, 0.0),
            size=(0.020, ey * 0.30, ez * 0.46),
            bevel_m=0.003, material_zone="trim",
            comment="Right ear vent dark trim."),
        _panel("helmet_jaw_trim", "trim_ridge",
            anchor=(0.0, -ey * 0.42, ez * 0.18),
            size=(ex * 0.66, 0.026, ez * 0.46),
            bevel_m=0.003, material_zone="trim",
            comment="Jawline trim framing the lower edge."),
    ]
    spec["silhouette"] = {"panels": panels, "wrap_arc_deg": 0.0}
    spec["emissive_lines"] = [
        _groove((0.0, ey * 0.45, ez * 0.36), (0.0, -ey * 0.05, ez * 0.5),
                width_m=0.008, depth_m=0.003),
    ]
    spec["vrm_attachment_hint"] = {"primary_bone": "head",
        "offset_m": [0.0, 0.02, 0.04], "rotation_deg": [0.0, 0.0, 0.0]}
    spec["silhouette_review_notes"] = [
        "Ellipsoid dome reaches target depth z without a box silhouette.",
        "Crest + visor + jaw form clear hero silhouette without antenna assets.",
        "Ear vents stay dark to anchor silver dome.",
    ]
    return spec


def _chest_spec() -> dict[str, Any]:
    # target_envelope_m: x=0.6392, y=0.4992, z=0.1632
    spec = _base("chest", "torso", "wave_1_core")
    ex, ey, ez = _ENVELOPE["chest"]["x"], _ENVELOPE["chest"]["y"], _ENVELOPE["chest"]["z"]
    panels = [
        _panel("chest_pectoral_shell", "body_wrap_arc",
            anchor=(0.0, 0.055, 0.0),
            size=(0.64, 0.38, 0.026),
            bevel_m=0.006, material_zone="base_surface",
            arc_deg=82.0, front_bulge=0.020, segments=16,
            y_taper_top=0.04, y_taper_bottom=0.11,
            comment="Main pectoral wrap arc; wider/taller ribcage shell while staying within target depth."),
        _panel("chest_abdomen_wrap", "body_wrap_arc",
            anchor=(0.0, -0.17, 0.0),
            size=(0.54, 0.18, 0.020),
            bevel_m=0.005, material_zone="base_surface",
            arc_deg=70.0, front_bulge=0.010, segments=12,
            y_taper_top=0.04, y_taper_bottom=0.20,
            comment="Lower abdomen wrap, dropped to meet the belt without a floating gap."),
        _panel("chest_left_rib_follow", "body_wrap_arc",
            anchor=(ex * 0.30, -0.005, 0.004),
            size=(0.10, 0.34, 0.018),
            rotation_deg=(0.0, -26.0, 0.0),
            bevel_m=0.004, material_zone="base_surface",
            arc_deg=58.0, front_bulge=0.012, segments=8,
            y_taper_top=0.06, y_taper_bottom=0.12,
            comment="Left rib side follower; gives the chest a torso-hugging side return."),
        _panel("chest_right_rib_follow", "body_wrap_arc",
            anchor=(-ex * 0.30, -0.005, 0.004),
            size=(0.10, 0.34, 0.018),
            rotation_deg=(0.0, 26.0, 0.0),
            bevel_m=0.004, material_zone="base_surface",
            arc_deg=58.0, front_bulge=0.012, segments=8,
            y_taper_top=0.06, y_taper_bottom=0.12,
            comment="Right rib side follower; mirrors the torso-hugging side return."),
        _panel("chest_central_v", "rounded_box",
            anchor=(0.0, ey * 0.05, 0.060),
            size=(ex * 0.06, ey * 0.34, 0.012),
            bevel_m=0.003, material_zone="emissive",
            comment="Central V emissive stripe down sternum; height matches pectoral wrap."),
        _panel("chest_clavicle_trim", "trim_ridge",
            anchor=(0.0, ey * 0.40, 0.030),
            size=(ex * 0.74, 0.020, 0.020),
            rotation_deg=(8.0, 0.0, 0.0),
            bevel_m=0.003, material_zone="accent",
            comment="Clavicle accent ridge connecting both pectorals."),
    ]
    spec["silhouette"] = {"panels": panels, "wrap_arc_deg": 95.0}
    spec["emissive_lines"] = [
        _groove((0.0, ey * 0.4, ez * 0.5), (0.0, -ey * 0.5, ez * 0.5),
                width_m=0.014, depth_m=0.005),
    ]
    spec["vrm_attachment_hint"] = {"primary_bone": "upperChest",
        "offset_m": [0.0, 0.012, 0.064], "rotation_deg": [0.0, 0.0, 0.0]}
    spec["body_follow_profile"] = {
        "mode": "ribcage_wrap_with_side_returns",
        "depth_axis": "z",
        "anchor_bones": ["upperChest", "chest", "spine"],
        "follow_panels": [
            "chest_pectoral_shell", "chest_abdomen_wrap",
            "chest_left_rib_follow", "chest_right_rib_follow",
        ],
        "target_contact": "front shell and side ribs keep visible clearance from the body proxy",
    }
    spec["fit_alignment_notes"] = [
        "Pectoral shell is widened and raised to track the upperChest volume.",
        "Side rib followers reduce the flat tile read without expanding the global bbox.",
        "Lower abdomen wrap is dropped to meet the waist module cleanly.",
    ]
    spec["silhouette_review_notes"] = [
        "Single body_wrap_arc (chord 0.62, arc 80°) gives true ribcage curvature.",
        "Sagitta + bulge reach z ~ 0.16m, matching authoring target envelope.",
        "Central V hosts the cyan power-line emissive groove.",
    ]
    return spec


def _back_spec() -> dict[str, Any]:
    # target_envelope_m: x=0.5984, y=0.5148, z=0.136
    spec = _base("back", "dorsal", "wave_1_core")
    ex, ey, ez = _ENVELOPE["back"]["x"], _ENVELOPE["back"]["y"], _ENVELOPE["back"]["z"]
    panels = [
        _panel("back_main_shell", "body_wrap_arc",
            anchor=(0.0, 0.0, 0.0),
            size=(0.58, 0.505, 0.030),
            rotation_deg=(0.0, 180.0, 0.0),
            bevel_m=0.006, material_zone="base_surface",
            arc_deg=64.0, front_bulge=0.016, segments=16,
            y_taper_top=0.05, y_taper_bottom=0.12,
            comment="Main back wrap arc; tuned under target cap while keeping rear shell curvature."),
        _panel("back_spine_plate", "rounded_box",
            anchor=(0.0, 0.0, -0.055),
            size=(ex * 0.13, ey * 0.54, 0.010),
            bevel_m=0.004, material_zone="accent",
            comment="Central raised spine plate; gives the rear apex readable thickness."),
        _panel("back_spine_keel_upper", "rounded_box",
            anchor=(0.0, ey * 0.21, -0.058),
            size=(ex * 0.075, ey * 0.19, 0.008),
            bevel_m=0.003, material_zone="accent",
            comment="Upper segmented spine keel for vertebra-like rear depth."),
        _panel("back_spine_keel_lower", "rounded_box",
            anchor=(0.0, -ey * 0.20, -0.058),
            size=(ex * 0.070, ey * 0.20, 0.008),
            bevel_m=0.003, material_zone="accent",
            comment="Lower segmented spine keel continuing into lumbar wrap."),
        _panel("back_lumbar_wrap", "body_wrap_arc",
            anchor=(0.0, -ey * 0.34, 0.0),
            size=(0.50, 0.19, 0.026),
            rotation_deg=(0.0, 180.0, 0.0),
            bevel_m=0.004, material_zone="base_surface",
            arc_deg=60.0, front_bulge=0.006, segments=12,
            y_taper_top=0.06, y_taper_bottom=0.18,
            comment="Lumbar wrap; wider rear tuck to align with the waist back belt."),
        _panel("back_scapula_pad_left", "body_wrap_arc",
            anchor=(ex * 0.22, ey * 0.16, -0.020),
            size=(0.18, 0.24, 0.022),
            rotation_deg=(0.0, 180.0, 0.0),
            bevel_m=0.004, material_zone="base_surface",
            arc_deg=54.0, front_bulge=0.010, segments=8,
            y_taper_top=0.04, y_taper_bottom=0.08,
            comment="Left scapula fill pad; adds rear part density without exceeding depth cap."),
        _panel("back_scapula_pad_right", "body_wrap_arc",
            anchor=(-ex * 0.22, ey * 0.16, -0.020),
            size=(0.18, 0.24, 0.022),
            rotation_deg=(0.0, 180.0, 0.0),
            bevel_m=0.004, material_zone="base_surface",
            arc_deg=54.0, front_bulge=0.010, segments=8,
            y_taper_top=0.04, y_taper_bottom=0.08,
            comment="Right scapula fill pad; mirrors rear part density."),
        _panel("back_side_return_left", "trim_ridge",
            anchor=(ex * 0.44, -ey * 0.02, -0.020),
            size=(0.030, ey * 0.48, 0.024),
            rotation_deg=(0.0, -24.0, 0.0),
            bevel_m=0.003, material_zone="accent",
            comment="Left side return lip makes the dorsal armor wrap around the torso in profile."),
        _panel("back_side_return_right", "trim_ridge",
            anchor=(-ex * 0.44, -ey * 0.02, -0.020),
            size=(0.030, ey * 0.48, 0.024),
            rotation_deg=(0.0, 24.0, 0.0),
            bevel_m=0.003, material_zone="accent",
            comment="Right side return lip mirrors the left torso wrap cue."),
        _panel("back_rear_core_socket", "trim_ridge",
            anchor=(0.0, ey * 0.05, -0.064),
            size=(ex * 0.18, ey * 0.12, 0.010),
            bevel_m=0.003, material_zone="emissive",
            comment="Small rear power-core socket breaks up the thin rear silhouette."),
        _panel("back_wing_left", "trim_ridge",
            anchor=(ex * 0.30, ey * 0.32, -0.030),
            size=(ex * 0.22, 0.020, 0.022),
            rotation_deg=(0.0, -16.0, 0.0),
            bevel_m=0.003, material_zone="trim",
            comment="Upper-left scapula trim."),
        _panel("back_wing_right", "trim_ridge",
            anchor=(-ex * 0.30, ey * 0.32, -0.030),
            size=(ex * 0.22, 0.020, 0.022),
            rotation_deg=(0.0, 16.0, 0.0),
            bevel_m=0.003, material_zone="trim",
            comment="Upper-right scapula trim."),
    ]
    spec["silhouette"] = {"panels": panels, "wrap_arc_deg": 75.0}
    spec["emissive_lines"] = [
        _groove((0.0, ey * 0.46, -0.060), (0.0, -ey * 0.46, -0.060),
                width_m=0.010, depth_m=0.004),
    ]
    spec["vrm_attachment_hint"] = {"primary_bone": "upperChest",
        "offset_m": [0.0, 0.002, -0.070], "rotation_deg": [0.0, 180.0, 0.0]}
    spec["body_follow_profile"] = {
        "mode": "dorsal_wrap_with_scapula_and_spine_keel",
        "depth_axis": "z",
        "anchor_bones": ["upperChest", "chest", "spine"],
        "follow_panels": [
            "back_main_shell", "back_lumbar_wrap",
            "back_scapula_pad_left", "back_scapula_pad_right",
        ],
        "rear_apex_panels": [
            "back_spine_plate", "back_spine_keel_upper", "back_spine_keel_lower",
        ],
        "target_contact": "rear shell follows shoulder blade and lumbar zones, not a single flat slab",
    }
    spec["visual_density_profile"] = {
        "issue": "rear silhouette previously read thin in web preview",
        "hero_density_panels": [
            "back_spine_plate", "back_spine_keel_upper", "back_spine_keel_lower",
            "back_side_return_left", "back_side_return_right", "back_rear_core_socket",
        ],
        "profile_cues": ["side return lips", "central rear core", "scapula pads"],
    }
    spec["auxiliary_part_suggestions"] = [
        {
            "proposal_id": "back_scapula_aux_left",
            "parent_module": "back",
            "suggested_bone": "upperChest",
            "anchor_m": [round(ex * 0.24, 4), round(ey * 0.14, 4), -0.052],
            "size_m": [0.16, 0.22, 0.018],
            "reason": "Optional separate scapula plate if reviewers still see a thin rear shell.",
        },
        {
            "proposal_id": "back_scapula_aux_right",
            "parent_module": "back",
            "suggested_bone": "upperChest",
            "anchor_m": [round(-ex * 0.24, 4), round(ey * 0.14, 4), -0.052],
            "size_m": [0.16, 0.22, 0.018],
            "reason": "Mirror of the left optional scapula auxiliary plate.",
        },
    ]
    spec["fit_alignment_notes"] = [
        "Back shell depth is redistributed into spine keel and scapula pads instead of only expanding bbox z.",
        "Side return lips add profile thickness without relying on Web-only offsets.",
        "Lumbar wrap is widened to meet waist_belt_back and reduce rear gap.",
        "Attachment offset moves the module slightly farther rearward for body tracking.",
    ]
    spec["silhouette_review_notes"] = [
        "body_wrap_arc with Y=180 rotation -> apex at rear, wraps the back cylinder.",
        "Spine keel + scapula pads add rear visual thickness while staying near target z.",
        "Lumbar wrap tapers into the waist seam below.",
    ]
    return spec


def _waist_spec() -> dict[str, Any]:
    # target_envelope_m: x=0.4896, y=0.1716, z=0.1904
    spec = _base("waist", "waist", "wave_1_core")
    ex, ey, ez = _ENVELOPE["waist"]["x"], _ENVELOPE["waist"]["y"], _ENVELOPE["waist"]["z"]
    panels = [
        _panel("waist_front_wrap", "body_wrap_arc",
            anchor=(0.0, 0.0, 0.006),
            size=(0.43, 0.165, 0.046),
            bevel_m=0.005, material_zone="base_surface",
            arc_deg=112.0, front_bulge=0.022, segments=16,
            comment="Front belt wrap with more pelvis-following width and depth."),
        _panel("waist_side_plate_left", "rounded_box",
            anchor=(ex * 0.39, 0.0, 0.018),
            size=(ex * 0.22, ey * 0.90, 0.036),
            rotation_deg=(0.0, -18.0, 0.0),
            bevel_m=0.005, material_zone="base_surface",
            comment="Left hip side plate closes the belt without a flat front slab."),
        _panel("waist_side_plate_right", "rounded_box",
            anchor=(-ex * 0.39, 0.0, 0.018),
            size=(ex * 0.22, ey * 0.90, 0.036),
            rotation_deg=(0.0, 18.0, 0.0),
            bevel_m=0.005, material_zone="base_surface",
            comment="Right hip side plate mirrors the segmented belt read."),
        _panel("waist_buckle", "rounded_box",
            anchor=(0.0, 0.0, 0.084),
            size=(ex * 0.23, ey * 0.82, 0.026),
            bevel_m=0.005, material_zone="accent",
            comment="Front buckle; sits on wrap apex."),
        _panel("waist_buckle_emissive", "rounded_box",
            anchor=(0.0, 0.0, 0.094),
            size=(ex * 0.06, ey * 0.64, 0.010),
            bevel_m=0.002, material_zone="emissive",
            comment="Buckle inner cyan insert (continues chest V)."),
        _panel("waist_belt_back", "body_wrap_arc",
            anchor=(0.0, 0.0, -0.004),
            size=(0.46, 0.15, 0.042),
            rotation_deg=(0.0, 180.0, 0.0),
            bevel_m=0.004, material_zone="base_surface",
            arc_deg=128.0, front_bulge=0.016, segments=14,
            comment="Rear belt wrap; closes the loop and follows the lumbar module."),
        _panel("waist_rear_spine_clasp", "rounded_box",
            anchor=(0.0, -0.004, -0.082),
            size=(ex * 0.32, ey * 0.72, 0.018),
            bevel_m=0.003, material_zone="accent",
            comment="Rear clasp visually receives the back spine keel."),
        _panel("waist_oblique_lip_left", "trim_ridge",
            anchor=(ex * 0.30, 0.0, 0.045),
            size=(0.040, ey * 0.80, 0.016),
            rotation_deg=(0.0, -22.0, 0.0),
            bevel_m=0.002, material_zone="accent",
            comment="Left oblique lip aligns side plate to chest/hip flow."),
        _panel("waist_oblique_lip_right", "trim_ridge",
            anchor=(-ex * 0.30, 0.0, 0.045),
            size=(0.040, ey * 0.80, 0.016),
            rotation_deg=(0.0, 22.0, 0.0),
            bevel_m=0.002, material_zone="accent",
            comment="Right oblique lip aligns side plate to chest/hip flow."),
    ]
    spec["silhouette"] = {"panels": panels, "wrap_arc_deg": 135.0}
    spec["emissive_lines"] = [
        _groove((0.0, ey * 0.5, ez * 0.5), (0.0, -ey * 0.5, ez * 0.5),
                width_m=0.012, depth_m=0.004),
    ]
    spec["vrm_attachment_hint"] = {"primary_bone": "hips",
        "offset_m": [0.0, 0.006, 0.040], "rotation_deg": [0.0, 0.0, 0.0]}
    spec["body_follow_profile"] = {
        "mode": "pelvis_belt_loop_with_front_and_rear_clasps",
        "depth_axis": "z",
        "anchor_bones": ["hips", "spine"],
        "follow_panels": [
            "waist_front_wrap", "waist_belt_back",
            "waist_side_plate_left", "waist_side_plate_right",
        ],
        "rear_apex_panels": ["waist_rear_spine_clasp"],
        "target_contact": "front, side, and rear plates read as one belt loop around the pelvis",
    }
    spec["fit_alignment_notes"] = [
        "Side plates now reach closer to the target lateral width.",
        "Rear clasp lines up with the back spine keel to reduce the rear waist gap.",
        "Buckle and rear wrap redistribute depth instead of making only the front protrude.",
    ]
    spec["silhouette_review_notes"] = [
        "Single body_wrap_arc (arc 120°) wraps the pelvis front+sides.",
        "Rear wrap mirrors the front to close the belt loop without rear gap.",
        "Buckle is the cyan focal point bridging chest-V to thigh stripe.",
    ]
    return spec


def _left_shoulder_spec() -> dict[str, Any]:
    # target_envelope_m: x=0.1904, y=0.1224, z=0.1632
    spec = _base("left_shoulder", "shoulder", "wave_1_arm_seams", side="left")
    ex, ey, ez = (_ENVELOPE["left_shoulder"]["x"], _ENVELOPE["left_shoulder"]["y"],
                  _ENVELOPE["left_shoulder"]["z"])
    panels = [
        _panel("shoulder_pauldron_cap", "body_wrap_arc",
            anchor=(0.0, 0.01, 0.0),
            size=(0.190, 0.122, 0.036),
            bevel_m=0.006, material_zone="base_surface",
            arc_deg=180.0, front_bulge=0.074, segments=16,
            y_taper_top=0.02, y_taper_bottom=0.06,
            comment="Pauldron cap wrap; wider shoulder cup with controlled depth."),
        _panel("shoulder_insertion_lip", "trim_ridge",
            anchor=(-ex * 0.40, ey * 0.05, 0.030),
            size=(0.032, ey * 0.74, 0.036),
            rotation_deg=(0.0, 14.0, 0.0),
            bevel_m=0.003, material_zone="accent",
            comment="Insertion lip extending toward chest line."),
        _panel("shoulder_outer_trim", "trim_ridge",
            anchor=(ex * 0.42, 0.0, 0.0),
            size=(0.018, ey * 0.62, ez * 0.46),
            bevel_m=0.003, material_zone="accent",
            comment="Outer trim ridge defining pauldron edge."),
        _panel("shoulder_rear_scapula_lip", "trim_ridge",
            anchor=(-ex * 0.10, 0.0, -0.056),
            size=(0.100, ey * 0.54, 0.016),
            rotation_deg=(0.0, -18.0, 0.0),
            bevel_m=0.002, material_zone="trim",
            comment="Rear lip tucks shoulder into the back/scapula line."),
        _panel("shoulder_under_socket_shadow", "trim_ridge",
            anchor=(ex * 0.08, -ey * 0.35, -0.018),
            size=(0.100, 0.014, 0.025),
            rotation_deg=(0.0, -8.0, 0.0),
            bevel_m=0.002, material_zone="trim",
            comment="Lower socket shadow keeps the pauldron seated on the deltoid."),
    ]
    spec["silhouette"] = {"panels": panels, "wrap_arc_deg": 170.0}
    spec["emissive_lines"] = [
        _groove((-ex * 0.18, ey * 0.30, ez * 0.45), (ex * 0.32, -ey * 0.18, ez * 0.45),
                width_m=0.006, depth_m=0.002),
    ]
    spec["vrm_attachment_hint"] = {"primary_bone": "leftShoulder",
        "offset_m": [0.035, 0.006, 0.022], "rotation_deg": [0.0, 0.0, -8.0]}
    spec["body_follow_profile"] = {
        "mode": "deltoid_cup_with_chest_and_scapula_lips",
        "depth_axis": "z",
        "anchor_bones": ["leftShoulder", "leftUpperArm", "upperChest"],
        "follow_panels": [
            "shoulder_pauldron_cap", "shoulder_insertion_lip",
            "shoulder_rear_scapula_lip", "shoulder_under_socket_shadow",
        ],
        "target_contact": "cap follows the deltoid while lips bridge to chest/back seams",
    }
    spec["fit_alignment_notes"] = [
        "Shoulder cup is widened to the target lateral envelope.",
        "Rear scapula lip improves continuity into the back module.",
        "Lower socket shadow makes the part read as attached to the arm, not floating.",
    ]
    spec["silhouette_review_notes"] = [
        "body_wrap_arc cap (arc 140°) sits over the deltoid, no flat slab read.",
        "Insertion lip extends inward to bridge into chest_clavicle_trim.",
        "Outer trim adds a bright cobalt edge on profile views.",
    ]
    return spec


def _left_upperarm_spec() -> dict[str, Any]:
    # target_envelope_m: x=0.1088, y=0.2924, z=0.1088
    spec = _base("left_upperarm", "arm", "wave_1_arm_seams", side="left")
    ex, ey, ez = (_ENVELOPE["left_upperarm"]["x"], _ENVELOPE["left_upperarm"]["y"],
                  _ENVELOPE["left_upperarm"]["z"])
    panels = [
        _panel("upperarm_outer_top", "body_wrap_arc",
            anchor=(0.0, ey * 0.22, 0.0),
            size=(0.10, 0.12, 0.020),
            bevel_m=0.004, material_zone="base_surface",
            arc_deg=180.0, front_bulge=0.060, segments=12,
            comment="Top half outer biceps wrap (split shell)."),
        _panel("upperarm_outer_bottom", "body_wrap_arc",
            anchor=(0.0, -ey * 0.22, 0.0),
            size=(0.10, 0.12, 0.020),
            bevel_m=0.004, material_zone="base_surface",
            arc_deg=180.0, front_bulge=0.060, segments=12,
            comment="Bottom half outer biceps wrap (split with elbow gap)."),
        _panel("upperarm_top_lip", "trim_ridge",
            anchor=(0.0, ey * 0.46, 0.0),
            size=(ex * 0.86, 0.014, ez * 0.50),
            bevel_m=0.003, material_zone="accent",
            comment="Top shoulder-socket lip seam."),
        _panel("upperarm_bottom_lip", "trim_ridge",
            anchor=(0.0, -ey * 0.46, 0.0),
            size=(ex * 0.80, 0.014, ez * 0.46),
            bevel_m=0.003, material_zone="accent",
            comment="Bottom elbow-transition lip."),
        _panel("upperarm_side_accent", "trim_ridge",
            anchor=(ex * 0.40, 0.0, 0.0),
            size=(0.012, ey * 0.60, ez * 0.40),
            bevel_m=0.002, material_zone="accent",
            comment="Outer-edge accent stripe down the arm."),
    ]
    spec["silhouette"] = {"panels": panels, "wrap_arc_deg": 180.0}
    spec["emissive_lines"] = [
        _groove((ex * 0.18, ey * 0.4, ez * 0.5), (ex * 0.18, -ey * 0.4, ez * 0.5),
                width_m=0.005, depth_m=0.002),
    ]
    spec["vrm_attachment_hint"] = {"primary_bone": "leftUpperArm",
        "offset_m": [0.0, -0.015, 0.005], "rotation_deg": [0.0, 0.0, 0.0]}
    spec["silhouette_review_notes"] = [
        "Two body_wrap_arc segments (top/bottom) with a deliberate gap preserve elbow bend.",
        "arc_deg=180 wraps the outer half-circumference; rear stays open for animation.",
        "Lips and side accent maintain the directional read at distance.",
    ]
    return spec


def _left_forearm_spec() -> dict[str, Any]:
    # target_envelope_m: x=0.102, y=0.2788, z=0.102
    spec = _base("left_forearm", "arm", "wave_1_arm_seams", side="left")
    ex, ey, ez = (_ENVELOPE["left_forearm"]["x"], _ENVELOPE["left_forearm"]["y"],
                  _ENVELOPE["left_forearm"]["z"])
    panels = [
        _panel("forearm_outer_top", "body_wrap_arc",
            anchor=(0.0, ey * 0.20, 0.0),
            size=(0.102, 0.13, 0.034),
            bevel_m=0.004, material_zone="base_surface",
            arc_deg=180.0, front_bulge=0.052, segments=12,
            y_taper_top=0.02, y_taper_bottom=0.06,
            comment="Top half outer forearm wrap, arc=180 + bulge fills z."),
        _panel("forearm_outer_bottom", "body_wrap_arc",
            anchor=(0.0, -ey * 0.22, 0.0),
            size=(0.094, 0.12, 0.030),
            bevel_m=0.004, material_zone="base_surface",
            arc_deg=180.0, front_bulge=0.048, segments=12,
            y_taper_top=0.04, y_taper_bottom=0.16,
            comment="Bottom half outer forearm wrap, tapered to wrist."),
        _panel("forearm_wrist_lip", "trim_ridge",
            anchor=(0.0, -ey * 0.46, 0.0),
            size=(ex * 0.84, 0.016, ez * 0.50),
            bevel_m=0.003, material_zone="accent",
            comment="Wrist lip seam against hand cuff."),
        _panel("forearm_accent_stripe", "trim_ridge",
            anchor=(ex * 0.34, 0.0, 0.020),
            size=(0.010, ey * 0.58, 0.008),
            bevel_m=0.002, material_zone="accent",
            comment="Outer accent stripe with small emissive groove."),
        _panel("forearm_rear_vent", "trim_ridge",
            anchor=(0.0, 0.0, -0.045),
            size=(ex * 0.46, ey * 0.36, 0.010),
            bevel_m=0.002, material_zone="trim",
            comment="Back-of-arm vent slat dark trim."),
    ]
    spec["silhouette"] = {"panels": panels, "wrap_arc_deg": 170.0}
    spec["emissive_lines"] = [
        _groove((ex * 0.32, ey * 0.4, ez * 0.5), (ex * 0.32, -ey * 0.4, ez * 0.5),
                width_m=0.005, depth_m=0.002),
    ]
    spec["vrm_attachment_hint"] = {"primary_bone": "leftLowerArm",
        "offset_m": [0.0, -0.01, 0.005], "rotation_deg": [0.0, 0.0, 0.0]}
    spec["silhouette_review_notes"] = [
        "Split wrap arcs (top/bottom) tapered toward wrist preserve rotation.",
        "Rear vent slat sells mecha detail without competing with chest emissive.",
        "Wrist lip helps the forearm-to-hand seam read at viewer distance.",
    ]
    return spec


def _left_hand_spec() -> dict[str, Any]:
    # target_envelope_m: x=0.1156, y=0.0816, z=0.136
    spec = _base("left_hand", "hand", "wave_3_head_hands", side="left")
    ex, ey, ez = (_ENVELOPE["left_hand"]["x"], _ENVELOPE["left_hand"]["y"],
                  _ENVELOPE["left_hand"]["z"])
    panels = [
        _panel("hand_knuckle_wrap", "body_wrap_arc",
            anchor=(0.0, 0.0, -0.020),
            size=(0.115, 0.07, 0.030),
            bevel_m=0.004, material_zone="accent",
            arc_deg=170.0, front_bulge=0.060, segments=12,
            comment="Knuckle wrap covering back of hand; arc=170 + bulge."),
        _panel("hand_knuckle_bump", "rounded_box",
            anchor=(0.0, 0.0, 0.050),
            size=(ex * 0.50, ey * 0.50, 0.030),
            bevel_m=0.004, material_zone="base_surface",
            comment="Knuckle bump pushes bbox z to target ~0.13; base_surface for sidecar coverage."),
        _panel("hand_wrist_cuff", "trim_ridge",
            anchor=(0.0, ey * 0.42, 0.0),
            size=(ex * 0.84, 0.018, ez * 0.40),
            bevel_m=0.003, material_zone="trim",
            comment="Wrist cuff dark trim seaming to forearm."),
        _panel("hand_accent_groove", "trim_ridge",
            anchor=(0.0, 0.0, 0.060),
            size=(ex * 0.20, ey * 0.40, 0.008),
            bevel_m=0.002, material_zone="emissive",
            comment="Top emissive line on knuckle bump."),
    ]
    spec["silhouette"] = {"panels": panels, "wrap_arc_deg": 170.0}
    spec["emissive_lines"] = [
        _groove((0.0, ey * 0.32, ez * 0.5), (0.0, -ey * 0.32, ez * 0.5),
                width_m=0.005, depth_m=0.002),
    ]
    spec["vrm_attachment_hint"] = {"primary_bone": "leftHand",
        "offset_m": [0.0, 0.0, 0.01], "rotation_deg": [0.0, 0.0, 0.0]}
    spec["silhouette_review_notes"] = [
        "body_wrap_arc covers back of hand like a hero gauntlet, fingers stay free.",
        "Cuff trim helps the wrist seam read clearly.",
        "Top groove hosts the cyan power-line continuation.",
    ]
    return spec


def _left_thigh_spec() -> dict[str, Any]:
    # target_envelope_m: x=0.136, y=0.3956, z=0.1292
    spec = _base("left_thigh", "leg", "wave_2_lower_body", side="left")
    ex, ey, ez = (_ENVELOPE["left_thigh"]["x"], _ENVELOPE["left_thigh"]["y"],
                  _ENVELOPE["left_thigh"]["z"])
    panels = [
        _panel("thigh_outer_wrap", "body_wrap_arc",
            anchor=(0.0, 0.0, 0.0),
            size=(0.130, 0.34, 0.020),
            bevel_m=0.005, material_zone="base_surface",
            arc_deg=180.0, front_bulge=0.060, segments=14,
            y_taper_top=0.02, y_taper_bottom=0.14,
            comment="Outer thigh wrap (front+sides), arc=180 + bulge fills z."),
        _panel("thigh_inner_wrap", "body_wrap_arc",
            anchor=(0.0, 0.0, 0.0),
            size=(0.115, 0.30, 0.022),
            rotation_deg=(0.0, 180.0, 0.0),
            bevel_m=0.004, material_zone="base_surface",
            arc_deg=130.0, front_bulge=0.018, segments=12,
            y_taper_top=0.04, y_taper_bottom=0.18,
            comment="Inner thigh wrap (rear) leaves a side gap for stride."),
        _panel("thigh_knee_lip", "trim_ridge",
            anchor=(0.0, -ey * 0.46, 0.040),
            size=(ex * 0.80, 0.018, 0.040),
            bevel_m=0.003, material_zone="accent",
            comment="Knee-transition lip with accent groove."),
        _panel("thigh_hip_accent", "trim_ridge",
            anchor=(ex * 0.34, ey * 0.32, 0.020),
            size=(0.022, ey * 0.30, 0.030),
            rotation_deg=(0.0, -22.0, 0.0),
            bevel_m=0.003, material_zone="accent",
            comment="Hip-side accent connecting to waist module."),
        _panel("thigh_side_trim", "trim_ridge",
            anchor=(ex * 0.46, 0.0, 0.0),
            size=(0.012, ey * 0.66, 0.030),
            bevel_m=0.002, material_zone="accent",
            comment="Outer-edge trim ridge running thigh length."),
        _panel("thigh_front_power_cell", "trim_ridge",
            anchor=(0.0, ey * 0.08, ez * 0.44),
            size=(ex * 0.30, ey * 0.12, 0.010),
            bevel_m=0.002, material_zone="emissive",
            comment="Front thigh power cell increases hero detail density while staying inside target depth."),
    ]
    spec["silhouette"] = {"panels": panels, "wrap_arc_deg": 180.0}
    spec["emissive_lines"] = [
        _groove((ex * 0.32, ey * 0.42, ez * 0.5), (ex * 0.32, -ey * 0.4, ez * 0.5),
                width_m=0.006, depth_m=0.002),
    ]
    spec["vrm_attachment_hint"] = {"primary_bone": "leftUpperLeg",
        "offset_m": [0.005, -0.01, 0.005], "rotation_deg": [0.0, 0.0, 0.0]}
    spec["body_follow_profile"] = {
        "mode": "segmented_thigh_shell_with_stride_gap",
        "depth_axis": "z",
        "anchor_bones": ["leftUpperLeg", "hips"],
        "follow_panels": ["thigh_outer_wrap", "thigh_inner_wrap"],
        "target_contact": "front and rear thigh shells leave side stride gaps but carry visible armor density",
    }
    spec["visual_density_profile"] = {
        "issue": "leg modules can read like sparse proxy guards at full-body distance",
        "hero_density_panels": ["thigh_knee_lip", "thigh_hip_accent", "thigh_side_trim", "thigh_front_power_cell"],
        "profile_cues": ["knee lip", "outer stripe", "front power cell"],
    }
    spec["fit_alignment_notes"] = [
        "Thigh front power cell adds a visible focal detail without changing the attachment offset.",
        "Topping slots reserve hip-side fin and knee lip trim anchors for later silhouette upgrades.",
    ]
    spec["silhouette_review_notes"] = [
        "Front wrap + rear wrap with side gap reads as armored thigh, not a tube.",
        "Hip accent links visually into the waist hip-side line.",
        "Side trim stripe ties into shin guard groove below.",
    ]
    return spec


def _left_shin_spec() -> dict[str, Any]:
    # target_envelope_m: x=0.1156, y=0.3956, z=0.1156
    spec = _base("left_shin", "leg", "wave_2_lower_body", side="left")
    ex, ey, ez = (_ENVELOPE["left_shin"]["x"], _ENVELOPE["left_shin"]["y"],
                  _ENVELOPE["left_shin"]["z"])
    panels = [
        _panel("shin_outer_wrap", "body_wrap_arc",
            anchor=(0.0, 0.0, 0.0),
            size=(0.110, 0.34, 0.020),
            bevel_m=0.005, material_zone="base_surface",
            arc_deg=180.0, front_bulge=0.060, segments=14,
            y_taper_top=0.02, y_taper_bottom=0.18,
            comment="Front+side shin wrap, arc=180 + bulge fills z."),
        _panel("shin_inner_wrap", "body_wrap_arc",
            anchor=(0.0, 0.0, 0.0),
            size=(0.095, 0.28, 0.020),
            rotation_deg=(0.0, 180.0, 0.0),
            bevel_m=0.004, material_zone="base_surface",
            arc_deg=120.0, front_bulge=0.014, segments=10,
            y_taper_top=0.04, y_taper_bottom=0.20,
            comment="Rear calf wrap (smaller) leaves ankle-flex gap."),
        _panel("shin_knee_dome", "rounded_box",
            anchor=(0.0, ey * 0.44, 0.030),
            size=(ex * 0.58, ey * 0.16, 0.050),
            bevel_m=0.005, material_zone="accent",
            comment="Knee-cap dome at top of shin module."),
        _panel("shin_ankle_lip", "trim_ridge",
            anchor=(0.0, -ey * 0.46, 0.020),
            size=(ex * 0.78, 0.018, 0.050),
            bevel_m=0.003, material_zone="trim",
            comment="Ankle-transition lip seaming to boot."),
        _panel("shin_center_v", "trim_ridge",
            anchor=(0.0, 0.0, 0.045),
            size=(ex * 0.10, ey * 0.66, 0.012),
            bevel_m=0.002, material_zone="emissive",
            comment="Front center V emissive stripe (mirrors chest V vertically)."),
        _panel("shin_boot_socket_shadow", "trim_ridge",
            anchor=(0.0, -ey * 0.50, -0.006),
            size=(ex * 0.88, 0.014, 0.030),
            bevel_m=0.002, material_zone="trim",
            comment="Dark lower socket visually nests into the boot cuff and reduces foot float."),
    ]
    spec["silhouette"] = {"panels": panels, "wrap_arc_deg": 180.0}
    spec["emissive_lines"] = [
        _groove((0.0, ey * 0.4, ez * 0.5), (0.0, -ey * 0.42, ez * 0.5),
                width_m=0.008, depth_m=0.003),
    ]
    spec["vrm_attachment_hint"] = {"primary_bone": "leftLowerLeg",
        "offset_m": [0.0, -0.015, 0.005], "rotation_deg": [0.0, 0.0, 0.0]}
    spec["body_follow_profile"] = {
        "mode": "shin_guard_with_boot_socket",
        "depth_axis": "z",
        "anchor_bones": ["leftLowerLeg", "leftFoot"],
        "follow_panels": ["shin_outer_wrap", "shin_inner_wrap", "shin_ankle_lip", "shin_boot_socket_shadow"],
        "target_contact": "lower socket visually receives the boot cuff instead of ending as a floating shin plate",
    }
    spec["visual_density_profile"] = {
        "issue": "shin guard needed more lower-leg detail and a stronger boot transition",
        "hero_density_panels": ["shin_knee_dome", "shin_ankle_lip", "shin_center_v", "shin_boot_socket_shadow"],
        "profile_cues": ["knee dome", "ankle lip", "boot socket shadow"],
    }
    spec["fit_alignment_notes"] = [
        "Boot socket shadow creates a source-of-truth seam for Web preview grounding.",
        "Topping slots reserve shin spike and ankle cuff trim anchors for later add-ons.",
    ]
    spec["silhouette_review_notes"] = [
        "Front wrap + rear wrap split mirrors thigh construction.",
        "Knee dome adds a clear visual hinge between thigh and shin.",
        "Center V emissive continues the suit's vertical hero stripe.",
    ]
    return spec


def _left_boot_spec() -> dict[str, Any]:
    # target_envelope_m: x=0.1224, y=0.0884, z=0.2856
    spec = _base("left_boot", "foot", "wave_2_lower_body", side="left")
    ex, ey, ez = (_ENVELOPE["left_boot"]["x"], _ENVELOPE["left_boot"]["y"],
                  _ENVELOPE["left_boot"]["z"])
    panels = [
        _panel("boot_toe_cap", "rounded_box",
            anchor=(0.0, 0.0, 0.10),
            size=(0.115, 0.07, 0.10),
            bevel_m=0.006, material_zone="base_surface",
            comment="Toe cap rounded box at front (z+)."),
        _panel("boot_heel_cap", "rounded_box",
            anchor=(0.0, 0.0, -0.10),
            size=(0.115, 0.07, 0.080),
            bevel_m=0.006, material_zone="base_surface",
            comment="Heel cap rounded box at rear (z-)."),
        _panel("boot_ankle_wrap", "body_wrap_arc",
            anchor=(0.0, 0.020, 0.0),
            size=(0.115, 0.05, 0.040),
            bevel_m=0.004, material_zone="accent",
            arc_deg=300.0, front_bulge=0.0, segments=20,
            comment="Ankle cuff wrap; arc=300 nearly full circumference."),
        _panel("boot_sole_flat", "rounded_box",
            anchor=(0.0, -0.038, 0.0),
            size=(0.115, 0.012, 0.26),
            bevel_m=0.002, material_zone="trim",
            comment="Flat sole plate spans full z envelope; ground contact."),
        _panel("boot_sole_outrigger_left", "trim_ridge",
            anchor=(ex * 0.43, -0.040, 0.018),
            size=(0.014, 0.010, ez * 0.70),
            bevel_m=0.002, material_zone="trim",
            comment="Left sole rail widens the visual footprint for stronger ground contact."),
        _panel("boot_sole_outrigger_right", "trim_ridge",
            anchor=(-ex * 0.43, -0.040, 0.018),
            size=(0.014, 0.010, ez * 0.70),
            bevel_m=0.002, material_zone="trim",
            comment="Right sole rail mirrors the visual footprint cue."),
        _panel("boot_instep_accent", "trim_ridge",
            anchor=(0.0, 0.010, 0.05),
            size=(ex * 0.40, 0.012, ez * 0.50),
            bevel_m=0.002, material_zone="emissive",
            comment="Instep accent strip; cyan glow continues from shin V."),
    ]
    spec["silhouette"] = {"panels": panels, "wrap_arc_deg": 0.0}
    spec["emissive_lines"] = [
        _groove((0.0, ey * 0.18, ez * 0.5), (0.0, ey * 0.18, -ez * 0.05),
                width_m=0.006, depth_m=0.002),
    ]
    spec["vrm_attachment_hint"] = {"primary_bone": "leftFoot",
        "offset_m": [0.0, 0.0, 0.035], "rotation_deg": [0.0, 0.0, 0.0]}
    spec["body_follow_profile"] = {
        "mode": "grounded_boot_with_ankle_cuff",
        "depth_axis": "z",
        "anchor_bones": ["leftFoot", "leftLowerLeg"],
        "follow_panels": ["boot_toe_cap", "boot_heel_cap", "boot_ankle_wrap", "boot_sole_flat"],
        "target_contact": "sole and side rails define contact in source geometry, not Web-only correction",
    }
    spec["ground_contact_profile"] = {
        "sole_panel": "boot_sole_flat",
        "side_rails": ["boot_sole_outrigger_left", "boot_sole_outrigger_right"],
        "local_bottom_y_m": -0.045,
        "stance_note": "Use the sole bottom as the foot contact reference in preview and fit QA.",
    }
    spec["visual_density_profile"] = {
        "issue": "boot silhouette needed more planted footprint and add-on anchors",
        "hero_density_panels": ["boot_ankle_wrap", "boot_sole_flat", "boot_sole_outrigger_left", "boot_sole_outrigger_right", "boot_instep_accent"],
        "profile_cues": ["flat sole", "side rails", "instep glow"],
    }
    spec["fit_alignment_notes"] = [
        "Sole rails widen the visual footprint while keeping the attachment offset inside target.",
        "Topping slots reserve toe fin and heel spur anchors for later boot silhouette upgrades.",
    ]
    spec["silhouette_review_notes"] = [
        "Toe cap + heel cap + ankle wrap + flat sole keeps foot articulated.",
        "Ankle wrap (arc 300°) gives true ground-up boot silhouette.",
        "Sole plate anchors silver above to ground in profile views.",
    ]
    return spec


def _mirror_spec(
    module: str,
    mirror_of: str,
    *,
    primary_bone: str,
    offset_m: tuple[float, float, float] = (0.0, 0.0, 0.0),
    rotation_deg: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> dict[str, Any]:
    spec = _base(module, _category_for(module), _wave_for(module),
                 mirror_of=mirror_of, side="right")
    spec["silhouette"] = {"mirror": True, "source": mirror_of, "axis": "x"}
    spec["emissive_lines"] = []
    spec["vrm_attachment_hint"] = {
        "primary_bone": primary_bone,
        "offset_m": list(offset_m),
        "rotation_deg": list(rotation_deg),
        "derive_from": mirror_of,
    }
    spec["body_follow_profile"] = {
        "mode": "mirror_source_body_follow",
        "derive_from": mirror_of,
        "mirror_axis": "x",
    }
    spec["visual_density_profile"] = {
        "derive_from": mirror_of,
        "mirror_axis": "x",
        "profile_cues": ["mirrors source hero-density panels and silhouette cues"],
    }
    if "boot" in module:
        spec["ground_contact_profile"] = {
            "derive_from": mirror_of,
            "mirror_axis": "x",
            "stance_note": "Mirror uses the source sole bottom as the foot contact reference.",
        }
    spec["fit_alignment_notes"] = [
        f"Mirrors {mirror_of} body-follow geometry and attachment intent across X.",
    ]
    spec["silhouette_review_notes"] = [
        f"Right-side mirror of {mirror_of}; pipeline negates x to derive geometry.",
        "No independent panel data; keeps mirror pair dimension delta within QA tolerance.",
    ]
    return spec


def _category_for(module: str) -> str:
    if "shoulder" in module:
        return "shoulder"
    if "upperarm" in module or "forearm" in module:
        return "arm"
    if "hand" in module:
        return "hand"
    if "thigh" in module or "shin" in module:
        return "leg"
    if "boot" in module:
        return "foot"
    raise KeyError(module)


def _wave_for(module: str) -> str:
    if "shoulder" in module or "upperarm" in module or "forearm" in module:
        return "wave_1_arm_seams"
    if "thigh" in module or "shin" in module or "boot" in module:
        return "wave_2_lower_body"
    if "hand" in module:
        return "wave_3_head_hands"
    raise KeyError(module)


def _build_part_specs() -> dict[str, dict[str, Any]]:
    specs: dict[str, dict[str, Any]] = {}
    specs["helmet"] = _helmet_spec()
    specs["chest"] = _chest_spec()
    specs["back"] = _back_spec()
    specs["waist"] = _waist_spec()
    specs["left_shoulder"] = _left_shoulder_spec()
    specs["right_shoulder"] = _mirror_spec("right_shoulder", "left_shoulder",
                                           primary_bone="rightShoulder",
                                           offset_m=(-0.035, 0.006, 0.022),
                                           rotation_deg=(0.0, 0.0, 8.0))
    specs["left_upperarm"] = _left_upperarm_spec()
    specs["right_upperarm"] = _mirror_spec("right_upperarm", "left_upperarm",
                                           primary_bone="rightUpperArm",
                                           offset_m=(0.0, -0.015, 0.005))
    specs["left_forearm"] = _left_forearm_spec()
    specs["right_forearm"] = _mirror_spec("right_forearm", "left_forearm",
                                          primary_bone="rightLowerArm",
                                          offset_m=(0.0, -0.01, 0.005))
    specs["left_hand"] = _left_hand_spec()
    specs["right_hand"] = _mirror_spec("right_hand", "left_hand",
                                       primary_bone="rightHand",
                                       offset_m=(0.0, 0.0, 0.01))
    specs["left_thigh"] = _left_thigh_spec()
    specs["right_thigh"] = _mirror_spec("right_thigh", "left_thigh",
                                        primary_bone="rightUpperLeg",
                                        offset_m=(-0.005, -0.01, 0.005))
    specs["left_shin"] = _left_shin_spec()
    specs["right_shin"] = _mirror_spec("right_shin", "left_shin",
                                       primary_bone="rightLowerLeg",
                                       offset_m=(0.0, -0.015, 0.005))
    specs["left_boot"] = _left_boot_spec()
    specs["right_boot"] = _mirror_spec("right_boot", "left_boot",
                                       primary_bone="rightFoot",
                                       offset_m=(0.0, 0.0, 0.035))
    return specs


PART_SPECS: dict[str, dict[str, Any]] = _build_part_specs()


__all__ = [
    "MATERIAL_PALETTE",
    "PART_SPECS",
    "SPEC_CONTRACT_VERSION",
]
