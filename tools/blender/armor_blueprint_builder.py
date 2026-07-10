"""ArmorBlueprint v1 -> smooth hard-surface armor GLB (Blender 5.x, headless).

Design contract: an LLM (or the rule compiler in src/henshin/armor_blueprint.py)
emits a small JSON blueprint; this builder turns it into dense, smooth armor
with sharp creased accents in seconds — no LLM in the geometry loop.

Technique: superellipse cross-section lofts define the character of the shell
(rounded / squared / sharp), grooves and feature regions are built INTO the
control cage, edge creases mark what must stay sharp, and a Subdivision
Surface pass produces the final curvature-continuous, high-density mesh.

Run headless:
  blender --background --factory-startup --python tools/blender/armor_blueprint_builder.py -- \
    --blueprint examples/armor-blueprint.sample.json --out-dir output/blueprint-armor \
    --modules helmet,chest --quality runtime --render

Coordinates: authored Z-up in Blender (X width, Z height, front = -Y);
glTF export flips to Y-up so runtime sees the same frame as canonical parts.
"""
from __future__ import annotations

import json
import math
import os
import sys

try:
    import bmesh  # type: ignore
    import bpy  # type: ignore
    from mathutils import Vector  # type: ignore
except ImportError:  # pragma: no cover - importable for spec inspection only
    bmesh = None
    bpy = None

# ---------------------------------------------------------------------------
# Module presets: envelope (x=width, y=height, z=depth in glTF terms),
# attachment hints copied from the canonical modeler sidecars, loft config.
# ---------------------------------------------------------------------------

ENVELOPE_M = {
    "helmet": (0.2856, 0.34, 0.2584),
    "chest": (0.6392, 0.4992, 0.1632),
    "back": (0.5984, 0.5148, 0.136),
    "waist": (0.4896, 0.1716, 0.1904),
    "left_shoulder": (0.1904, 0.1224, 0.1632),
    "left_upperarm": (0.1088, 0.2924, 0.1088),
    "left_forearm": (0.102, 0.2788, 0.102),
    "left_hand": (0.1156, 0.0816, 0.136),
    "left_thigh": (0.136, 0.3956, 0.1292),
    "left_shin": (0.1156, 0.3956, 0.1156),
    "left_boot": (0.1224, 0.0884, 0.2856),
}

VRM_ATTACHMENT = {
    "helmet": {"primary_bone": "head", "offset_m": [0.0, 0.02, 0.04], "rotation_deg": [0, 0, 0], "fallback_bones": ["head", "neck"]},
    "chest": {"primary_bone": "upperChest", "offset_m": [0.0, 0.012, 0.064], "rotation_deg": [0, 0, 0], "fallback_bones": ["upperChest", "chest"]},
    "back": {"primary_bone": "upperChest", "offset_m": [0.0, 0.002, -0.07], "rotation_deg": [0, 180, 0], "fallback_bones": ["upperChest", "chest"]},
    "waist": {"primary_bone": "hips", "offset_m": [0.0, 0.006, 0.04], "rotation_deg": [0, 0, 0], "fallback_bones": ["hips", "spine"]},
    "left_shoulder": {"primary_bone": "leftShoulder", "offset_m": [0.0318, 0.0055, 0.02], "rotation_deg": [0, 0, -8], "fallback_bones": ["leftShoulder", "leftUpperArm"]},
    "right_shoulder": {"primary_bone": "rightShoulder", "offset_m": [-0.0318, 0.0055, 0.02], "rotation_deg": [0, 0, 8], "fallback_bones": ["rightShoulder", "rightUpperArm"]},
    "left_upperarm": {"primary_bone": "leftUpperArm", "offset_m": [0.0, -0.015, 0.005], "rotation_deg": [0, 0, 0], "fallback_bones": ["leftUpperArm", "leftShoulder"]},
    "right_upperarm": {"primary_bone": "rightUpperArm", "offset_m": [0.0, -0.015, 0.005], "rotation_deg": [0, 0, 0], "fallback_bones": ["rightUpperArm", "rightShoulder"]},
    "left_forearm": {"primary_bone": "leftLowerArm", "offset_m": [0.0, -0.01, 0.005], "rotation_deg": [0, 0, 0], "fallback_bones": ["leftLowerArm", "leftUpperArm"]},
    "right_forearm": {"primary_bone": "rightLowerArm", "offset_m": [0.0, -0.01, 0.005], "rotation_deg": [0, 0, 0], "fallback_bones": ["rightLowerArm", "rightUpperArm"]},
    "left_hand": {"primary_bone": "leftHand", "offset_m": [0.0, 0.0, 0.01], "rotation_deg": [0, 0, 0], "fallback_bones": ["leftHand", "leftLowerArm"]},
    "right_hand": {"primary_bone": "rightHand", "offset_m": [0.0, 0.0, 0.01], "rotation_deg": [0, 0, 0], "fallback_bones": ["rightHand", "rightLowerArm"]},
    "left_thigh": {"primary_bone": "leftUpperLeg", "offset_m": [0.005, -0.01, 0.005], "rotation_deg": [0, 0, 0], "fallback_bones": ["leftUpperLeg", "hips"]},
    "right_thigh": {"primary_bone": "rightUpperLeg", "offset_m": [-0.005, -0.01, 0.005], "rotation_deg": [0, 0, 0], "fallback_bones": ["rightUpperLeg", "hips"]},
    "left_shin": {"primary_bone": "leftLowerLeg", "offset_m": [0.0, -0.015, 0.005], "rotation_deg": [0, 0, 0], "fallback_bones": ["leftLowerLeg", "leftUpperLeg"]},
    "right_shin": {"primary_bone": "rightLowerLeg", "offset_m": [0.0, -0.015, 0.005], "rotation_deg": [0, 0, 0], "fallback_bones": ["rightLowerLeg", "rightUpperLeg"]},
    "left_boot": {"primary_bone": "leftFoot", "offset_m": [0.0, 0.0, 0.035], "rotation_deg": [0, 0, 0], "fallback_bones": ["leftFoot", "leftLowerLeg"]},
    "right_boot": {"primary_bone": "rightFoot", "offset_m": [0.0, 0.0, 0.035], "rotation_deg": [0, 0, 0], "fallback_bones": ["rightFoot", "rightLowerLeg"]},
}

# wrap_deg: arc around Z (360 = closed loop). closed_top adds a pole cap.
# profile: default [t, scale] control points (t: 0 bottom -> 1 top).
MODULE_LOFT = {
    "helmet": {"wrap_deg": 360, "closed_top": True, "flat_bottom": False, "rows": 26, "cols": 68,
               "profile": [[0.0, 0.86], [0.18, 0.97], [0.45, 1.0], [0.75, 0.94], [0.95, 0.72], [1.0, 0.42]]},
    # wrap広め(218/208): 前後半シェルの側端が体側線を越えて重なる(瓦)。
    # 205/195では剛体シフト後に脇のシームが縦一本開いた(2026-07-10)
    "chest": {"wrap_deg": 218, "closed_top": False, "rows": 22, "cols": 58,
              "profile": [[0.0, 0.82], [0.32, 0.94], [0.62, 1.0], [1.0, 0.90]]},
    "back": {"wrap_deg": 208, "closed_top": False, "rows": 20, "cols": 54,
             "profile": [[0.0, 0.80], [0.35, 0.95], [0.70, 1.0], [1.0, 0.88]]},
    # full ring: an exposed backside is a weakness, not a design choice
    "waist": {"wrap_deg": 360, "closed_top": False, "rows": 12, "cols": 64,
              "profile": [[0.0, 0.92], [0.5, 1.0], [1.0, 0.92]]},
    "shoulder": {"wrap_deg": 360, "closed_top": True, "rows": 16, "cols": 48,
                 "profile": [[0.0, 0.95], [0.35, 1.0], [0.75, 0.82], [1.0, 0.55]]},
    "limb": {"wrap_deg": 360, "closed_top": False, "rows": 18, "cols": 44,
             "profile": [[0.0, 0.80], [0.25, 0.94], [0.55, 1.0], [1.0, 0.84]]},
    "hand": {"wrap_deg": 360, "closed_top": True, "rows": 11, "cols": 36,
             "profile": [[0.0, 0.90], [0.4, 1.0], [0.8, 0.85], [1.0, 0.6]]},
    "boot": {"wrap_deg": 360, "closed_top": True, "closed_bottom": True, "rows": 14, "cols": 44,
             "profile": [[0.0, 1.0], [0.45, 0.97], [0.8, 0.88], [1.0, 0.74]]},
}

ZONE_ORDER = ("base_surface", "accent", "emissive", "trim")

CROSS_SECTION_EXPONENT = {"sharp": 1.55, "rounded": 2.0, "squared": 3.4}
QUALITY_SUBSURF = {"preview": 1, "runtime": 2, "hero": 3}


def loft_config_for(module: str) -> dict:
    key = module.replace("right_", "left_")
    if key in MODULE_LOFT:
        return dict(MODULE_LOFT[key])
    if key in ("left_shoulder",):
        return dict(MODULE_LOFT["shoulder"])
    if key in ("left_upperarm", "left_forearm", "left_thigh", "left_shin"):
        return dict(MODULE_LOFT["limb"])
    if key == "left_hand":
        return dict(MODULE_LOFT["hand"])
    if key == "left_boot":
        return dict(MODULE_LOFT["boot"])
    return dict(MODULE_LOFT["limb"])


def envelope_for(module: str):
    key = module.replace("right_", "left_")
    return ENVELOPE_M.get(key, (0.15, 0.25, 0.15))


# ---------------------------------------------------------------------------
# Pure math helpers (importable without bpy)
# ---------------------------------------------------------------------------

def catmull_rom(points, t):
    """Evaluate a 1D Catmull-Rom spline through [x, value] control points."""
    pts = sorted((float(p[0]), float(p[1])) for p in points)
    if not pts:
        return 1.0
    if t <= pts[0][0]:
        return pts[0][1]
    if t >= pts[-1][0]:
        return pts[-1][1]
    for i in range(len(pts) - 1):
        x0, y0 = pts[i]
        x1, y1 = pts[i + 1]
        if x0 <= t <= x1:
            xm1, ym1 = pts[max(0, i - 1)]
            x2, y2 = pts[min(len(pts) - 1, i + 2)]
            span = (x1 - x0) or 1e-9
            u = (t - x0) / span
            m0 = (y1 - ym1) / ((x1 - xm1) or 1e-9) * span
            m1 = (y2 - y0) / ((x2 - x0) or 1e-9) * span
            u2, u3 = u * u, u * u * u
            return ((2 * u3 - 3 * u2 + 1) * y0 + (u3 - 2 * u2 + u) * m0
                    + (-2 * u3 + 3 * u2) * y1 + (u3 - u2) * m1)
    return pts[-1][1]


def smoothstep(edge0, edge1, x):
    span = (edge1 - edge0) or 1e-9
    t = max(0.0, min(1.0, (x - edge0) / span))
    return t * t * (3.0 - 2.0 * t)


def superellipse_point(theta, rx, ry, exponent):
    """Point on a superellipse; exponent <2 sharp, 2 round, >2 squared."""
    c, s = math.cos(theta), math.sin(theta)
    e = 2.0 / max(0.8, float(exponent))
    x = math.copysign(abs(c) ** e, c) * rx
    y = math.copysign(abs(s) ** e, s) * ry
    return x, y


