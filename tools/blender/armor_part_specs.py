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
    }


def _helmet_spec() -> dict[str, Any]:
    # target_envelope_m: x=0.2856, y=0.34, z=0.2584
    spec = _base("helmet", "head", "wave_3_head_hands")
    ex, ey, ez = _ENVELOPE["helmet"]["x"], _ENVELOPE["helmet"]["y"], _ENVELOPE["helmet"]["z"]
    panels = [
        _panel("helmet_dome", "rounded_box",
            anchor=(0.0, 0.02, 0.0),
            size=(ex * 0.96, ey * 0.94, ez * 0.94),
            bevel_m=0.020, material_zone="base_surface",
            comment="Main dome volume; bevelled cube produces the broad hero head silhouette."),
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
    spec["vrm_attachment_hint"] = {"primary_bone": "Head",
        "offset_m": [0.0, 0.05, 0.0], "rotation_deg": [0.0, 0.0, 0.0]}
    spec["silhouette_review_notes"] = [
        "Bevelled dome cube reaches target depth z (no flat plate read).",
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
            anchor=(0.0, 0.04, 0.0),
            size=(0.62, 0.36, 0.024),
            bevel_m=0.006, material_zone="base_surface",
            arc_deg=85.0, front_bulge=0.028, segments=14,
            y_taper_top=0.05, y_taper_bottom=0.10,
            comment="Main pectoral wrap arc; arc=85 + bulge fills target z=0.163."),
        _panel("chest_abdomen_wrap", "body_wrap_arc",
            anchor=(0.0, -0.16, 0.0),
            size=(0.54, 0.16, 0.022),
            bevel_m=0.005, material_zone="base_surface",
            arc_deg=80.0, front_bulge=0.018, segments=10,
            y_taper_top=0.04, y_taper_bottom=0.18,
            comment="Lower abdomen wrap, slightly tucked at waist seam."),
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
    spec["vrm_attachment_hint"] = {"primary_bone": "UpperChest",
        "offset_m": [0.0, 0.04, 0.04], "rotation_deg": [0.0, 0.0, 0.0]}
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
            size=(0.58, 0.50, 0.030),
            rotation_deg=(0.0, 180.0, 0.0),
            bevel_m=0.006, material_zone="base_surface",
            arc_deg=70.0, front_bulge=0.022, segments=14,
            y_taper_top=0.06, y_taper_bottom=0.10,
            comment="Main back wrap arc; rotation Y=180 puts apex at -Z (rear)."),
        _panel("back_spine_plate", "rounded_box",
            anchor=(0.0, 0.0, -0.060),
            size=(ex * 0.12, ey * 0.46, 0.010),
            bevel_m=0.004, material_zone="accent",
            comment="Central spine plate accent on rear apex; width/height match main back wrap."),
        _panel("back_lumbar_wrap", "body_wrap_arc",
            anchor=(0.0, -ey * 0.34, 0.0),
            size=(0.50, 0.18, 0.030),
            rotation_deg=(0.0, 180.0, 0.0),
            bevel_m=0.004, material_zone="base_surface",
            arc_deg=70.0, front_bulge=0.020, segments=10,
            y_taper_top=0.06, y_taper_bottom=0.18,
            comment="Lumbar wrap; tucks at waist seam."),
        _panel("back_wing_left", "trim_ridge",
            anchor=(ex * 0.30, ey * 0.32, -0.040),
            size=(ex * 0.22, 0.020, 0.022),
            rotation_deg=(0.0, -16.0, 0.0),
            bevel_m=0.003, material_zone="trim",
            comment="Upper-left scapula trim."),
        _panel("back_wing_right", "trim_ridge",
            anchor=(-ex * 0.30, ey * 0.32, -0.040),
            size=(ex * 0.22, 0.020, 0.022),
            rotation_deg=(0.0, 16.0, 0.0),
            bevel_m=0.003, material_zone="trim",
            comment="Upper-right scapula trim."),
    ]
    spec["silhouette"] = {"panels": panels, "wrap_arc_deg": 75.0}
    spec["emissive_lines"] = [
        _groove((0.0, ey * 0.46, -ez * 0.5), (0.0, -ey * 0.46, -ez * 0.5),
                width_m=0.010, depth_m=0.004),
    ]
    spec["vrm_attachment_hint"] = {"primary_bone": "UpperChest",
        "offset_m": [0.0, 0.02, -0.05], "rotation_deg": [0.0, 180.0, 0.0]}
    spec["silhouette_review_notes"] = [
        "body_wrap_arc with Y=180 rotation -> apex at rear, wraps the back cylinder.",
        "Sagitta now reaches z ~ 0.13m; spine accent + scapula trims complete the silhouette.",
        "Lumbar wrap tapers into the waist seam below.",
    ]
    return spec