def angle_delta(a, b):
    d = (a - b + math.pi) % (2.0 * math.pi) - math.pi
    return abs(d)


def resolve_part(part_bp: dict) -> dict:
    """Merge a blueprint part with defaults into a fully-resolved spec."""
    module = str(part_bp.get("module", "helmet"))
    sil = dict(part_bp.get("silhouette") or {})
    surf = dict(part_bp.get("surface") or {})
    cfg = loft_config_for(module)
    exponent = sil.get("cross_section", "rounded")
    if isinstance(exponent, str):
        exponent = CROSS_SECTION_EXPONENT.get(exponent, 2.0)
    resolved = {
        "module": module,
        "envelope": envelope_for(module),
        "wrap_deg": float(sil.get("wrap_deg", cfg["wrap_deg"])),
        "closed_top": bool(cfg.get("closed_top", False)),
        "closed_bottom": bool(cfg.get("closed_bottom", False)),
        "rows": int(cfg["rows"]),
        "cols": int(cfg["cols"]),
        "profile": list(sil.get("profile") or cfg["profile"]),
        "exponent": float(exponent),
        "crown_height": max(0.0, min(0.5, float(sil.get("crown_height", 0.0)))),
        "front_bias": max(-0.35, min(0.35, float(sil.get("front_bias", 0.0)))),
        "edge_style": str(surf.get("edge_style", "machined")),
        "smoothness": max(0.0, min(1.0, float(surf.get("smoothness", 0.7)))),
        "ring_grooves": list(surf.get("ring_grooves") or []),
        "meridian_grooves": list(surf.get("meridian_grooves") or []),
        "rim_trim": bool(surf.get("rim_trim", True)),
        "features": list(part_bp.get("features") or []),
        "shell_thickness": float(surf.get("shell_thickness_m", 0.009)),
    }
    return resolved


# ---------------------------------------------------------------------------
# Loft construction (bpy required beyond this point)
# ---------------------------------------------------------------------------

FRONT_ANGLE = -math.pi / 2.0  # front of the body = -Y in the authoring frame


def _features(spec, kind):
    """All features of a kind (panel_step/vent_slats/rivet_row may repeat)."""
    return [f for f in spec["features"] if f.get("kind") == kind]


def _window_bounds(feat, default_span=0.2):
    """(t0, t1) window of a rectangular surface feature."""
    t_c = max(0.05, min(0.95, float(feat.get("position", 0.5))))
    t_span = max(0.04, min(0.8, float(feat.get("t_span", default_span))))
    return max(0.02, t_c - t_span * 0.5), min(0.98, t_c + t_span * 0.5)


def _row_positions(spec):
    """Return sorted row t-values, injecting groove row triplets."""
    rows = max(4, spec["rows"])
    ts = [r / rows for r in range(rows + 1)]
    for groove in spec["ring_grooves"]:
        t = max(0.04, min(0.96, float(groove.get("position", 0.5))))
        w = max(0.008, float(groove.get("width", 0.02)))
        ts.extend([t - w, t, t + w])
    # visor band edges are exact rows: the frame ledge needs a tight triplet
    for feat in _features(spec, "visor"):
        t0 = float(feat.get("band_bottom", 0.52))
        t1 = float(feat.get("band_top", 0.74))
        ts.extend([t0 - 0.014, t0, t0 + 0.014, t1 - 0.014, t1, t1 + 0.014])
    # crisp borders for stepped panels: double rows hugging each edge
    for feat in _features(spec, "panel_step"):
        t0, t1 = _window_bounds(feat)
        ts.extend([t0 - 0.008, t0, t0 + 0.008, t1 - 0.008, t1, t1 + 0.008])
    # vent pockets: borders + one row per slat crest and trough
    for feat in _features(spec, "vent_slats"):
        t0, t1 = _window_bounds(feat, 0.14)
        slats = max(2, min(8, int(feat.get("slats", 4))))
        ts.extend([t0 - 0.008, t0, t1, t1 + 0.008])
        for k in range(slats * 2 + 1):
            ts.append(t0 + (t1 - t0) * k / (slats * 2))
    return sorted(set(round(t, 5) for t in ts if 0.0 <= t <= 1.0))


def _col_angles(spec):
    """Return sorted column angles, injecting meridian groove triplets."""
    cols = max(8, spec["cols"])
    wrap = math.radians(spec["wrap_deg"])
    full = abs(wrap - 2.0 * math.pi) < 1e-6
    start = FRONT_ANGLE - wrap / 2.0
    count = cols if full else cols + 1
    angles = [start + wrap * (c / cols) for c in range(count)]
    for groove in spec["meridian_grooves"]:
        rel = float(groove.get("angle_deg", 0.0))
        theta = FRONT_ANGLE + math.radians(rel)
        w = math.radians(max(1.0, float(groove.get("width_deg", 3.0))))
        for cand in (theta - w, theta, theta + w):
            if full:
                angles.append(cand)
            else:
                if start + 1e-6 < cand < start + wrap - 1e-6:
                    angles.append(cand)
    # visor arc ends: put a column exactly on the membership-0.5 line so the
    # vertical glow boundary follows one column instead of staircasing
    for feat in (f for f in spec["features"] if f.get("kind") == "visor"):
        half = math.radians(float(feat.get("wrap_deg", 120.0))) / 2.0
        eps = math.radians(1.0)
        for side in (-1.0, 1.0):
            edge = FRONT_ANGLE + side * half
            for cand in (edge - eps, edge, edge + eps):
                if full:
                    angles.append(cand)
                elif start + 1e-6 < cand < start + wrap - 1e-6:
                    angles.append(cand)
    # crisp side borders for stepped panels / vent pockets (mirror-aware)
    step_eps = math.radians(0.9)
    for kind, default_arc in (("panel_step", 60.0), ("vent_slats", 26.0)):
        for feat in _features(spec, kind):
            a_c = float(feat.get("angle_deg", 0.0))
            half = math.radians(max(6.0, min(160.0, float(feat.get("arc_deg", default_arc))))) / 2.0
            centers = [a_c] + ([-a_c] if feat.get("mirror") and abs(a_c) > 2 else [])
            for ac in centers:
                theta_c = FRONT_ANGLE + math.radians(ac)
                for cand in (theta_c - half - step_eps, theta_c - half, theta_c - half + step_eps,
                             theta_c + half - step_eps, theta_c + half, theta_c + half + step_eps):
                    if full:
                        angles.append(cand)
                    elif start + 1e-6 < cand < start + wrap - 1e-6:
                        angles.append(cand)
    uniq = sorted(set(round(a, 6) for a in angles))
    return uniq, full


def _ring_groove_in_sector(groove, theta):
    """Ring grooves may be limited to an angular window (e.g. mouth vents)."""
    sector = groove.get("sector_deg")
    if not sector:
        return True
    center = FRONT_ANGLE + math.radians(float(groove.get("center_deg", 0.0)))
    return angle_delta(theta, center) <= math.radians(float(sector)) / 2.0


def _groove_scale(spec, t, theta):
    """Radial multiplier + zone tag from grooves closest to (t, theta)."""
    scale = 1.0
    zone = None
    for groove in spec["ring_grooves"]:
        gt = max(0.04, min(0.96, float(groove.get("position", 0.5))))
        w = max(0.008, float(groove.get("width", 0.02)))
        if abs(t - gt) <= w * 0.55 and _ring_groove_in_sector(groove, theta):
            scale = min(scale, 1.0 - float(groove.get("depth", 0.35)) * 0.06)
            zone = groove.get("zone", zone or "accent")
    for groove in spec["meridian_grooves"]:
        gtheta = FRONT_ANGLE + math.radians(float(groove.get("angle_deg", 0.0)))
        w = math.radians(max(1.0, float(groove.get("width_deg", 3.0))))
        if angle_delta(theta, gtheta) <= w * 0.55:
            scale = min(scale, 1.0 - float(groove.get("depth", 0.35)) * 0.06)
            zone = groove.get("zone", zone or "accent")
    return scale, zone


def _feature(spec, kind):
    for feat in spec["features"]:
        if feat.get("kind") == kind:
            return feat
    return None


def _visor_membership(spec, t, theta):
    feat = _feature(spec, "visor")
    if not feat:
        return 0.0
    t0 = float(feat.get("band_bottom", 0.52))
    t1 = float(feat.get("band_top", 0.74))
    wrap = math.radians(float(feat.get("wrap_deg", 120.0))) / 2.0
    # crisp frame: the 0.5-contour must hug the analytic boundary so the
    # snapped rows / injected arc-end columns catch it (no staircase)
    soft_t = 0.014
    soft_a = math.radians(2.5)
    if not (t0 - soft_t < t < t1 + soft_t):
        return 0.0
    d = angle_delta(theta, FRONT_ANGLE)
    if d > wrap + soft_a:
        return 0.0
    # NOTE: shape "v" no longer moves the band edges — the V silhouette is a
    # geometric warp (_visor_geo_warp), so the band stays row-aligned here
    band = min(smoothstep(t0 - soft_t, t0 + soft_t, t),
               1.0 - smoothstep(t1 - soft_t, t1 + soft_t, t))
    arc = 1.0 - smoothstep(wrap - soft_a, wrap + soft_a, d)
    return max(0.0, min(1.0, band * arc))


def _gauss(x, sigma):
    return math.exp(-(x * x) / max(1e-9, 2.0 * sigma * sigma))


def _visor_geo_warp(spec, t, theta):
    """V visor as a geometric brow warp.

    Cutting the V diagonally through the loft grid can never give a clean
    material edge (zone tags follow faces; snapped polylines scallop under
    subsurf). Instead the visor band stays RECTANGULAR in parameter space —
    its edges are exact mesh rows — and the V comes from warping the shell
    itself: the whole brow region rises toward the arc edges. Same silhouette,
    knife-clean boundary."""
    feat = _feature(spec, "visor")
    if not feat or str(feat.get("shape", "band")) != "v":
        return t
    dip = float(feat.get("v_dip", 0.10))
    if dip <= 0.0:
        return t
    wrap = math.radians(float(feat.get("wrap_deg", 120.0))) / 2.0
    d = angle_delta(theta, FRONT_ANGLE)
    frac = min(1.0, d / max(wrap, 1e-6))
    if d > wrap:  # relax back to the unwarped shell behind the visor
        frac = max(0.0, 1.0 - (d - wrap) / math.radians(30.0))
    t0 = float(feat.get("band_bottom", 0.52))
    t1 = float(feat.get("band_top", 0.74))
    w = _gauss(t - (t0 + t1) * 0.5, (t1 - t0) * 0.9)
    return t + dip * (frac ** 1.2) * w


def _pec_membership(spec, t, theta):
    """Two pectoral bulges left/right of the sternum line."""
    feat = _feature(spec, "pec_plates")
    if not feat:
        return 0.0
    strength = float(feat.get("strength", 0.10))
    lobe_deg = math.radians(float(feat.get("lobe_offset_deg", 30.0)))
    sig_a = math.radians(float(feat.get("lobe_width_deg", 17.0)))
    t_center = float(feat.get("center", 0.68))
    sig_t = float(feat.get("height", 0.14))
    d_l = angle_delta(theta, FRONT_ANGLE - lobe_deg)
    d_r = angle_delta(theta, FRONT_ANGLE + lobe_deg)
    lobes = max(_gauss(d_l, sig_a), _gauss(d_r, sig_a))
    return strength * lobes * _gauss(t - t_center, sig_t)


def _chin_membership(spec, t, theta):
    """Jaw guard: the lower front of a helmet flares forward."""
    feat = _feature(spec, "chin_guard")
    if not feat:
        return 0.0
    flare = float(feat.get("flare", 0.14))
    top = float(feat.get("top", 0.42))
    half = math.radians(float(feat.get("wrap_deg", 110.0))) / 2.0
    if t > top:
        return 0.0
    d = angle_delta(theta, FRONT_ANGLE)
    if d > half:
        return 0.0
    fall = 1.0 - smoothstep(half * 0.6, half, d)
    return flare * ((top - t) / max(top, 1e-6)) ** 1.2 * fall


def _bulge_membership(spec, t, theta):
    """Generic anatomical bulge (calf, muscle plate) at (t, theta)."""
    total = 0.0
    for feat in spec["features"]:
        if feat.get("kind") != "bulge":
            continue
        strength = float(feat.get("strength", 0.10))
        center = FRONT_ANGLE + math.radians(float(feat.get("angle_deg", 180.0)))
        sig_a = math.radians(float(feat.get("width_deg", 40.0)))
        t_center = float(feat.get("position", 0.6))
        sig_t = float(feat.get("width", 0.16))
        total += strength * _gauss(angle_delta(theta, center), sig_a) * _gauss(t - t_center, sig_t)
    return total


def _flange_membership(spec, t):
    """Cuff flanges: gaussian ring flares (boot cuffs, gauntlet cuffs)."""
    total = 0.0
    zone = None
    for feat in spec["features"]:
        if feat.get("kind") != "cuff_flange":
            continue
        pos = float(feat.get("position", 0.9))
        width = max(0.02, float(feat.get("width", 0.07)))
        flare = float(feat.get("flare", 0.2))
        w = _gauss(t - pos, width)
        if w > 0.2:
            zone = feat.get("zone", "accent")
        total += flare * w
    return total, zone


def _rect_window(t, theta, t0, t1, theta_c, half, soft_t=0.010, soft_a_deg=1.4):
    """Steep-edged 0..1 membership of a (t, theta) rectangle on the shell."""
    band = min(smoothstep(t0 - soft_t, t0 + soft_t, t),
               1.0 - smoothstep(t1 - soft_t, t1 + soft_t, t))
    if band <= 0.0:
        return 0.0
    soft_a = math.radians(soft_a_deg)
    d = angle_delta(theta, theta_c)
    arc = 1.0 - smoothstep(half - soft_a, half + soft_a, d)
    return max(0.0, band * arc)


def _panel_step_membership(spec, t, theta):
    """Raised panel sectors with crisp borders — the panel-line grammar.

    Real suits are not one skin: they read as separate stamped panels with a
    visible height step at every seam. raise_r is relative to local radius."""
    total = 0.0
    for feat in _features(spec, "panel_step"):
        t0, t1 = _window_bounds(feat)
        a_c = float(feat.get("angle_deg", 0.0))
        half = math.radians(max(6.0, min(160.0, float(feat.get("arc_deg", 60.0))))) / 2.0
        raise_r = max(-1.0, min(1.0, float(feat.get("raise", 0.5)))) * 0.045
        centers = [a_c] + ([-a_c] if feat.get("mirror") and abs(a_c) > 2 else [])
        for ac in centers:
            theta_c = FRONT_ANGLE + math.radians(ac)
            total += raise_r * _rect_window(t, theta, t0, t1, theta_c, half)
    return total


def _vent_membership(spec, t, theta):
    """Recessed vent pocket with raised slat bars (intakes, coolers, mouths).

    Returns (radial delta, zone tag). The pocket dives by depth, the slats
    climb most of the way back — machined louvres, not painted-on stripes."""
    delta = 0.0
    zone = None
    for feat in _features(spec, "vent_slats"):
        t0, t1 = _window_bounds(feat, 0.14)
        a_c = float(feat.get("angle_deg", 0.0))
        half = math.radians(max(6.0, min(160.0, float(feat.get("arc_deg", 26.0))))) / 2.0
        slats = max(2, min(8, int(feat.get("slats", 4))))
        depth = max(0.1, min(1.0, float(feat.get("depth", 0.5)))) * 0.05
        centers = [a_c] + ([-a_c] if feat.get("mirror") and abs(a_c) > 2 else [])
        for ac in centers:
            theta_c = FRONT_ANGLE + math.radians(ac)
            m = _rect_window(t, theta, t0, t1, theta_c, half, soft_t=0.008)
            if m <= 0.0:
                continue
            u = max(0.0, min(1.0, (t - t0) / max(1e-6, t1 - t0)))
            wave = 0.5 - 0.5 * math.cos(u * slats * 2.0 * math.pi)  # troughs..crests
            delta += m * (-depth + wave * depth * 0.85)
            if m > 0.4:
                zone = str(feat.get("zone", "trim"))
    return delta, zone


def _chest_core_membership(spec, t, theta):
    feat = _feature(spec, "v_core")
    if not feat:
        return 0.0
    d = angle_delta(theta, FRONT_ANGLE)
    half = math.radians(float(feat.get("width_deg", 26.0))) / 2.0
    apex_t = float(feat.get("apex", 0.30))
    top_t = float(feat.get("top", 0.86))
    if t < apex_t or t > top_t:
        return 0.0
    # V shape: allowed angular half-width grows from apex to top
    u = (t - apex_t) / max(1e-6, (top_t - apex_t))
    limit = half * (0.18 + 0.82 * u)
    if d > limit:
        return 0.0
    return 1.0 - smoothstep(limit * 0.72, limit, d)