def _waist_spec() -> dict[str, Any]:
    # target_envelope_m: x=0.4896, y=0.1716, z=0.1904
    spec = _base("waist", "waist", "wave_1_core")
    ex, ey, ez = _ENVELOPE["waist"]["x"], _ENVELOPE["waist"]["y"], _ENVELOPE["waist"]["z"]
    panels = [
        _panel("waist_main_wrap", "body_wrap_arc",
            anchor=(0.0, 0.0, 0.0),
            size=(0.45, 0.16, 0.052),
            bevel_m=0.005, material_zone="base_surface",
            arc_deg=135.0, front_bulge=0.032, segments=18,
            comment="Main hip wrap arc; arc=135 hugs front+sides of pelvis."),
        _panel("waist_buckle", "rounded_box",
            anchor=(0.0, 0.0, 0.080),
            size=(ex * 0.22, ey * 0.78, 0.024),
            bevel_m=0.005, material_zone="accent",
            comment="Front buckle; sits on wrap apex."),
        _panel("waist_buckle_emissive", "rounded_box",
            anchor=(0.0, 0.0, 0.090),
            size=(ex * 0.06, ey * 0.62, 0.012),
            bevel_m=0.002, material_zone="emissive",
            comment="Buckle inner cyan insert (continues chest V)."),
        _panel("waist_belt_back", "body_wrap_arc",
            anchor=(0.0, 0.0, 0.0),
            size=(0.44, 0.13, 0.040),
            rotation_deg=(0.0, 180.0, 0.0),
            bevel_m=0.004, material_zone="base_surface",
            arc_deg=120.0, front_bulge=0.020, segments=12,
            comment="Rear belt wrap; thinner so seated/animation comfort preserved."),
    ]
    spec["silhouette"] = {"panels": panels, "wrap_arc_deg": 135.0}
    spec["emissive_lines"] = [
        _groove((0.0, ey * 0.5, ez * 0.5), (0.0, -ey * 0.5, ez * 0.5),
                width_m=0.012, depth_m=0.004),
    ]
    spec["vrm_attachment_hint"] = {"primary_bone": "Hips",
        "offset_m": [0.0, 0.0, 0.04], "rotation_deg": [0.0, 0.0, 0.0]}
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
            size=(0.18, 0.118, 0.040),
            bevel_m=0.006, material_zone="base_surface",
            arc_deg=180.0, front_bulge=0.080, segments=14,
            y_taper_top=0.02, y_taper_bottom=0.06,
            comment="Pauldron cap wrap; arc=180 + bulge=0.08 caps the deltoid."),
        _panel("shoulder_insertion_lip", "trim_ridge",
            anchor=(-ex * 0.32, ey * 0.05, 0.030),
            size=(0.024, ey * 0.66, 0.040),
            rotation_deg=(0.0, 14.0, 0.0),
            bevel_m=0.003, material_zone="accent",
            comment="Insertion lip extending toward chest line."),
        _panel("shoulder_outer_trim", "trim_ridge",
            anchor=(ex * 0.42, 0.0, 0.0),
            size=(0.018, ey * 0.62, ez * 0.46),
            bevel_m=0.003, material_zone="accent",
            comment="Outer trim ridge defining pauldron edge."),
    ]
    spec["silhouette"] = {"panels": panels, "wrap_arc_deg": 170.0}
    spec["emissive_lines"] = [
        _groove((-ex * 0.18, ey * 0.30, ez * 0.45), (ex * 0.32, -ey * 0.18, ez * 0.45),
                width_m=0.006, depth_m=0.002),
    ]
    spec["vrm_attachment_hint"] = {"primary_bone": "LeftShoulder",
        "offset_m": [0.04, 0.02, 0.0], "rotation_deg": [0.0, 0.0, -8.0]}
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
    spec["vrm_attachment_hint"] = {"primary_bone": "LeftUpperArm",
        "offset_m": [0.0, -0.02, 0.0], "rotation_deg": [0.0, 0.0, 0.0]}
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
    spec["vrm_attachment_hint"] = {"primary_bone": "LeftLowerArm",
        "offset_m": [0.0, -0.02, 0.0], "rotation_deg": [0.0, 0.0, 0.0]}
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
    spec["vrm_attachment_hint"] = {"primary_bone": "LeftHand",
        "offset_m": [0.0, 0.0, 0.02], "rotation_deg": [0.0, 0.0, 0.0]}
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
    ]
    spec["silhouette"] = {"panels": panels, "wrap_arc_deg": 180.0}
    spec["emissive_lines"] = [
        _groove((ex * 0.32, ey * 0.42, ez * 0.5), (ex * 0.32, -ey * 0.4, ez * 0.5),
                width_m=0.006, depth_m=0.002),
    ]
    spec["vrm_attachment_hint"] = {"primary_bone": "LeftUpperLeg",
        "offset_m": [0.02, -0.02, 0.02], "rotation_deg": [0.0, 0.0, 0.0]}
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
    ]
    spec["silhouette"] = {"panels": panels, "wrap_arc_deg": 180.0}
    spec["emissive_lines"] = [
        _groove((0.0, ey * 0.4, ez * 0.5), (0.0, -ey * 0.42, ez * 0.5),
                width_m=0.008, depth_m=0.003),
    ]
    spec["vrm_attachment_hint"] = {"primary_bone": "LeftLowerLeg",
        "offset_m": [0.0, -0.02, 0.02], "rotation_deg": [0.0, 0.0, 0.0]}
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
    spec["vrm_attachment_hint"] = {"primary_bone": "LeftFoot",
        "offset_m": [0.0, 0.02, 0.04], "rotation_deg": [0.0, 0.0, 0.0]}
    spec["silhouette_review_notes"] = [
        "Toe cap + heel cap + ankle wrap + flat sole keeps foot articulated.",
        "Ankle wrap (arc 300°) gives true ground-up boot silhouette.",
        "Sole plate anchors silver above to ground in profile views.",
    ]
    return spec