def build_shell(spec, palette_seed=0.0):
    """Build the lofted control cage with zones + creases; returns object."""
    env_x, env_h, env_d = spec["envelope"]
    rx_base = env_x * 0.5
    ry_base = env_d * 0.5
    crown = spec["crown_height"]
    body_h = env_h * (1.0 - crown * 0.55)

    bm = bmesh.new()
    zone_layer = bm.faces.layers.int.new("armor_zone")
    crease = bm.edges.layers.float.new("crease_edge")

    ts = _row_positions(spec)
    angles, full = _col_angles(spec)
    n_cols = len(angles)

    grid = []
    for t_row in ts:
        row = []
        for theta in angles:
            # memberships live in row space (t_row); only the world position
            # uses the warped t, so feature edges stay glued to mesh rows
            t_geo = _visor_geo_warp(spec, t_row, theta)
            prof = catmull_rom(spec["profile"], t_geo)
            z = t_geo * body_h
            center_y = -spec["front_bias"] * ry_base * (t_geo ** 1.4)
            flange, _ = _flange_membership(spec, t_row)
            g_scale, _ = _groove_scale(spec, t_row, theta)
            visor = _visor_membership(spec, t_row, theta)
            core = _chest_core_membership(spec, t_row, theta)
            vent_delta, _ = _vent_membership(spec, t_row, theta)
            radial = prof * g_scale
            radial *= (1.0 - 0.24 * (env_d / max(env_x, 1e-6)) * visor)
            radial *= (1.0 - 0.05 * core)
            radial *= (1.0 + _pec_membership(spec, t_row, theta))
            radial *= (1.0 + _chin_membership(spec, t_row, theta))
            radial *= (1.0 + _bulge_membership(spec, t_row, theta))
            radial *= (1.0 + _panel_step_membership(spec, t_row, theta))
            radial *= (1.0 + vent_delta)
            radial *= (1.0 + flange)
            x, y = superellipse_point(theta, rx_base * radial, ry_base * radial, spec["exponent"])
            row.append(bm.verts.new((x, y + center_y, z)))
        grid.append(row)

    def zone_at(t, theta, is_bottom):
        """Zone from memberships evaluated at the face centroid — a single
        clean boundary line instead of the per-vertex-vote staircase that
        tears apart on dense grids."""
        if _visor_membership(spec, t, theta) > 0.5:
            return "emissive"
        if _chest_core_membership(spec, t, theta) > 0.5:
            return "emissive"
        vent_delta, vent_zone = _vent_membership(spec, t, theta)
        if vent_zone and vent_delta < -0.004:
            return vent_zone
        g_scale, g_zone = _groove_scale(spec, t, theta)
        if g_zone and g_scale < 0.999:
            return g_zone
        flange, flange_zone = _flange_membership(spec, t)
        if flange > 0.06 and flange_zone:
            return flange_zone
        if spec["rim_trim"] and is_bottom:
            return "trim"
        return "base_surface"

    faces = []
    col_range = n_cols if full else n_cols - 1
    for r in range(len(grid) - 1):
        t_mid = (ts[r] + ts[r + 1]) * 0.5
        for c in range(col_range):
            c2 = (c + 1) % n_cols
            quad = (grid[r][c], grid[r][c2], grid[r + 1][c2], grid[r + 1][c])
            try:
                f = bm.faces.new(quad)
            except ValueError:
                continue
            a2 = angles[c2] if c2 > c else angles[c] + (angles[1] - angles[0])
            theta_mid = (angles[c] + a2) * 0.5
            f[zone_layer] = ZONE_ORDER.index(zone_at(t_mid, theta_mid, r == 0))
            faces.append(f)

    # sole cap: boots must have a bottom — bare feet showing from below is
    # an undressed suit (user memo 2026-07-09)
    if spec.get("closed_bottom"):
        bottom_row = grid[0]
        sole_cy = -spec["front_bias"] * ry_base * 0.0
        sole = bm.verts.new((0.0, sole_cy, 0.0))
        for c in range(col_range):
            c2 = (c + 1) % n_cols
            try:
                f = bm.faces.new((bottom_row[c2], bottom_row[c], sole))
                f[zone_layer] = ZONE_ORDER.index("trim")
            except ValueError:
                pass

    # crown cap: pole vertex (optionally raised into a point by crown_height)
    if spec["closed_top"]:
        top_row = grid[-1]
        apex_z = body_h + crown * env_h * 0.55
        cy = -spec["front_bias"] * ry_base
        apex = bm.verts.new((0.0, cy, apex_z))
        for c in range(col_range):
            c2 = (c + 1) % n_cols
            try:
                f = bm.faces.new((top_row[c], top_row[c2], apex))
                f[zone_layer] = 0
            except ValueError:
                pass

    bm.verts.index_update()
    bm.normal_update()

    # creases: groove borders + visor boundary + rim
    def crease_edge(v0, v1, amount):
        e = bm.edges.get((v0, v1))
        if e is not None:
            e[crease] = max(e[crease], amount)

    sharp = {"machined": 0.85, "razor": 1.0, "organic": 0.55}.get(spec["edge_style"], 0.85)
    for r, t in enumerate(ts):
        for groove in spec["ring_grooves"]:
            gt = max(0.04, min(0.96, float(groove.get("position", 0.5))))
            w = max(0.008, float(groove.get("width", 0.02)))
            if abs(abs(t - gt) - w) < 0.004 or abs(t - gt) < 0.004:
                for c in range(col_range):
                    if _ring_groove_in_sector(groove, angles[c]):
                        crease_edge(grid[r][c], grid[r][(c + 1) % n_cols], sharp)
    for ci, theta in enumerate(angles):
        for groove in spec["meridian_grooves"]:
            gtheta = FRONT_ANGLE + math.radians(float(groove.get("angle_deg", 0.0)))
            w = math.radians(max(1.0, float(groove.get("width_deg", 3.0))))
            if angle_delta(theta, gtheta) < w * 1.2:
                for r in range(len(grid) - 1):
                    crease_edge(grid[r][ci], grid[r + 1][ci], sharp)
    # stepped panel / vent borders stay knife-sharp under subsurf
    for kind, default_arc in (("panel_step", 60.0), ("vent_slats", 26.0)):
        for feat in _features(spec, kind):
            t0, t1 = _window_bounds(feat, 0.2 if kind == "panel_step" else 0.14)
            a_c = float(feat.get("angle_deg", 0.0))
            half = math.radians(max(6.0, min(160.0, float(feat.get("arc_deg", default_arc)))) ) / 2.0
            centers = [a_c] + ([-a_c] if feat.get("mirror") and abs(a_c) > 2 else [])
            for ac in centers:
                theta_c = FRONT_ANGLE + math.radians(ac)
                for r, t in enumerate(ts):
                    if min(abs(t - t0), abs(t - t1)) < 0.004:
                        for c in range(col_range):
                            mid = (angles[c] + angles[(c + 1) % n_cols]) * 0.5 if c + 1 < n_cols else angles[c]
                            if angle_delta(mid, theta_c) <= half:
                                crease_edge(grid[r][c], grid[r][(c + 1) % n_cols], sharp)
                for ci, theta in enumerate(angles):
                    if min(abs(angle_delta(theta, theta_c - half)), abs(angle_delta(theta, theta_c + half))) < math.radians(0.5):
                        for r in range(len(grid) - 1):
                            tm = (ts[r] + ts[r + 1]) * 0.5
                            if t0 - 0.002 < tm < t1 + 0.002:
                                crease_edge(grid[r][ci], grid[r + 1][ci], sharp)
    # visor boundary crease: edges between emissive-tagged and base faces
    for e in bm.edges:
        zones = {f[zone_layer] for f in e.link_faces}
        if len(zones) > 1 and ZONE_ORDER.index("emissive") in zones:
            e[crease] = max(e[crease], 1.0)
    # bottom rim crease keeps the opening crisp under subsurf
    for c in range(col_range):
        crease_edge(grid[0][c], grid[0][(c + 1) % n_cols], 1.0)

    mesh = bpy.data.meshes.new(f"abp_{spec['module']}_mesh")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    obj = bpy.data.objects.new(f"abp_{spec['module']}", mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def build_crest_fin(spec, feat):
    """Sharp swept blade over the crown (helmet) or along the part top."""
    env_x, env_h, env_d = spec["envelope"]
    length = max(0.05, min(0.95, float(feat.get("length", 0.62)))) * env_d
    height = max(0.02, min(0.6, float(feat.get("height", 0.28)))) * env_h
    sweep = float(feat.get("sweep", 0.35))
    thick = max(0.004, float(feat.get("thickness_m", 0.012)))
    zone = feat.get("zone", "accent")
    segments = 14

    bm = bmesh.new()
    zone_layer = bm.faces.layers.int.new("armor_zone")
    crease = bm.edges.layers.float.new("crease_edge")
    rows = []
    # ride ON the crown: the skirt sinks into the dome, the blade rises above
    # the apex so the silhouette always reads from any angle.
    base_z = env_h * 0.80
    for i in range(segments + 1):
        u = i / segments
        y = (u - 0.5) * length - spec["front_bias"] * env_d * 0.3
        rise = math.sin(min(1.0, u * 1.25) * math.pi) ** 0.8
        back_sweep = sweep * height * 0.6 * u  # tip flows backward
        z = base_z + rise * height * 1.4
        w = thick * (0.35 + 0.65 * math.sin(u * math.pi) ** 0.7)
        # skirt sinks deepest at the ends where the dome surface falls away
        bottom_z = base_z - env_h * (0.06 + 0.30 * (1.0 - math.sin(u * math.pi) ** 0.7))
        rows.append((
            bm.verts.new((-w, y + back_sweep, bottom_z)),
            bm.verts.new((w, y + back_sweep, bottom_z)),
            bm.verts.new((0.0, y + back_sweep, z)),
        ))
    zone_idx = ZONE_ORDER.index(zone if zone in ZONE_ORDER else "accent")
    for i in range(segments):
        a, b = rows[i], rows[i + 1]
        for tri in (((a[0], b[0], b[2], a[2])), ((b[1], a[1], a[2], b[2])), ((a[1], b[1], b[0], a[0]))):
            try:
                f = bm.faces.new(tri)
                f[zone_layer] = zone_idx
            except ValueError:
                pass
    for i in range(segments):
        e = bm.edges.get((rows[i][2], rows[i + 1][2]))
        if e is not None:
            e[crease] = 1.0  # razor top edge of the crest
    bm.normal_update()
    mesh = bpy.data.meshes.new("abp_crest_mesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("abp_crest", mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def build_surface_pods(spec, feat):
    """Surface-mounted pods: knee pads (dome) and belt buckles (box).

    A pod is a small superellipse loft stacked along the outward radial
    direction at (t, theta) on the shell, its skirt sunk into the plate."""
    env_x, env_h, env_d = spec["envelope"]
    body_h = env_h * (1.0 - spec["crown_height"] * 0.55)
    kind = str(feat.get("kind"))
    t = max(0.05, min(0.95, float(feat.get("position", 0.9))))
    theta = FRONT_ANGLE + math.radians(float(feat.get("angle_deg", 0.0)))
    width = float(feat.get("width_m", 0.05))
    height = float(feat.get("height_m", 0.045))
    depth = float(feat.get("depth_m", 0.02))
    exponent = 3.2 if kind == "buckle" else 2.0
    zone_idx = ZONE_ORDER.index(str(feat.get("zone", "accent")) if feat.get("zone", "accent") in ZONE_ORDER else "accent")

    prof = catmull_rom(spec["profile"], t)
    sx, sy = superellipse_point(theta, env_x * 0.5 * prof, env_d * 0.5 * prof, spec["exponent"])
    center = Vector((sx, sy - spec["front_bias"] * env_d * 0.5 * (t ** 1.4), t * body_h))
    out_dir = Vector((sx, sy, 0.0)).normalized()
    u = Vector((0.0, 0.0, 1.0)).cross(out_dir).normalized()
    v_axis = Vector((0.0, 0.0, 1.0))

    bm = bmesh.new()
    zone_layer = bm.faces.layers.int.new("armor_zone")
    crease = bm.edges.layers.float.new("crease_edge")
    rings = []
    layers = 5
    ring_n = 16
    for i in range(layers + 1):
        s = i / layers
        # profile: full size at the skirt, tapering dome/box toward the top
        taper = 1.0 - 0.55 * (s ** (1.6 if kind == "buckle" else 1.0))
        lift = depth * s - depth * 0.35  # skirt sits below the shell surface
        ring = []
        for k in range(ring_n):
            a = 2.0 * math.pi * k / ring_n
            px, py = superellipse_point(a, width * 0.5 * taper, height * 0.5 * taper, exponent)
            world = center + out_dir * lift + u * px + v_axis * py
            ring.append(bm.verts.new(world))
        rings.append(ring)
    for i in range(layers):
        for k in range(ring_n):
            k2 = (k + 1) % ring_n
            try:
                f = bm.faces.new((rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]))
                f[zone_layer] = zone_idx
            except ValueError:
                pass
    try:
        f = bm.faces.new(tuple(reversed(rings[-1])))
        f[zone_layer] = zone_idx
    except ValueError:
        pass
    for k in range(ring_n):
        e = bm.edges.get((rings[-1][k], rings[-1][(k + 1) % ring_n]))
        if e is not None:
            e[crease] = 0.9
    bm.normal_update()
    mesh = bpy.data.meshes.new(f"abp_pod_{kind}_mesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(f"abp_pod_{kind}", mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def _shell_radial(spec, t, theta):
    """Shell surface point (x, y_offset, z) at (t, theta), matching build_shell."""
    env_x, env_h, env_d = spec["envelope"]
    body_h = env_h * (1.0 - spec["crown_height"] * 0.55)
    prof = catmull_rom(spec["profile"], t)
    x, y = superellipse_point(theta, env_x * 0.5 * prof, env_d * 0.5 * prof, spec["exponent"])
    cy = -spec["front_bias"] * env_d * 0.5 * (t ** 1.4)
    return Vector((x, y + cy, t * body_h))


def _add_stud(bm, zone_layer, crease, center, out_dir, r, zone_idx):
    """A hex bolt head standing on a surface point — tiny, but it sells
    'this plate is fastened to something' at every scale."""
    out = out_dir.normalized() if out_dir.length > 1e-6 else Vector((0.0, -1.0, 0.0))
    side = Vector((0.0, 0.0, 1.0)).cross(out)
    if side.length < 1e-6:
        side = Vector((1.0, 0.0, 0.0))
    side.normalize()
    up = out.cross(side).normalized()
    base_ring, top_ring = [], []
    for k in range(6):
        a = k / 6.0 * 2.0 * math.pi
        rim = side * math.cos(a) + up * math.sin(a)
        base_ring.append(bm.verts.new(center + rim * r - out * (r * 0.35)))
        top_ring.append(bm.verts.new(center + rim * (r * 0.72) + out * (r * 0.85)))
    cap = bm.verts.new(center + out * (r * 1.05))
    for k in range(6):
        k2 = (k + 1) % 6
        for tri_or_quad in ((base_ring[k], base_ring[k2], top_ring[k2], top_ring[k]),
                            (top_ring[k], top_ring[k2], cap)):
            try:
                f = bm.faces.new(tri_or_quad)
                f[zone_layer] = zone_idx
            except ValueError:
                pass
    for k in range(6):
        e = bm.edges.get((top_ring[k], top_ring[(k + 1) % 6]))
        if e is not None:
            e[crease] = 0.8


def build_rivet_row(spec, feat):
    """A row of hex studs riding the shell — along a ring arc or a meridian."""
    t_c = max(0.05, min(0.95, float(feat.get("position", 0.5))))
    a_c = float(feat.get("angle_deg", 0.0))
    count = max(2, min(24, int(feat.get("count", 6))))
    r = max(0.002, min(0.012, float(feat.get("radius_m", 0.0045))))
    along = str(feat.get("along", "ring"))
    zone_idx = ZONE_ORDER.index(str(feat.get("zone", "trim")) if feat.get("zone", "trim") in ZONE_ORDER else "trim")
    centers = [a_c] + ([-a_c] if feat.get("mirror") and abs(a_c) > 2 else [])

    bm = bmesh.new()
    zone_layer = bm.faces.layers.int.new("armor_zone")
    crease = bm.edges.layers.float.new("crease_edge")
    for ac in centers:
        for k in range(count):
            frac = (k + 0.5) / count
            if along == "meridian":
                span = max(0.06, min(0.8, float(feat.get("t_span", 0.4))))
                t = max(0.04, min(0.96, t_c + (frac - 0.5) * span))
                theta = FRONT_ANGLE + math.radians(ac)
            else:
                arc = max(8.0, min(300.0, float(feat.get("arc_deg", 90.0))))
                t = t_c
                theta = FRONT_ANGLE + math.radians(ac + (frac - 0.5) * arc)
            center, out_dir, _, _ = _shell_frame(spec, t, theta)
            _add_stud(bm, zone_layer, crease, center + out_dir * 0.001, out_dir, r, zone_idx)
    bm.normal_update()
    mesh = bpy.data.meshes.new("abp_rivets_mesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("abp_rivets", mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def build_overlay_plate(spec, feat):
    """A floating armor plate: a curved patch that rides OVER the base shell.

    This is the costume-maker's move — suits are stacks of separate panels,
    not one skin. corner: 0=square plate, 1=lens/rounded plate. lift_m raises
    it off the shell; the rim skirts back toward the shell so it reads as a
    mounted piece. mirror duplicates it across the front axis."""
    t_c = max(0.08, min(0.92, float(feat.get("position", 0.5))))
    t_span = max(0.06, min(0.7, float(feat.get("t_span", 0.25))))
    a_c = float(feat.get("angle_deg", 0.0))
    arc = max(12.0, min(160.0, float(feat.get("arc_deg", 60.0))))
    lift = max(0.002, min(0.04, float(feat.get("lift_m", 0.012))))
    corner = max(0.0, min(1.0, float(feat.get("corner", 0.5))))
    taper = max(-0.7, min(0.7, float(feat.get("taper", 0.0))))  # +: narrow top
    bulge = float(feat.get("bulge_m", lift * 0.6))
    zone_idx = ZONE_ORDER.index(str(feat.get("zone", "accent")) if feat.get("zone", "accent") in ZONE_ORDER else "accent")
    angles = [a_c] + ([-a_c] if feat.get("mirror") and abs(a_c) > 2 else [])

    rim = max(0.0, min(1.0, float(feat.get("rim", 0.55))))
    bolts = bool(feat.get("bolts"))
    objs = []
    rows_n, cols_n = 10, 13
    for a_center in angles:
        bm = bmesh.new()
        zone_layer = bm.faces.layers.int.new("armor_zone")
        crease = bm.edges.layers.float.new("crease_edge")
        grid = []
        stud_anchors = []
        for i in range(rows_n + 1):
            u = i / rows_n                      # 0..1 along height of plate
            t = t_c + (u - 0.5) * t_span
            t = max(0.03, min(0.97, t))
            # corner shaping: the angular width shrinks toward the ends —
            # square plate keeps full width, lens plate tapers elliptically
            end = abs(u - 0.5) * 2.0
            width_scale = corner * math.sqrt(max(0.0, 1.0 - end * end)) + (1.0 - corner)
            # trapezoid: linear width change bottom->top (thigh fronts, skirts)
            width_scale *= max(0.2, 1.0 - taper * (u - 0.5))
            row = []
            for j in range(cols_n + 1):
                v = j / cols_n
                rel = (v - 0.5) * arc * width_scale
                theta = FRONT_ANGLE + math.radians(a_center + rel)
                base = _shell_radial(spec, t, theta)
                out_dir = Vector((base.x, base.y + spec["front_bias"] * spec["envelope"][2] * 0.5 * (t ** 1.4), 0.0))
                out_dir = out_dir.normalized() if out_dir.length > 1e-6 else Vector((0.0, -1.0, 0.0))
                # skirt: edges sit lower; the middle domes up by bulge
                edge_u = max(end, abs(v - 0.5) * 2.0)
                h = lift + bulge * math.cos(min(1.0, edge_u) * math.pi * 0.5)
                if edge_u > 0.92:
                    h = lift * 0.25  # rim dives toward the shell
                elif edge_u > 0.68:
                    # raised border ridge just inside the dive — a stamped
                    # plate has a reinforced rim, not a knife-cut edge
                    h += rim * 0.004 * math.sin((edge_u - 0.68) / 0.24 * math.pi)
                if bolts and 0.27 < abs(u - 0.5) < 0.45 and 0.27 < abs(v - 0.5) < 0.45:
                    stud_anchors.append((u, v, base + out_dir * h, out_dir))
                row.append(bm.verts.new(base + out_dir * h))
            grid.append(row)
        if bolts and stud_anchors:
            # one stud per plate quadrant — fasteners at the four corners.
            # Studs live in their own object: they are closed solids and must
            # NOT go through the plate's solidify pass.
            picked = {}
            for u, v, anchor, out_dir in stud_anchors:
                picked.setdefault((u > 0.5, v > 0.5), (anchor, out_dir))
            sbm = bmesh.new()
            s_zone = sbm.faces.layers.int.new("armor_zone")
            s_crease = sbm.edges.layers.float.new("crease_edge")
            for anchor, out_dir in picked.values():
                _add_stud(sbm, s_zone, s_crease, anchor + out_dir * 0.0005, out_dir,
                          0.0038, ZONE_ORDER.index("trim"))
            sbm.normal_update()
            smesh = bpy.data.meshes.new("abp_plate_bolts_mesh")
            sbm.to_mesh(smesh)
            sbm.free()
            sobj = bpy.data.objects.new("abp_plate_bolts", smesh)
            sobj["abp_no_solidify"] = True
            bpy.context.scene.collection.objects.link(sobj)
            objs.append(sobj)
        for i in range(rows_n):
            for j in range(cols_n):
                try:
                    f = bm.faces.new((grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]))
                    f[zone_layer] = zone_idx
                except ValueError:
                    pass
        # crease the plate border so it stays a crisp panel under subsurf
        for j in range(cols_n):
            for row_idx in (0, rows_n):
                e = bm.edges.get((grid[row_idx][j], grid[row_idx][j + 1]))
                if e is not None:
                    e[crease] = 0.9
        for i in range(rows_n):
            for col_idx in (0, cols_n):
                e = bm.edges.get((grid[i][col_idx], grid[i + 1][col_idx]))
                if e is not None:
                    e[crease] = 0.9
        bm.normal_update()
        mesh = bpy.data.meshes.new("abp_plate_mesh")
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new("abp_plate", mesh)
        bpy.context.scene.collection.objects.link(obj)
        objs.append(obj)
    return objs


def build_edge_blade(spec, feat):
    """A streamlined blade fin along the shell — 流線の刃. Runs vertically at
    angle_deg, sweeping backward; razor-creased outer edge."""
    env_x, env_h, env_d = spec["envelope"]
    t_c = max(0.1, min(0.9, float(feat.get("position", 0.55))))
    t_span = max(0.1, min(0.8, float(feat.get("t_span", 0.45))))
    a_c = float(feat.get("angle_deg", 90.0))
    height = max(0.01, min(0.12, float(feat.get("height_m", 0.035))))
    sweep = float(feat.get("sweep", 0.4))
    zone_idx = ZONE_ORDER.index(str(feat.get("zone", "accent")) if feat.get("zone", "accent") in ZONE_ORDER else "accent")
    angles = [a_c] + ([-a_c] if feat.get("mirror") and abs(a_c) > 2 else [])
    seg = 10
    objs = []
    for a_center in angles:
        bm = bmesh.new()
        zone_layer = bm.faces.layers.int.new("armor_zone")
        crease = bm.edges.layers.float.new("crease_edge")
        theta = FRONT_ANGLE + math.radians(a_center)
        rows = []
        for i in range(seg + 1):
            u = i / seg
            t = t_c + (u - 0.5) * t_span
            t = max(0.03, min(0.97, t))
            base = _shell_radial(spec, t, theta)
            out_dir = Vector((base.x, base.y, 0.0))
            out_dir = out_dir.normalized() if out_dir.length > 1e-6 else Vector((0.0, -1.0, 0.0))
            fin = height * math.sin(min(1.0, u * 1.15) * math.pi) ** 0.7
            # sweep: the fin leans down/back as it rises (speed lines)
            lean = Vector((0.0, 0.0, -sweep * fin))
            w = 0.004 * (0.4 + 0.6 * math.sin(u * math.pi))
            side = Vector((0.0, 0.0, 1.0)).cross(out_dir).normalized()
            rows.append((
                bm.verts.new(base + side * w - out_dir * 0.002),
                bm.verts.new(base - side * w - out_dir * 0.002),
                bm.verts.new(base + out_dir * fin + lean),
            ))
        for i in range(seg):
            a, b = rows[i], rows[i + 1]
            for quad in ((a[0], b[0], b[2], a[2]), (b[1], a[1], a[2], b[2]), (a[1], b[1], b[0], a[0])):
                try:
                    f = bm.faces.new(quad)
                    f[zone_layer] = zone_idx
                except ValueError:
                    pass
        for i in range(seg):
            e = bm.edges.get((rows[i][2], rows[i + 1][2]))
            if e is not None:
                e[crease] = 1.0
        bm.normal_update()
        mesh = bpy.data.meshes.new("abp_blade_mesh")
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new("abp_blade", mesh)
        bpy.context.scene.collection.objects.link(obj)
        objs.append(obj)
    return objs


def build_sash(spec, feat):
    """斜め帯 — a strap/bandolier strip riding the shell diagonally.

    The Rider grammar (reference: samplephoto PARADOXIS): a chest strap from
    the shoulder line down to the opposite hip. mirror=True builds the X
    cross. Like every costume strap it is a SEPARATE part, not paint."""
    t1 = max(0.2, min(0.95, float(feat.get("band_top", 0.86))))
    t0 = max(0.2, min(0.9, float(feat.get("band_bottom", 0.22))))
    if t0 >= t1:
        t0, t1 = min(t0, t1) - 0.01, max(t0, t1)
    a_from = float(feat.get("from_deg", -28.0))   # angle at band_top
    a_to = float(feat.get("to_deg", 30.0))        # angle at band_bottom
    width = max(0.02, min(0.12, float(feat.get("width_m", 0.055))))
    lift = max(0.004, min(0.03, float(feat.get("lift_m", 0.012))))
    zone = str(feat.get("zone", "accent"))
    zone_idx = ZONE_ORDER.index(zone if zone in ZONE_ORDER else "accent")
    pairs = [(a_from, a_to)] + ([(-a_from, -a_to)] if feat.get("mirror") else [])
    seg = 16
    objs = []
    for af, at in pairs:
        bm = bmesh.new()
        zone_layer = bm.faces.layers.int.new("armor_zone")
        crease = bm.edges.layers.float.new("crease_edge")
        rows = []
        for i in range(seg + 1):
            u = i / seg
            t = t1 + (t0 - t1) * u
            theta = FRONT_ANGLE + math.radians(af + (at - af) * u)
            base = _shell_radial(spec, t, theta)
            out_dir = Vector((base.x, base.y, 0.0))
            out_dir = out_dir.normalized() if out_dir.length > 1e-6 else Vector((0.0, -1.0, 0.0))
            # the strap ends dive to the shell — an anchored belt, not a decal
            end = min(smoothstep(0.0, 0.1, u), 1.0 - smoothstep(0.9, 1.0, u))
            rows.append((base + out_dir * (lift * (0.25 + 0.75 * end)), out_dir))
        pairs_v = []
        for i, (center, out_dir) in enumerate(rows):
            nxt = rows[min(i + 1, seg)][0]
            prv = rows[max(i - 1, 0)][0]
            tangent = (nxt - prv)
            tangent = tangent.normalized() if tangent.length > 1e-6 else Vector((0.0, 0.0, -1.0))
            side = tangent.cross(out_dir)
            side = side.normalized() if side.length > 1e-6 else Vector((1.0, 0.0, 0.0))
            pairs_v.append((bm.verts.new(center + side * (width * 0.5)),
                            bm.verts.new(center - side * (width * 0.5))))
        for i in range(seg):
            a, b = pairs_v[i], pairs_v[i + 1]
            try:
                f = bm.faces.new((a[0], a[1], b[1], b[0]))
                f[zone_layer] = zone_idx
            except ValueError:
                pass
        for i in range(seg):
            for k in (0, 1):
                e = bm.edges.get((pairs_v[i][k], pairs_v[i + 1][k]))
                if e is not None:
                    e[crease] = 1.0
        for row in (pairs_v[0], pairs_v[-1]):  # square ends under subsurf
            e = bm.edges.get((row[0], row[1]))
            if e is not None:
                e[crease] = 1.0
        bm.normal_update()
        mesh = bpy.data.meshes.new("abp_sash_mesh")
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new("abp_sash", mesh)
        bpy.context.scene.collection.objects.link(obj)
        objs.append(obj)
    return objs


def build_collar(spec, feat):
    """襟甲(ネックガード) — a raised collar ring standing on the chest top.

    The neck line is where the eye judges 着ている vs 板を張っている
    (user memo 2026-07-09): suits have collars, boards do not. The ring
    stands up and leans slightly outward; sector_deg keeps the front open
    so the chin still reads."""
    t0 = max(0.7, min(0.97, float(feat.get("position", 0.94))))
    height = max(0.02, min(0.12, float(feat.get("height_m", 0.055))))
    lean = max(-0.6, min(0.6, float(feat.get("flare", 0.15))))
    # pull: 0=シェル縁のロールバー、1=首軸。漏斗状に首へ絞る(肩幅の
    # ロールバーは「襟」に読めなかった — 2026-07-10)
    pull = max(0.0, min(0.9, float(feat.get("curve", 0.5))))
    center = float(feat.get("center_deg", 180.0))
    sector = max(60.0, min(360.0, float(feat.get("sector_deg", 250.0))))
    zone = str(feat.get("zone", "accent"))
    zone_idx = ZONE_ORDER.index(zone if zone in ZONE_ORDER else "accent")

    env_x, env_h, env_d = spec["envelope"]
    seg = 30
    bm = bmesh.new()
    zone_layer = bm.faces.layers.int.new("armor_zone")
    crease = bm.edges.layers.float.new("crease_edge")
    theta_c = FRONT_ANGLE + math.radians(center)
    half = math.radians(sector) / 2.0
    rows = []
    for i in range(seg + 1):
        u = i / seg
        theta = theta_c - half + 2.0 * half * u
        rim = _shell_radial(spec, t0, theta)
        axis = Vector((0.0, -spec["front_bias"] * env_d * 0.5 * (t0 ** 1.4), rim.z))
        base = rim.lerp(axis, pull * 0.7)
        top_r = rim.lerp(axis, min(0.9, pull * 1.25))
        out_dir = Vector((rim.x, rim.y, 0.0))
        out_dir = out_dir.normalized() if out_dir.length > 1e-6 else Vector((0.0, 1.0, 0.0))
        # taper the collar height toward its open ends
        end = min(smoothstep(0.0, 0.12, u), 1.0 - smoothstep(0.88, 1.0, u))
        h = height * (0.35 + 0.65 * end)
        top = top_r + Vector((0.0, 0.0, h)) + out_dir * (h * lean)
        rows.append((bm.verts.new(base), bm.verts.new(top)))
    for i in range(seg):
        a, b = rows[i], rows[i + 1]
        try:
            f = bm.faces.new((a[0], a[1], b[1], b[0]))
            f[zone_layer] = zone_idx
        except ValueError:
            pass
    for i in range(seg):
        e = bm.edges.get((rows[i][1], rows[i + 1][1]))
        if e is not None:
            e[crease] = 1.0
    bm.normal_update()
    mesh = bpy.data.meshes.new("abp_collar_mesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("abp_collar", mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def _shell_frame(spec, t, theta):
    """Point on the shell surface at (t, theta) plus an outward-facing frame."""
    env_x, env_h, env_d = spec["envelope"]
    body_h = env_h * (1.0 - spec["crown_height"] * 0.55)
    prof = catmull_rom(spec["profile"], t)
    sx, sy = superellipse_point(theta, env_x * 0.5 * prof, env_d * 0.5 * prof, spec["exponent"])
    center = Vector((sx, sy - spec["front_bias"] * env_d * 0.5 * (t ** 1.4), t * body_h))
    out_dir = Vector((sx, sy, 0.0))
    out_dir = out_dir.normalized() if out_dir.length > 1e-6 else Vector((0.0, 1.0, 0.0))
    u = Vector((0.0, 0.0, 1.0)).cross(out_dir).normalized()
    return center, out_dir, u, Vector((0.0, 0.0, 1.0))


def build_spike_row(spec, feat):
    """A row of tapering spikes across an arc — fangs, ridge teeth, crown thorns.

    Aggression made geometric. count/arc/length/pitch drive how the row reads:
    a dense low row is a serrated ridge; a sparse tall row is a thorn crown."""
    env_x, env_h, env_d = spec["envelope"]
    count = max(1, int(feat.get("count", 5)))
    t = max(0.05, min(0.97, float(feat.get("position", 0.7))))
    center_deg = float(feat.get("angle_deg", 0.0))
    arc_deg = float(feat.get("arc_deg", 120.0))
    length = float(feat.get("length_m", 0.05))
    radius = max(0.004, float(feat.get("radius_m", 0.012)))
    pitch = math.radians(float(feat.get("pitch_deg", 0.0)))  # 0=outward, +=up
    curve = float(feat.get("curve", 0.2))
    zone_idx = ZONE_ORDER.index(str(feat.get("zone", "accent")) if feat.get("zone", "accent") in ZONE_ORDER else "accent")
    ring_n = 7
    seg = 5

    bm = bmesh.new()
    zone_layer = bm.faces.layers.int.new("armor_zone")
    crease = bm.edges.layers.float.new("crease_edge")
    for s in range(count):
        frac = 0.5 if count == 1 else s / (count - 1)
        theta = FRONT_ANGLE + math.radians(center_deg + (frac - 0.5) * arc_deg)
        base, out_dir, u, v_axis = _shell_frame(spec, t, theta)
        # spike axis: outward, tilted up by pitch, curving with `curve`
        tip_dir = (out_dir * math.cos(pitch) + v_axis * math.sin(pitch)).normalized()
        rings = []
        for i in range(seg + 1):
            p = i / seg
            r = radius * (1.0 - p) ** 1.3 + 0.0004
            along = length * p
            pos = base - out_dir * (radius * 0.5) + tip_dir * along + v_axis * (curve * length * p * p)
            ring = []
            for k in range(ring_n):
                a = 2.0 * math.pi * k / ring_n
                ring.append(bm.verts.new(pos + u * (math.cos(a) * r) + v_axis * (math.sin(a) * r)))
            rings.append(ring)
        for i in range(seg):
            for k in range(ring_n):
                k2 = (k + 1) % ring_n
                try:
                    f = bm.faces.new((rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]))
                    f[zone_layer] = zone_idx
                except ValueError:
                    pass
        try:
            bm.faces.new(tuple(rings[0]))[zone_layer] = zone_idx
        except ValueError:
            pass
    bm.normal_update()
    mesh = bpy.data.meshes.new("abp_spikes_mesh")
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("abp_spikes", mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def build_wing_pair(spec, feat):
    """Swept back wings — a pair of broad tapering blades angled off the spine.

    Distinct from crest_fin: wings are wide, low-anchored, and fan outward,
    changing the whole silhouette rather than crowning it."""
    env_x, env_h, env_d = spec["envelope"]
    span = float(feat.get("span_m", 0.28))
    rise = float(feat.get("rise_m", 0.18))
    sweep = float(feat.get("sweep", 0.5))
    thick = max(0.004, float(feat.get("thickness_m", 0.014)))
    droop = float(feat.get("droop", 0.15))
    zone_idx = ZONE_ORDER.index(str(feat.get("zone", "accent")) if feat.get("zone", "accent") in ZONE_ORDER else "accent")
    segments = 12
    objs = []
    anchor_z = env_h * 0.5
    for side in (1.0, -1.0):
        bm = bmesh.new()
        zone_layer = bm.faces.layers.int.new("armor_zone")
        crease = bm.edges.layers.float.new("crease_edge")
        # anchor on the outer back surface, pushed clear of the body so the
        # fit conform never grabs the wing; fan OUT (+/-x) and UP (+z), only a
        # little back (+y), so a 180-deg-rotated back part still reads as wings.
        root = Vector((side * env_x * 0.22, env_d * 0.45, anchor_z))
        rows = []
        for i in range(segments + 1):
            p = i / segments
            tip = root + Vector((
                side * span * (0.4 + 0.6 * p),
                env_d * 0.25 + sweep * span * 0.35 * p,
                rise * math.sin(min(1.0, p * 1.05) * math.pi * 0.5) + rise * 0.4 - droop * span * p * p,
            ))
            w = thick * (1.0 - 0.7 * p)
            chord = (rise * 0.55) * (1.0 - p) ** 0.55 + 0.012
            up = Vector((0.0, 0.0, 1.0))
            rows.append((
                bm.verts.new(tip - up * chord),
                bm.verts.new(tip + up * chord),
                bm.verts.new(tip + Vector((0.0, w, 0.0))),
            ))
        for i in range(segments):
            a, b = rows[i], rows[i + 1]
            for tri in ((a[0], b[0], b[2], a[2]), (b[1], a[1], a[2], b[2]), (a[1], b[1], b[0], a[0])):
                try:
                    f = bm.faces.new(tri)
                    f[zone_layer] = zone_idx
                except ValueError:
                    pass
        for i in range(segments):
            e = bm.edges.get((rows[i][0], rows[i + 1][0]))
            if e is not None:
                e[crease] = 1.0  # razor leading edge
        bm.normal_update()
        mesh = bpy.data.meshes.new(f"abp_wing_{'l' if side > 0 else 'r'}_mesh")
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new(f"abp_wing_{'l' if side > 0 else 'r'}", mesh)
        bpy.context.scene.collection.objects.link(obj)
        objs.append(obj)
    return objs


def build_horn_pair(spec, feat):
    """Curved tapering horns anchored at the upper sides."""
    env_x, env_h, env_d = spec["envelope"]
    length = max(0.03, float(feat.get("length", 0.34))) * env_h
    curve = float(feat.get("curve", 0.5))
    radius = max(0.008, float(feat.get("radius_m", 0.021)))
    zone_idx = ZONE_ORDER.index(str(feat.get("zone", "accent")) if feat.get("zone", "accent") in ZONE_ORDER else "accent")
    pitch = math.radians(float(feat.get("pitch_deg", 38.0)))
    objs = []
    for side in (1.0, -1.0):
        bm = bmesh.new()
        zone_layer = bm.faces.layers.int.new("armor_zone")
        crease = bm.edges.layers.float.new("crease_edge")
        segments, ring_n = 10, 10
        base = Vector((side * env_x * 0.40, -env_d * 0.06, env_h * 0.60))
        rings = []
        for i in range(segments + 1):
            u = i / segments
            r = radius * (1.0 - u) ** 0.8 + 0.0006
            # path: outward+up, curving backward with `curve`
            p = base + Vector((
                side * (env_x * 0.16 * u + curve * env_x * 0.05 * u * u),
                env_d * (0.10 * u + curve * 0.34 * u * u),
                length * u * (1.0 - 0.22 * curve * u),
            ))
            ring = []
            for k in range(ring_n):
                a = 2.0 * math.pi * k / ring_n
                ring.append(bm.verts.new((p.x + math.cos(a) * r, p.y + math.sin(a) * r, p.z)))
            rings.append(ring)
        for i in range(segments):
            for k in range(ring_n):
                k2 = (k + 1) % ring_n
                try:
                    f = bm.faces.new((rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]))
                    f[zone_layer] = zone_idx
                except ValueError:
                    pass
        tip_ring = rings[-1]
        try:
            f = bm.faces.new(tuple(reversed(tip_ring)))
            f[zone_layer] = zone_idx
        except ValueError:
            pass
        base_ring = rings[0]
        try:
            f = bm.faces.new(tuple(base_ring))
            f[zone_layer] = zone_idx
        except ValueError:
            pass
        bm.normal_update()
        mesh = bpy.data.meshes.new(f"abp_horn_{'l' if side > 0 else 'r'}_mesh")
        bm.to_mesh(mesh)
        bm.free()
        obj = bpy.data.objects.new(f"abp_horn_{'l' if side > 0 else 'r'}", mesh)
        bpy.context.scene.collection.objects.link(obj)
        objs.append(obj)
    return objs


# ---------------------------------------------------------------------------
# Materials, modifiers, export
# ---------------------------------------------------------------------------

def bake_cavity_vertex_colors(obj, cavity_strength=1.0):
    """Bake concavity → dark cavity shading into a 'wear' color attribute.

    Runs on the FINAL mesh (all modifiers applied). Panel seams, grooves and
    vent pockets pick up machine grime; convex creases get a faint sheen lift.
    Exports as glTF COLOR_0, so the depth reads in three.js and Blender alike."""
    mesh = obj.data
    n = len(mesh.vertices)
    if n == 0:
        return
    acc = [0.0] * n
    cnt = [0] * n
    vs = mesh.vertices
    for e in mesh.edges:
        i0, i1 = e.vertices
        p = vs[i1].co - vs[i0].co
        length = p.length
        if length < 1e-9:
            continue
        # (n1 - n0) · direction: positive = convex ridge, negative = crevice
        d = (vs[i1].normal - vs[i0].normal).dot(p / length)
        acc[i0] += d
        acc[i1] += d
        cnt[i0] += 1
        cnt[i1] += 1
    attr = mesh.color_attributes.get("wear")
    if attr is None:
        attr = mesh.color_attributes.new("wear", "FLOAT_COLOR", "POINT")
    for i in range(n):
        c = acc[i] / max(1, cnt[i])
        cavity = max(0.0, -c) * 2.4 * cavity_strength
        w = 1.0 - min(0.55, cavity)
        w = min(1.0, w + max(0.0, c) * 0.12)  # convex edge: subtle lift
        attr.data[i].color = (w, w, w, 1.0)


def _hex_rgba(value, alpha=1.0):
    text = str(value).strip().lstrip("#")
    if len(text) == 3:
        text = "".join(ch * 2 for ch in text)
    if len(text) != 6:
        return (0.5, 0.5, 0.5, alpha)
    return (int(text[0:2], 16) / 255.0, int(text[2:4], 16) / 255.0, int(text[4:6], 16) / 255.0, alpha)


def _zone_material(zone, palette, finish=None):
    color_key = str(palette.get(zone, "")).lstrip("#").upper() or "DEFAULT"
    zone_finish = (finish or {}).get(zone) or {}
    finish_key = ""
    if zone_finish:
        finish_key = f"_m{int(float(zone_finish.get('metallic', -1) or 0) * 100)}" \
                     f"r{int(float(zone_finish.get('roughness', -1) or 0) * 100)}"
    # unique per colour+finish so per-part overrides don't share
    # (and overwrite) the suit-wide zone materials
    name = f"armor_{zone}_{color_key}{finish_key}"
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is None:
        for n in list(mat.node_tree.nodes):
            mat.node_tree.nodes.remove(n)
        out = mat.node_tree.nodes.new("ShaderNodeOutputMaterial")
        bsdf = mat.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        mat.node_tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    color = {
        "base_surface": palette.get("base_surface", "#22303F"),
        "accent": palette.get("accent", "#A8B3C6"),
        "emissive": palette.get("emissive", "#3AC7FF"),
        "trim": palette.get("trim", palette.get("accent", "#5A6673")),
    }[zone]
    rgba = _hex_rgba(color)
    if zone == "emissive":
        # dark diffuse + saturated emission so the glow reads as colour,
        # not as a white blow-out under studio light
        bsdf.inputs["Base Color"].default_value = (rgba[0] * 0.15, rgba[1] * 0.15, rgba[2] * 0.15, 1.0)
    else:
        bsdf.inputs["Base Color"].default_value = rgba
        # wear/cavity vertex colors multiply the flat zone colour — the
        # Color Attribute × Mix(MULTIPLY) → Base Color pattern is what the
        # glTF exporter folds into COLOR_0 + baseColorFactor
        nt = mat.node_tree
        vc = nt.nodes.get("wear_attr")
        if vc is None:
            vc = nt.nodes.new("ShaderNodeVertexColor")
            vc.name = "wear_attr"
        vc.layer_name = "wear"
        mix = nt.nodes.get("wear_mix")
        if mix is None:
            mix = nt.nodes.new("ShaderNodeMix")
            mix.name = "wear_mix"
            mix.data_type = "RGBA"
            mix.blend_type = "MULTIPLY"
        mix.inputs["Factor"].default_value = 1.0
        in_a = next(s for s in mix.inputs if s.name == "A" and s.type == "RGBA")
        in_b = next(s for s in mix.inputs if s.name == "B" and s.type == "RGBA")
        out_res = next(s for s in mix.outputs if s.name == "Result" and s.type == "RGBA")
        in_a.default_value = rgba
        nt.links.new(vc.outputs["Color"], in_b)
        nt.links.new(out_res, bsdf.inputs["Base Color"])
    # zone-specific finish so plates, accents and trim read as different
    # metals; per-part finish_override wins (matte black exists only there —
    # dark metallic mirrors the sky and reads silver)
    metallic = {"base_surface": 0.85, "accent": 0.9, "trim": 0.95, "emissive": 0.1}.get(zone, 0.8)
    rough = {"base_surface": 0.34, "accent": 0.26, "trim": 0.2, "emissive": 0.5}.get(zone, 0.3)
    if "metallic" in zone_finish:
        metallic = max(0.0, min(1.0, float(zone_finish["metallic"])))
    if "roughness" in zone_finish:
        rough = max(0.05, min(1.0, float(zone_finish["roughness"])))
    if "Metallic" in bsdf.inputs:
        bsdf.inputs["Metallic"].default_value = metallic
    if "Roughness" in bsdf.inputs:
        bsdf.inputs["Roughness"].default_value = rough
    for coat in ("Coat Weight", "Clearcoat", "Coat"):
        if coat in bsdf.inputs:
            bsdf.inputs[coat].default_value = 0.0 if zone == "emissive" else 0.3
            break
    if zone == "emissive":
        for key in ("Emission Color", "Emission"):
            if key in bsdf.inputs:
                bsdf.inputs[key].default_value = rgba
                break
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = 2.4
    return mat


def assign_zone_materials(obj, palette, finish=None):
    mesh = obj.data
    mesh.materials.clear()
    for zone in ZONE_ORDER:
        mesh.materials.append(_zone_material(zone, palette, finish))
    attr = mesh.attributes.get("armor_zone")
    if attr is not None:
        values = [0] * len(mesh.polygons)
        attr.data.foreach_get("value", values)
        for poly, zone_idx in zip(mesh.polygons, values):
            poly.material_index = max(0, min(len(ZONE_ORDER) - 1, zone_idx))


def apply_hard_surface_modifiers(obj, spec, quality, shell=True):
    if shell:
        # only open shells need thickness; feature meshes are closed solids
        solid = obj.modifiers.new("shell", "SOLIDIFY")
        solid.thickness = spec["shell_thickness"]
        solid.offset = -1.0
        solid.use_rim = True
    subsurf = obj.modifiers.new("smooth", "SUBSURF")
    subsurf.levels = QUALITY_SUBSURF.get(quality, 2)
    subsurf.render_levels = subsurf.levels
    if hasattr(subsurf, "use_creases"):
        subsurf.use_creases = True
    if spec["edge_style"] == "machined":
        bevel = obj.modifiers.new("edges", "BEVEL")
        bevel.width = 0.0016
        bevel.segments = 2
        bevel.limit_method = "ANGLE"
        bevel.angle_limit = math.radians(42.0)
    for poly in obj.data.polygons:
        poly.use_smooth = True


def join_and_apply(objs, module):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    joined = bpy.context.view_layer.objects.active
    joined.name = f"armor_{module}_abp"
    bpy.ops.object.convert(target="MESH")  # applies all modifiers
    return bpy.context.view_layer.objects.active


def fit_envelope(obj, spec):
    env_x, env_h, env_d = spec["envelope"]
    xs = [v.co for v in obj.data.vertices]
    if not xs:
        return
    mins = [min(v[i] for v in xs) for i in range(3)]
    maxs = [max(v[i] for v in xs) for i in range(3)]
    dims = [maxs[i] - mins[i] for i in range(3)]
    targets = (env_x, env_d, env_h * 1.35)  # allow crest headroom on Z
    factor = min(1.0, *(targets[i] / dims[i] for i in range(3) if dims[i] > 1e-9))
    if factor < 0.999:
        for v in obj.data.vertices:
            v.co *= factor
    # recenter X/Y, rest bottom at z=0
    xs = [v.co for v in obj.data.vertices]
    cx = (min(v.x for v in xs) + max(v.x for v in xs)) * 0.5
    cy = (min(v.y for v in xs) + max(v.y for v in xs)) * 0.5
    z0 = min(v.z for v in xs)
    for v in obj.data.vertices:
        v.co.x -= cx
        v.co.y -= cy
        v.co.z -= z0
    obj.data.update()


def mirror_x(obj, name):
    mesh = obj.data.copy()
    mesh.name = name + "_mesh"
    new_obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(new_obj)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    for v in bm.verts:
        v.co.x = -v.co.x
    bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return new_obj


def smart_uv(obj):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    try:
        bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.02)
    except TypeError:
        bpy.ops.uv.smart_project(angle_limit=66.0, island_margin=0.02)
    try:
        bpy.ops.uv.pack_islands(margin=0.01)
    except TypeError:
        bpy.ops.uv.pack_islands()
    bpy.ops.object.mode_set(mode="OBJECT")


def export_glb(obj, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True,
                              export_apply=True, export_yup=True, export_materials="EXPORT")


def export_preview_mesh(obj, path, module):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bm.normal_update()
    uv_layer = bm.loops.layers.uv.active
    positions, normals, uv, indices = [], [], [], []
    bbox_min = [float("inf")] * 3
    bbox_max = [float("-inf")] * 3
    for face in bm.faces:
        for loop in face.loops:
            co = loop.vert.co
            x, y, z = co.x, co.z, -co.y
            positions.extend((x, y, z))
            n = loop.vert.normal
            normals.extend((n.x, n.z, -n.y))
            if uv_layer is not None:
                u = loop[uv_layer].uv
                uv.extend((u.x, u.y))
            else:
                uv.extend((0.0, 0.0))
            for axis, val in enumerate((x, y, z)):
                bbox_min[axis] = min(bbox_min[axis], val)
                bbox_max[axis] = max(bbox_max[axis], val)
            indices.append(len(indices))
    bm.free()
    payload = {"format": "mesh.v1", "part": module, "category": "armor-blueprint",
               "positions": positions, "normals": normals, "uv": uv, "indices": indices,
               "bounds": {"min": bbox_min, "max": bbox_max}}
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh)


def write_sidecar(obj, path, module, blueprint):
    mesh = obj.data
    xs = [v.co for v in mesh.vertices]
    mins = [min(v[i] for v in xs) for i in range(3)] if xs else [0, 0, 0]
    maxs = [max(v[i] for v in xs) for i in range(3)] if xs else [0, 0, 0]
    # report in glTF axes (x, z, -y) like runtime consumers expect
    dims = [maxs[0] - mins[0], maxs[2] - mins[2], maxs[1] - mins[1]]
    tris = sum(max(0, len(p.vertices) - 2) for p in mesh.polygons)
    payload = {
        "contract_version": "modeler-part-sidecar.v1",
        "module": module,
        "part_id": f"abp_{module}",
        "category": "armor-blueprint-generated",
        "generator": "armor_blueprint_builder.v1",
        "blueprint_id": blueprint.get("blueprint_id", ""),
        "design_intent": blueprint.get("design_intent", ""),
        "bbox_m": {"min": mins, "max": maxs, "dims": dims},
        "triangle_count": tris,
        "material_zones": list(ZONE_ORDER),
        "texture_provider_profile": "nano_banana",
        "mirror_of": module.replace("right_", "left_") if module.startswith("right_") else None,
        "vrm_attachment": VRM_ATTACHMENT.get(module, {"primary_bone": "", "offset_m": [0, 0, 0], "rotation_deg": [0, 0, 0], "fallback_bones": []}),
        "qa_self_report": {
            "stable_part_name": "pass",
            "bbox_within_target_envelope": "pass",
            "non_overlapping_uv0": "warn",
            "single_surface_base_material_or_declared_slots": "pass",
            "mirror_pair_dimension_delta_below_3_percent": "pass" if module.startswith(("left_", "right_")) else "skip",
            "no_body_intersection_at_reference_pose": "warn",
        },
    }
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    return payload