def _mirror_spec(module: str, mirror_of: str, *, primary_bone: str) -> dict[str, Any]:
    spec = _base(module, _category_for(module), _wave_for(module),
                 mirror_of=mirror_of, side="right")
    spec["silhouette"] = {"mirror": True, "source": mirror_of, "axis": "x"}
    spec["emissive_lines"] = []
    spec["vrm_attachment_hint"] = {
        "primary_bone": primary_bone,
        "offset_m": [0.0, 0.0, 0.0],
        "rotation_deg": [0.0, 0.0, 0.0],
        "derive_from": mirror_of,
    }
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
                                           primary_bone="RightShoulder")
    specs["left_upperarm"] = _left_upperarm_spec()
    specs["right_upperarm"] = _mirror_spec("right_upperarm", "left_upperarm",
                                           primary_bone="RightUpperArm")
    specs["left_forearm"] = _left_forearm_spec()
    specs["right_forearm"] = _mirror_spec("right_forearm", "left_forearm",
                                          primary_bone="RightLowerArm")
    specs["left_hand"] = _left_hand_spec()
    specs["right_hand"] = _mirror_spec("right_hand", "left_hand",
                                       primary_bone="RightHand")
    specs["left_thigh"] = _left_thigh_spec()
    specs["right_thigh"] = _mirror_spec("right_thigh", "left_thigh",
                                        primary_bone="RightUpperLeg")
    specs["left_shin"] = _left_shin_spec()
    specs["right_shin"] = _mirror_spec("right_shin", "left_shin",
                                       primary_bone="RightLowerLeg")
    specs["left_boot"] = _left_boot_spec()
    specs["right_boot"] = _mirror_spec("right_boot", "left_boot",
                                       primary_bone="RightFoot")
    return specs


PART_SPECS: dict[str, dict[str, Any]] = _build_part_specs()


__all__ = [
    "MATERIAL_PALETTE",
    "PART_SPECS",
    "SPEC_CONTRACT_VERSION",
]