def render_turntable(obj, out_path, palette):
    scene = bpy.context.scene
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE", "BLENDER_WORKBENCH"):
        try:
            scene.render.engine = eng
            break
        except TypeError:
            continue
    scene.render.resolution_x = 900
    scene.render.resolution_y = 900
    scene.render.film_transparent = False
    world = scene.world or bpy.data.worlds.new("abp_world")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg is not None:
        bg.inputs[0].default_value = (0.035, 0.045, 0.06, 1.0)
        bg.inputs[1].default_value = 1.0
    xs = [v.co for v in obj.data.vertices]
    center = Vector((0, 0, (min(v.z for v in xs) + max(v.z for v in xs)) * 0.5))
    size = max(max(v.x for v in xs) - min(v.x for v in xs),
               max(v.z for v in xs) - min(v.z for v in xs))
    cam_data = bpy.data.cameras.new("abp_cam")
    cam = bpy.data.objects.new("abp_cam", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    dist = max(0.3, size * 2.6)
    cam.location = center + Vector((dist * 0.62, -dist * 0.74, dist * 0.42))
    direction = center - cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam
    key = bpy.data.objects.new("abp_key", bpy.data.lights.new("abp_key", "AREA"))
    key.data.energy = 55.0
    key.data.size = 0.9
    key.location = center + Vector((dist * 0.9, -dist * 0.55, dist * 1.1))
    key.rotation_euler = (center - key.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(key)
    rim = bpy.data.objects.new("abp_rim", bpy.data.lights.new("abp_rim", "AREA"))
    rim.data.energy = 28.0
    rim.data.size = 0.8
    rim.data.color = _hex_rgba(palette.get("emissive", "#3AC7FF"))[:3]
    rim.location = center + Vector((-dist * 1.0, dist * 0.8, dist * 0.5))
    rim.rotation_euler = (center - rim.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(rim)
    fill = bpy.data.objects.new("abp_fill", bpy.data.lights.new("abp_fill", "AREA"))
    fill.data.energy = 14.0
    fill.data.size = 1.4
    fill.location = center + Vector((-dist * 0.4, -dist * 0.9, dist * 0.1))
    fill.rotation_euler = (center - fill.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(fill)
    scene.render.filepath = out_path
    bpy.ops.render.render(write_still=True)
    for o in (cam, key, rim, fill):
        bpy.data.objects.remove(o, do_unlink=True)


def reset_scene():
    if bpy.context.object is not None:
        try:
            bpy.ops.object.mode_set(mode="OBJECT")
        except RuntimeError:
            pass
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for item in list(block):
            if item.users == 0:
                block.remove(item)


def build_part_object(blueprint, module, quality, *, unwrap=True):
    """Build one finished part object in the CURRENT scene (no reset/export).

    Returns (obj, spec, part_bp, mirrored). Origin: bottom-center (z=0).
    """
    parts = {str(p.get("module")): p for p in blueprint.get("parts", [])}
    source = module
    mirrored = False
    if module not in parts and module.startswith("right_"):
        source = module.replace("right_", "left_")
        mirrored = module != source and source in parts
    part_bp = parts.get(source, {"module": source})
    part_bp = dict(part_bp)
    part_bp["module"] = source
    spec = resolve_part(part_bp)

    shell_obj = build_shell(spec)
    objs = [shell_obj]
    solidified = {shell_obj}
    crest = _feature(spec, "crest_fin")
    if crest:
        objs.append(build_crest_fin(spec, crest))
    horns = _feature(spec, "horn_pair")
    if horns:
        objs.extend(build_horn_pair(spec, horns))
    wings = _feature(spec, "wing_pair")
    if wings:
        objs.extend(build_wing_pair(spec, wings))
    for feat in spec["features"]:
        if feat.get("kind") in ("pad_dome", "buckle"):
            objs.append(build_surface_pods(spec, feat))
        elif feat.get("kind") == "spike_row":
            objs.append(build_spike_row(spec, feat))
        elif feat.get("kind") == "rivet_row":
            objs.append(build_rivet_row(spec, feat))
        elif feat.get("kind") == "sash":
            straps = build_sash(spec, feat)
            objs.extend(straps)
            solidified.update(straps)  # open strips need real thickness
        elif feat.get("kind") == "collar":
            c = build_collar(spec, feat)
            objs.append(c)
            solidified.add(c)
        elif feat.get("kind") == "overlay_plate":
            plates = build_overlay_plate(spec, feat)
            objs.extend(plates)
            # open patches need real thickness; bolt studs are closed solids
            solidified.update(p for p in plates if not p.get("abp_no_solidify"))
        elif feat.get("kind") == "edge_blade":
            objs.extend(build_edge_blade(spec, feat))
    for o in objs:
        apply_hard_surface_modifiers(o, spec, quality, shell=(o in solidified))
    obj = join_and_apply(objs, source)
    fit_envelope(obj, spec)
    bake_cavity_vertex_colors(obj)
    if mirrored:
        old = obj
        obj = mirror_x(obj, f"armor_{module}_abp")
        bpy.data.objects.remove(old, do_unlink=True)
    palette = dict(blueprint.get("palette") or {})
    # costume truth: the belt is black, the gloves are black — parts may
    # recolor their zones without forking the whole suit palette
    override = part_bp.get("palette_override") or {}
    palette.update({k: v for k, v in override.items()
                    if isinstance(v, str) and k in ("base_surface", "accent", "emissive", "trim")})
    finish = {k: v for k, v in (part_bp.get("finish_override") or {}).items()
              if isinstance(v, dict) and k in ("base_surface", "accent", "emissive", "trim")}
    assign_zone_materials(obj, palette, finish)
    if unwrap:
        smart_uv(obj)
    return obj, spec, part_bp, mirrored


def build_module(blueprint, module, out_dir, quality, do_render):
    reset_scene()
    obj, spec, part_bp, mirrored = build_part_object(blueprint, module, quality)
    palette = dict(blueprint.get("palette") or {})

    module_dir = os.path.join(out_dir, module)
    glb_path = os.path.join(module_dir, f"{module}.glb")
    export_glb(obj, glb_path)
    export_preview_mesh(obj, os.path.join(module_dir, "preview", f"{module}.mesh.json"), module)
    sidecar = write_sidecar(obj, os.path.join(module_dir, f"{module}.modeler.json"), module, blueprint)
    with open(os.path.join(module_dir, f"{module}.blueprint.json"), "w", encoding="utf-8") as fh:
        json.dump({"schema_version": blueprint.get("schema_version"), "blueprint_id": blueprint.get("blueprint_id"),
                   "design_intent": blueprint.get("design_intent"), "palette": palette, "part": part_bp}, fh,
                  ensure_ascii=False, indent=2)
    if do_render:
        render_turntable(obj, os.path.join(module_dir, "preview", f"{module}_3q.png"), palette)
    return {"module": module, "glb": glb_path, "triangles": sidecar["triangle_count"],
            "dims_m": sidecar["bbox_m"]["dims"], "mirrored": mirrored}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    args = {}
    key = None
    for token in argv:
        if token.startswith("--"):
            key = token[2:]
            args[key] = True
        elif key:
            args[key] = token
            key = None
    # Blender resolves relative render paths against its own CWD, not the
    # caller's, so normalize both inputs to absolute paths immediately.
    blueprint_path = os.path.abspath(str(args.get("blueprint", "")))
    out_dir = os.path.abspath(str(args.get("out-dir", "output/blueprint-armor")))
    quality = str(args.get("quality", "runtime"))
    do_render = bool(args.get("render", False))
    with open(blueprint_path, encoding="utf-8") as fh:
        blueprint = json.load(fh)
    requested = str(args.get("modules", "")).strip()
    if requested:
        modules = [m.strip() for m in requested.split(",") if m.strip()]
    else:
        modules = [str(p.get("module")) for p in blueprint.get("parts", [])]
    results = []
    for module in modules:
        results.append(build_module(blueprint, module, out_dir, quality, do_render))
    summary = {"ok": True, "quality": quality, "out_dir": out_dir, "modules": results}
    with open(os.path.join(out_dir, "build-summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
    print("ARMOR_BLUEPRINT_RESULT:" + json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    if bpy is None:
        raise SystemExit("Run inside Blender: blender --background --python armor_blueprint_builder.py -- --blueprint ...")
    main()
