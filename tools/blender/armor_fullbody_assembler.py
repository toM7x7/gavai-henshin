"""Assemble a full ArmorBlueprint suit onto the default VRM body and render it.

Answers three questions in one image set:
  1. does the generated lineup read as one tokusatsu suit over the base body?
  2. how well does each part fit the VRM proportions?
  3. what do different blueprints look like side by side?

Run headless (from the repo root D:/personal_dev/gavai-henshin/gavai-henshin):
  blender --background --factory-startup --python tools/blender/armor_fullbody_assembler.py -- \
    --blueprint output/blueprint-armor/intent-demo.blueprint.json \
    --out-dir output/blueprint-armor/fullbody --quality preview --label demo

Normally invoked through tools/armor_variation_lab.py.
"""
from __future__ import annotations

import importlib.util
import json
import math
import os
import sys

import bmesh  # type: ignore
import bpy  # type: ignore
from mathutils import Euler, Vector  # type: ignore
from mathutils.bvhtree import BVHTree  # type: ignore

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "armor_blueprint_builder", os.path.join(_HERE, "armor_blueprint_builder.py"))
builder = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(builder)

VRM_PATH = os.path.abspath(os.path.join(_HERE, "..", "..", "viewer", "assets", "vrm", "default.vrm"))

ALL_MODULES = [
    "helmet", "chest", "back", "waist",
    "left_shoulder", "right_shoulder",
    "left_upperarm", "right_upperarm",
    "left_forearm", "right_forearm",
    "left_hand", "right_hand",
    "left_thigh", "right_thigh",
    "left_shin", "right_shin",
    "left_boot", "right_boot",
]

# VRM humanoid name -> VRoid armature bone name
BONE_NAME = {
    "head": "J_Bip_C_Head",
    "neck": "J_Bip_C_Neck",
    "upperChest": "J_Bip_C_UpperChest",
    "chest": "J_Bip_C_Chest",
    "hips": "J_Bip_C_Hips",
    "leftShoulder": "J_Bip_L_Shoulder",
    "rightShoulder": "J_Bip_R_Shoulder",
    "leftUpperArm": "J_Bip_L_UpperArm",
    "rightUpperArm": "J_Bip_R_UpperArm",
    "leftLowerArm": "J_Bip_L_LowerArm",
    "rightLowerArm": "J_Bip_R_LowerArm",
    "leftHand": "J_Bip_L_Hand",
    "rightHand": "J_Bip_R_Hand",
    "leftUpperLeg": "J_Bip_L_UpperLeg",
    "rightUpperLeg": "J_Bip_R_UpperLeg",
    "leftLowerLeg": "J_Bip_L_LowerLeg",
    "rightLowerLeg": "J_Bip_R_LowerLeg",
    "leftFoot": "J_Bip_L_Foot",
    "rightFoot": "J_Bip_R_Foot",
}

# worn sizes mirror QUEST_GLB_TARGET_SIZES in viewer/quest-iw-demo/quest-demo.js
# (glTF order: width, height, depth) — the runtime fit contract.
WORN_SIZE = {
    "helmet": (0.24, 0.30, 0.24),  # overridden by calibrate_helmet_to_head
    # 丈0.36: 裾を肋骨下まで下げ、腰との間の脇腹リビールを絞る(2026-07-10)
    "chest": (0.42, 0.36, 0.11),
    "back": (0.40, 0.36, 0.12),
    # waist wraps the full hip ring now (butt covered): depth must hold the
    # actual pelvis+glutes, and the guard must reach BELOW the glutes —
    # an exposed backside is a weakness, not a design choice
    # 丈0.19は実測の均衡点: 上へ伸ばすと上端リムが腹の張り出しへ、下へ伸ばすと
    # 底部リムが臀部へ食い込み rigid_shift が上下往復して収束しない(2026-07-10実測)。
    # 脇腹のシーム閉鎖は胸/背の奥行き0.74/0.62+wrap218/208+裾下げが担う
    "waist": (0.36, 0.19, 0.21),
    "left_shoulder": (0.15, 0.10, 0.13),
    "right_shoulder": (0.15, 0.10, 0.13),
    "left_upperarm": (0.09, 0.28, 0.09),
    "right_upperarm": (0.09, 0.28, 0.09),
    "left_forearm": (0.085, 0.25, 0.085),
    "right_forearm": (0.085, 0.25, 0.085),
    "left_hand": (0.095, 0.08, 0.11),
    "right_hand": (0.095, 0.08, 0.11),
    "left_thigh": (0.11, 0.36, 0.10),
    "right_thigh": (0.11, 0.36, 0.10),
    "left_shin": (0.095, 0.33, 0.095),
    "right_shin": (0.095, 0.33, 0.095),
    "left_boot": (0.12, 0.12, 0.20),
    "right_boot": (0.12, 0.12, 0.20),
}

# armor floats over the undersuit: radial clearance multiplier (x/depth axes)
CLEARANCE = {
    "default": 1.0,
    "helmet": 1.15,
    "chest": 1.20,
    "back": 1.15,
    "waist": 1.10,
    "left_shoulder": 1.15, "right_shoulder": 1.15,
    "left_upperarm": 1.35, "right_upperarm": 1.35,
    "left_forearm": 1.35, "right_forearm": 1.35,
    "left_thigh": 1.30, "right_thigh": 1.30,
    "left_shin": 1.32, "right_shin": 1.32,
    "left_hand": 1.2, "right_hand": 1.2,
}

# assembly rules per module:
#   anchor: humanoid bone
#   mode:   "center" = part bbox-center sits on the anchor point
#           "bottom" = part origin (bottom-center) sits on the anchor point
#           "along"  = part +Z axis is rotated onto the bone head->tail axis,
#                       then the part is centered on the bone midpoint
#   delta:  extra offset in Blender frame (x, y, z) after facing alignment
PLACEMENT = {
    "helmet": {"anchor": "head", "mode": "center", "delta": (0.0, 0.0, 0.05)},
    "chest": {"anchor": "upperChest", "mode": "center", "delta": (0.0, -0.025, 0.01)},
    "back": {"anchor": "upperChest", "mode": "center", "rotate_z_deg": 180, "delta": (0.0, 0.03, 0.01)},
    "waist": {"anchor": "hips", "mode": "center", "delta": (0.0, 0.0, -0.02)},
    "left_shoulder": {"anchor": "leftUpperArm", "mode": "center", "delta": (0.075, 0.0, 0.06)},
    "right_shoulder": {"anchor": "rightUpperArm", "mode": "center", "delta": (-0.075, 0.0, 0.06)},
    "left_upperarm": {"anchor": "leftUpperArm", "mode": "along"},
    "right_upperarm": {"anchor": "rightUpperArm", "mode": "along"},
    "left_forearm": {"anchor": "leftLowerArm", "mode": "along"},
    "right_forearm": {"anchor": "rightLowerArm", "mode": "along"},
    "left_hand": {"anchor": "leftHand", "mode": "center", "delta": (0.03, 0.0, 0.02)},
    "right_hand": {"anchor": "rightHand", "mode": "center", "delta": (-0.03, 0.0, 0.02)},
    "left_thigh": {"anchor": "leftUpperLeg", "mode": "along"},
    "right_thigh": {"anchor": "rightUpperLeg", "mode": "along"},
    "left_shin": {"anchor": "leftLowerLeg", "mode": "along"},
    "right_shin": {"anchor": "rightLowerLeg", "mode": "along"},
    "left_boot": {"anchor": "leftFoot", "mode": "foot", "delta": (0.0, -0.05, 0.0)},
    "right_boot": {"anchor": "rightFoot", "mode": "foot", "delta": (0.0, -0.05, 0.0)},
}

# --- Fit Audit (適合審査) contract -----------------------------------------
# Fit is MEASURED against the body mesh, not assumed. For every sampled armor
# vertex we find the nearest body point and test the sign against the body
# normal: a vertex that lands on the inside is a penetration.
#
# Physical pass rule (what actually matters for a wearable plate):
#   * at most FIT_MAX_INTRUSION_RATIO of the armor may sink into the body, and
#   * no vertex may sink deeper than FIT_MAX_INTRUSION_M.
# "Not floating 6 mm off the skin everywhere" is fine — plates meet the body at
# their anchor. Failing parts are reforged (scaled or pushed) until they clear.
FIT_REFORGE_MAX_PASSES = 4
FIT_MAX_INTRUSION_RATIO = 0.01
FIT_MAX_INTRUSION_M = 0.004

# probe spec per module: axis source, angular sector (relative to front),
# span along the axis, required gap, and how a reforge may scale the part.
PROBE = {
    "helmet": {"axis": "vertical", "sector": (0, 180), "span": (0.12, 0.82), "gap_m": 0.008, "scale": "xyz", "anchor_xy": True, "max_body_r": 0.4, "reforge": "enclose"},
    "chest": {"axis": "vertical", "sector": (0, 84), "span": (0.15, 0.9), "gap_m": 0.010, "scale": "xy", "anchor_xy": True, "max_body_r": 0.6, "reforge": "push_front", "push_max": 0.05},
    "back": {"axis": "vertical", "sector": (180, 80), "span": (0.15, 0.9), "gap_m": 0.010, "scale": "xy", "anchor_xy": True, "max_body_r": 0.6, "reforge": "push_rear", "push_max": 0.05},
    "waist": {"axis": "vertical", "sector": (0, 118), "span": (0.2, 0.8), "gap_m": 0.008, "scale": "xy", "anchor_xy": True, "max_body_r": 0.6, "reforge": "scale_cap", "scale_cap": 1.12, "push_cap": 0.014, "crotch_guard": True, "max_ratio": 0.02, "crease_filter": True},
    "left_shoulder": {"axis": "vertical", "sector": (90, 78), "span": (0.35, 0.85), "gap_m": 0.008, "scale": "xy", "max_body_r": 0.3, "reforge": "report"},
    "right_shoulder": {"axis": "vertical", "sector": (-90, 78), "span": (0.35, 0.85), "gap_m": 0.008, "scale": "xy", "max_body_r": 0.3, "reforge": "report"},
    "left_upperarm": {"axis": "chain", "sector": (0, 180), "span": (0.15, 0.85), "gap_m": 0.006, "scale": "xy", "max_body_r": 0.22},
    "right_upperarm": {"axis": "chain", "sector": (0, 180), "span": (0.15, 0.85), "gap_m": 0.006, "scale": "xy", "max_body_r": 0.22},
    "left_forearm": {"axis": "chain", "sector": (0, 180), "span": (0.15, 0.85), "gap_m": 0.006, "scale": "xy", "max_body_r": 0.22},
    "right_forearm": {"axis": "chain", "sector": (0, 180), "span": (0.15, 0.85), "gap_m": 0.006, "scale": "xy", "max_body_r": 0.22},
    "left_hand": {"axis": "hand", "sector": (0, 180), "span": (0.1, 0.8), "gap_m": 0.004, "scale": "xy", "max_body_r": 0.12, "reforge": "scale_cap", "scale_cap": 1.15},
    "right_hand": {"axis": "hand", "sector": (0, 180), "span": (0.1, 0.8), "gap_m": 0.004, "scale": "xy", "max_body_r": 0.12, "reforge": "scale_cap", "scale_cap": 1.15},
    "left_thigh": {"axis": "chain", "sector": (0, 180), "span": (0.15, 0.85), "gap_m": 0.006, "scale": "xy", "max_body_r": 0.22},
    "right_thigh": {"axis": "chain", "sector": (0, 180), "span": (0.15, 0.85), "gap_m": 0.006, "scale": "xy", "max_body_r": 0.22},
    "left_shin": {"axis": "chain", "sector": (0, 180), "span": (0.15, 0.85), "gap_m": 0.006, "scale": "xy", "max_body_r": 0.22},
    "right_shin": {"axis": "chain", "sector": (0, 180), "span": (0.15, 0.85), "gap_m": 0.006, "scale": "xy", "max_body_r": 0.22},
    "left_boot": {"axis": "foot", "sector": (0, 180), "span": (0.2, 0.85), "gap_m": 0.004, "scale": "xyz", "max_body_r": 0.16, "reforge": "scale_cap", "scale_cap": 1.2},
    "right_boot": {"axis": "foot", "sector": (0, 180), "span": (0.2, 0.85), "gap_m": 0.004, "scale": "xyz", "max_body_r": 0.16, "reforge": "scale_cap", "scale_cap": 1.2},
}

# target joint reveals (undersuit visible between plates), measured ALONG the
# limb axis (T-pose safe): (upper part, lower part, joint humanoid bone chain)
JOINT_GAP_TARGETS_M = {
    "elbow": ("left_upperarm", "left_forearm", "leftUpperArm", 0.002, 0.06),
    "knee": ("left_thigh", "left_shin", "leftUpperLeg", 0.002, 0.08),
    "wrist": ("left_forearm", "left_hand", "leftLowerArm", -0.02, 0.06),
    # 上限0.07: へそ出しの防止(0.13は側面から見ると脇腹が空く)。
    # 下限-0.02: 胸裾が腰上端に僅かに被るのは瓦重ねで衣装として正(2026-07-10)
    "chest_waist": ("chest", "waist", None, -0.02, 0.07),
}

# The glTF importer synthesizes bone tails (all +Z), so limb direction must
# come from the joint chain: anchor joint -> next joint down the limb.
NEXT_JOINT = {
    "leftUpperArm": "leftLowerArm",
    "rightUpperArm": "rightLowerArm",
    "leftLowerArm": "leftHand",
    "rightLowerArm": "rightHand",
    "leftUpperLeg": "leftLowerLeg",
    "rightUpperLeg": "rightLowerLeg",
    "leftLowerLeg": "leftFoot",
    "rightLowerLeg": "rightFoot",
}

# fallback axes when a joint chain is degenerate
_FALLBACK_AXIS = {
    "left": Vector((1.0, 0.0, 0.0)),
    "right": Vector((-1.0, 0.0, 0.0)),
    "leg": Vector((0.0, 0.0, -1.0)),
}

# Which way the imported VRM faces in Blender. -1 = -Y (matches the parts'
# authoring frame); flip to +1 if renders show armor on the model's back.
BODY_FACING = -1.0


def rigid_skin_to_armature(obj, module, armature):
    """Weld an armor part to its anchor bone: 100% weight, rigid follow.
    This is what makes the suit poseable — and exportable as VRM/skinned GLB."""
    bone_name = BONE_NAME[PLACEMENT[module]["anchor"]]
    for vg in list(obj.vertex_groups):
        obj.vertex_groups.remove(vg)
    group = obj.vertex_groups.new(name=bone_name)
    group.add(list(range(len(obj.data.vertices))), 1.0, "REPLACE")
    mod = obj.modifiers.new("rig", "ARMATURE")
    mod.object = armature
    obj.parent = armature


def _mtoonify_material(mat):
    """Convert a principled material to MToon (VRM0 shader 'VRM/MToon').

    Empirical finding (2026-07-09, diff vs working VRoid files): services with
    UniVRM-derived importers only implement MToon. Exporting materials as
    VRM_USE_GLTFSHADER renders the avatar as an error placeholder — the
    infamous red box. Pull the flat zone colour out of the principled setup
    and hand it to the addon's MToon properties."""
    ext = getattr(mat, "vrm_addon_extension", None)
    if ext is None:
        return False
    color = (0.8, 0.8, 0.8, 1.0)
    emissive = (0.0, 0.0, 0.0)
    strength = 0.0
    if mat.use_nodes and mat.node_tree:
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        mix = mat.node_tree.nodes.get("wear_mix")
        if mix is not None:
            for s in mix.inputs:
                if s.name == "A" and s.type == "RGBA":
                    color = tuple(s.default_value)
                    break
        elif bsdf is not None:
            color = tuple(bsdf.inputs["Base Color"].default_value)
        if bsdf is not None:
            for key in ("Emission Color", "Emission"):
                if key in bsdf.inputs:
                    emissive = tuple(bsdf.inputs[key].default_value)[:3]
                    break
            if "Emission Strength" in bsdf.inputs:
                strength = float(bsdf.inputs["Emission Strength"].default_value)
    try:
        mt = ext.mtoon1
        mt.enabled = True
        mt.pbr_metallic_roughness.base_color_factor = color
        vmt = mt.extensions.vrmc_materials_mtoon
        # platform note (samplemovie, 2026-07-09): services atlas materials
        # and reinterpret MToon params — a deep shade colour renders as harsh
        # banding on some. Keep the shade shallow so every platform reads the
        # zone colour first.
        vmt.shade_color_factor = tuple(c * 0.72 for c in color[:3])
        vmt.shading_toony_factor = 0.7
        if strength > 0.0 and any(c > 0.01 for c in emissive):
            mt.emissive_factor = tuple(min(1.0, c) for c in emissive)
        return True
    except Exception as exc:  # noqa: BLE001 — addon property names vary
        print(f"MTOON_CONVERT_FAILED {mat.name}: {exc}")
        return False


def _apply_vrm_meta(ext, label):
    """Display-safe avatar meta for both VRM spec generations.

    allowed_user/avatar_permission gates whether services will even RENDER
    the avatar; everything else stays conservative (no redistribution)."""
    def try_set(target, name, value):
        try:
            setattr(target, name, value)
        except Exception:  # noqa: BLE001 — addon enum names vary by version
            pass

    m1 = getattr(getattr(ext, "vrm1", None), "meta", None)
    if m1 is not None:
        try_set(m1, "vrm_name", f"GAVAI {label}")
        try_set(m1, "version", "1.0")
        try_set(m1, "avatar_permission", "everyone")
        try_set(m1, "credit_notation", "unnecessary")
        try_set(m1, "commercial_usage", "personalNonProfit")
        try_set(m1, "modification", "prohibited")
        try_set(m1, "allow_redistribution", False)
        try:
            if not len(m1.authors):
                m1.authors.add()
            m1.authors[0].value = "gavai-henshin forge"
        except Exception:  # noqa: BLE001
            pass
    m0 = getattr(getattr(ext, "vrm0", None), "meta", None)
    if m0 is not None:
        try_set(m0, "title", f"GAVAI {label}")
        try_set(m0, "version", "1.0")
        try_set(m0, "author", "gavai-henshin forge")
        try_set(m0, "allowed_user_name", "Everyone")
        try_set(m0, "violent_ussage_name", "Disallow")
        try_set(m0, "sexual_ussage_name", "Disallow")
        try_set(m0, "commercial_ussage_name", "Disallow")
        try_set(m0, "license_name", "Redistribution_Prohibited")


def _body_world_verts():
    """All visible body vertices in world space (hair already hidden)."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    pts = []
    for obj in bpy.data.objects:
        if obj.type != "MESH" or obj.hide_render or obj.name.startswith("armor_"):
            continue
        ev = obj.evaluated_get(depsgraph)
        mesh = ev.to_mesh()
        mesh.transform(ev.matrix_world)
        pts.extend(v.co.copy() for v in mesh.vertices)
        ev.to_mesh_clear()
    return pts


def _slice_dims(pts, z0, z1, x_limit=None):
    """Width/depth of the body slice between two heights."""
    sel = [p for p in pts if z0 <= p.z <= z1 and (x_limit is None or abs(p.x) <= x_limit)]
    if len(sel) < 30:
        return None
    w = max(p.x for p in sel) - min(p.x for p in sel)
    d = max(p.y for p in sel) - min(p.y for p in sel)
    return w, d


def _limb_diameter(pts, head, tail, r_cap, t0=0.3, t1=0.75, x_side=None):
    """Max radial thickness around a bone segment.

    Measurement hygiene (learned the hard way): a generous radial window
    swallows the OTHER leg / the torso flank and reports elephant limbs.
    r_cap per limb type, t-range clipped away from joints, and x_side
    keeps only the limb's own side of the body."""
    axis = tail - head
    length = axis.length
    if length < 0.02:
        return None
    axis /= length
    r_max = 0.0
    found = 0
    for p in pts:
        if x_side is not None and p.x * x_side < 0.01:
            continue
        rel = p - head
        t = rel.dot(axis) / length
        if not (t0 <= t <= t1):
            continue
        radial = (rel - axis * (t * length)).length
        if radial < r_cap:
            r_max = max(r_max, radial)
            found += 1
    if found < 30:
        return None
    return r_max * 2.0


# ヒーロー増幅テーブル: 装甲=人体の増幅。幅は誇張し、胸の奥行きは体に沿わせ、
# 腰は絞る — Vテーパーはここで生まれる (docs/hero-proportion-grammar-2026-07.md)
_AMPLIFY = {
    "chest": {"w": 1.30, "d": 1.32},
    "waist": {"w": 1.12, "d": 1.18},  # pods need air or conform crushes them
    "shoulder": {"dia": 2.2},
    "upperarm": {"dia": 1.45},
    "forearm": {"dia": 1.5},
    "thigh": {"dia": 1.28},
    "shin": {"dia": 1.3},  # shin dia already contains the calf bulge
}
V_TAPER_MIN = 1.45
# per-limb measurement windows: (radial cap, t0, t1)
_LIMB_WINDOW = {
    "upperarm": (0.075, 0.35, 0.75),
    "forearm": (0.065, 0.3, 0.75),
    "thigh": (0.11, 0.35, 0.75),
    "shin": (0.09, 0.25, 0.7),
}


def calibrate_worn_from_body(armature):
    """人体線第一 — derive every worn size from the measured body.

    The helmet calibration generalized: chest/waist widths from torso slices
    (inside the shoulder joints so T-pose arms don't pollute the measure),
    limb diameters from bone-axis radii. Constants become a per-body result;
    physique bulks still modulate on top. Returns the measurement report."""
    pts = _body_world_verts()
    if len(pts) < 500:
        return None
    try:
        chest_z0 = bone_points(armature, "chest")[0].z
        neck_z = bone_points(armature, "neck")[0].z
        hips_z = bone_points(armature, "hips")[0].z
        shoulder_x = abs(bone_points(armature, "leftUpperArm")[0].x)
    except RuntimeError:
        return None
    report = {}
    chest = _slice_dims(pts, chest_z0, neck_z, x_limit=shoulder_x * 0.92)
    waist = _slice_dims(pts, hips_z - 0.04, hips_z + 0.05)
    # V-taper guard direction matters: the BODY is the floor. Squeezing the
    # waist below the pelvis collapses it into the hips (measured) — so the
    # taper is achieved by GROWING the chest over the hips, never by
    # shrinking the waist under the body.
    waist_w = waist[0] * _AMPLIFY["waist"]["w"] if waist else None
    if chest:
        w = chest[0] * _AMPLIFY["chest"]["w"]
        if waist_w:
            w = max(w, waist_w * V_TAPER_MIN)
        d = chest[1] * _AMPLIFY["chest"]["d"]
        # 深めの前後分割(0.74/0.62): 側壁が体側線を越えて回り込み、リフォージの
        # 剛体シフト(±30-50mm)後も脇のシームが開かない(2026-07-10 腋下・脇腹対策。
        # 0.62/0.5では胸-34mm/背+48mmシフトで側面の重なりが尽きて縦帯が露出した)
        WORN_SIZE["chest"] = (w, WORN_SIZE["chest"][1], d * 0.74)
        WORN_SIZE["back"] = (w * 0.94, WORN_SIZE["back"][1], d * 0.62)
        CLEARANCE["chest"] = 1.0
        CLEARANCE["back"] = 1.0
        report["chest_slice"] = [round(v, 3) for v in chest]
    if waist:
        WORN_SIZE["waist"] = (waist_w, WORN_SIZE["waist"][1],
                              waist[1] * _AMPLIFY["waist"]["d"])
        CLEARANCE["waist"] = 1.0
        report["waist_slice"] = [round(v, 3) for v in waist]
    limb_map = {
        "upperarm": ("leftUpperArm", "leftLowerArm"),
        "forearm": ("leftLowerArm", "leftHand"),
        "thigh": ("leftUpperLeg", "leftLowerLeg"),
        "shin": ("leftLowerLeg", "leftFoot"),
    }
    for key, (b0, b1) in limb_map.items():
        cap, t0, t1 = _LIMB_WINDOW[key]
        try:
            dia = _limb_diameter(pts, bone_points(armature, b0)[0], bone_points(armature, b1)[0],
                                 cap, t0, t1, x_side=1.0)  # left-side bones
        except RuntimeError:
            dia = None
        if not dia:
            continue
        target = dia * _AMPLIFY[key]["dia"]
        if key == "shin":
            # calves must not outgrow thighs (shin dia includes the bulge)
            target = min(target, WORN_SIZE["left_thigh"][0] * 0.96)
        for side in ("left", "right"):
            mod = f"{side}_{key}"
            WORN_SIZE[mod] = (target, WORN_SIZE[mod][1], target)
            CLEARANCE[mod] = 1.0
        report[f"{key}_dia"] = round(dia, 3)
        if key == "shin":
            # boots carry the shin line: match their width to the calf
            bw = max(WORN_SIZE["left_boot"][0], dia * 1.35)
            for side in ("left", "right"):
                WORN_SIZE[f"{side}_boot"] = (bw, WORN_SIZE[f"{side}_boot"][1],
                                             WORN_SIZE[f"{side}_boot"][2])
        if key == "upperarm":
            # heroic span: pauldrons carry the silhouette out to ~2.9 heads
            pd = dia * _AMPLIFY["shoulder"]["dia"]
            for side, sign in (("left", 1.0), ("right", -1.0)):
                mod = f"{side}_shoulder"
                WORN_SIZE[mod] = (pd, WORN_SIZE[mod][1], pd * 0.84)
                CLEARANCE[mod] = 1.0
                d0 = PLACEMENT[mod]["delta"]
                PLACEMENT[mod]["delta"] = (sign * (dia * 0.5 + pd * 0.35), d0[1], d0[2])
    # feet: the toes must live INSIDE the boot. Measure the actual foot
    # (verts below the ankle, own side only) and size/center the boot on it
    try:
        ankle = bone_points(armature, "leftFoot")[0]
        # radius guard: stray far vertices at floor level measured a 1.6m
        # foot once — everything a foot owns lives within 35cm of the ankle
        sel = [p for p in pts if p.z < ankle.z + 0.02 and p.x > 0.01
               and (p - ankle).length < 0.35]
        if len(sel) > 50:
            y0 = min(p.y for p in sel)
            y1 = max(p.y for p in sel)
            x0 = min(p.x for p in sel)
            x1 = max(p.x for p in sel)
            foot_len = y1 - y0
            foot_w = x1 - x0
            for side in ("left", "right"):
                mod = f"{side}_boot"
                WORN_SIZE[mod] = (foot_w * 1.32, WORN_SIZE[mod][1], foot_len * 1.2)
                CLEARANCE[mod] = 1.0
                d0 = PLACEMENT[mod]["delta"]
                PLACEMENT[mod]["delta"] = (d0[0], ((y0 + y1) * 0.5 - ankle.y), d0[2])
            report["foot"] = [round(foot_len, 3), round(foot_w, 3)]
    except RuntimeError:
        pass
    report["worn"] = {k: [round(x, 3) for x in v] for k, v in WORN_SIZE.items()}
    print("BODY_CALIBRATION:" + json.dumps(report))
    return report


def import_body(use_vrm_importer=False):
    imported = False
    if use_vrm_importer:
        # the VRM add-on keeps the VRM humanoid/meta extension on the armature,
        # which export_scene.vrm needs to write a valid .vrm back out.
        # bpy.ops attributes are lazy stubs: only the CALL reveals absence.
        try:
            bpy.ops.import_scene.vrm(filepath=VRM_PATH)
            imported = True
        except AttributeError:
            print("VRM_ADDON_MISSING: falling back to glTF importer")
    if not imported:
        bpy.ops.import_scene.gltf(filepath=VRM_PATH)
    armature = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
    if armature is None:
        raise RuntimeError("VRM import produced no armature")
    # tokusatsu undersuit: flatten every body material to a dark technical tone
    suit = bpy.data.materials.new("base_suit_override")
    suit.use_nodes = True
    # Blender 5.x: a fresh node tree may not contain a node NAMED
    # "Principled BSDF" — look up by type and create when missing, or the
    # undersuit silently ships as default 0.8 grey (the white-body bug)
    bsdf = next((n for n in suit.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        bsdf = suit.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        out = next((n for n in suit.node_tree.nodes if n.type == "OUTPUT_MATERIAL"), None)
        if out is None:
            out = suit.node_tree.nodes.new("ShaderNodeOutputMaterial")
        suit.node_tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    if bsdf is not None:
        # matte near-black: reference undersuits are stretch fabric, and a
        # metallic dark tone bounces the IBL back as WHITE in every render
        bsdf.inputs["Base Color"].default_value = (0.022, 0.024, 0.03, 1.0)
        if "Metallic" in bsdf.inputs:
            bsdf.inputs["Metallic"].default_value = 0.05
        if "Roughness" in bsdf.inputs:
            bsdf.inputs["Roughness"].default_value = 0.85
    for obj in bpy.data.objects:
        if obj.type == "MESH" and obj.name != "armature":
            # hair/accessory meshes are not part of the undersuit silhouette
            if "hair" in obj.name.lower() or "hair" in obj.data.name.lower():
                obj.hide_render = True
                obj.hide_set(True)
                continue
            for slot in obj.material_slots:
                slot.material = suit
    return armature


def bone_points(armature, humanoid_name):
    bone = armature.data.bones.get(BONE_NAME[humanoid_name])
    if bone is None:
        raise RuntimeError(f"bone not found: {humanoid_name}")
    head = armature.matrix_world @ bone.head_local
    tail = armature.matrix_world @ bone.tail_local
    return head, tail


def calibrate_helmet_to_head(armature):
    """「首から差し替える」サイズ規範 — target the MEASURED head, not a constant.

    The helmet reads wrong whenever it is sized like a prop: it must be the
    head plus a thin shell. Hair is already hidden with the undersuit
    override, so the bare-head bbox is the true reference. Overrides
    WORN_SIZE/CLEARANCE/PLACEMENT for the helmet in place."""
    try:
        anchor = bone_points(armature, "head")[0]
    except RuntimeError:
        return None
    depsgraph = bpy.context.evaluated_depsgraph_get()
    pts = []
    for obj in bpy.data.objects:
        if obj.type != "MESH" or obj.hide_render or obj.name.startswith("armor_"):
            continue
        ev = obj.evaluated_get(depsgraph)
        mesh = ev.to_mesh()
        mesh.transform(ev.matrix_world)
        pts.extend(v.co.copy() for v in mesh.vertices if v.co.z >= anchor.z - 0.005)
        ev.to_mesh_clear()
    if len(pts) < 100:
        return None
    mins = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    maxs = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    dims = maxs - mins
    # thin-shell margins; enclose_scale remains the safety net for intrusions.
    # Height 1.28 + seat lift 0.01: the helmet must swallow the JAW — a high
    # seat exposes the mouth like Riderman (user memo 2026-07-09)
    WORN_SIZE["helmet"] = (dims.x * 1.16, dims.z * 1.28, dims.y * 1.12)
    CLEARANCE["helmet"] = 1.0
    center = (mins + maxs) * 0.5
    PLACEMENT["helmet"]["delta"] = (
        0.0,
        (center.y - anchor.y) * -BODY_FACING,
        center.z - anchor.z + dims.z * 0.01,
    )
    report = {"head_dims_m": [round(v, 3) for v in dims],
              "helmet_worn": [round(v, 3) for v in WORN_SIZE["helmet"]]}
    print("HELMET_CALIBRATION:" + json.dumps(report))
    return report


def object_bbox(obj):
    xs = [v.co for v in obj.data.vertices]
    mins = Vector((min(v.x for v in xs), min(v.y for v in xs), min(v.z for v in xs)))
    maxs = Vector((max(v.x for v in xs), max(v.y for v in xs), max(v.z for v in xs)))
    return mins, maxs


def build_body_bvh():
    """BVH trees of every rendered body mesh (evaluated, world space)."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    trees = []
    for obj in bpy.data.objects:
        if obj.type != "MESH" or obj.hide_render or obj.name.startswith("armor_"):
            continue
        ev = obj.evaluated_get(depsgraph)
        mesh = ev.to_mesh()
        mesh.transform(ev.matrix_world)
        verts = [v.co.copy() for v in mesh.vertices]
        polys = [tuple(p.vertices) for p in mesh.polygons]
        if verts and polys:
            trees.append(BVHTree.FromPolygons(verts, polys))
        ev.to_mesh_clear()
    return trees


def _nearest_body(body_trees, point):
    """(distance, inside) to the nearest body surface across all trees."""
    best = None
    for tree in body_trees:
        hit = tree.find_nearest(point)
        if hit is None or hit[0] is None:
            continue
        location, normal, _, dist = hit
        if best is None or dist < best[0]:
            inside = (point - location).dot(normal) < 0.0
            best = (dist, inside, location, normal)
    return best


def _escapes_through_body(body_trees, point, direction, max_dist):
    """真の体内判定の裏取り: 体内の点が外向きに出るなら体表を必ず貫く。"""
    for tree in body_trees:
        hit = tree.ray_cast(point, direction, max_dist)
        if hit is not None and hit[0] is not None:
            return True
    return False


def _emissive_vert_mask(obj):
    """Vertex indices on emissive-zone faces (visor glass, glow channels).

    The face sitting inside the visor recess is DESIGN, not a fit failure —
    counting those vertices as intrusions made the helmet balloon 1.42x."""
    mesh = obj.data
    emiss = {i for i, m in enumerate(mesh.materials) if m and "emissive" in m.name}
    if not emiss:
        return None
    bad = set()
    for poly in mesh.polygons:
        if poly.material_index in emiss:
            bad.update(poly.vertices)
    return bad


def measure_clearance(module, obj, armature, body_trees, sample_step=2, skip=None,
                      z_floor=None, crotch_guard=None):
    """Robust intrusion measure: for each sampled armor vertex, find the
    nearest body point and test the sign against the body normal. Reports how
    deep the armor sinks into the body and the mean outward push needed.

    z_floor: ignore armor vertices below this world height. A helmet rim
    skirts the neck beside the shoulders — nearest-surface sign tests flag
    that airspace as 'inside the trapezius', which is a false positive.

    crotch_guard: (z_max, half_x) — ignore vertices in the between-the-legs
    strip. 脚の間の空中にある腰リング下端は最近傍が「隣の腿の内側」になり
    体内と誤判定される(内股の凹面、兜の首空域と同種の偽陽性。2026-07-10)。"""
    spec = PROBE[module]
    bpy.context.view_layer.update()
    matrix = obj.matrix_world
    normal_m = matrix.inverted_safe().transposed().to_3x3()
    verts = obj.data.vertices
    total = 0
    intrusions = 0
    max_depth = 0.0
    min_clear = 1e9
    push = Vector((0.0, 0.0, 0.0))
    in_cen = Vector((0.0, 0.0, 0.0))
    in_zmin, in_zmax = 1e9, -1e9
    for i in range(0, len(verts), max(1, sample_step)):
        if skip is not None and i in skip:
            continue
        world = matrix @ verts[i].co
        if z_floor is not None and world.z < z_floor:
            continue
        if (crotch_guard is not None and world.z < crotch_guard[0]
                and abs(world.x) < crotch_guard[1]):
            continue
        near = _nearest_body(body_trees, world)
        if near is None:
            continue
        dist, inside, _loc, normal = near
        # 内壁除外(2026-07-10): Solidify内壁など体を向く面は「見える表面」では
        # ない。外壁を突き抜ける本物の貫通は外壁頂点(法線が体法線と同向)が
        # 必ず体内に入るので検出は落ちない — 落ちるのはシェル厚未満の不可視かすりだけ
        n_v = (normal_m @ verts[i].normal)
        if n_v.length > 1e-9 and n_v.normalized().dot(normal) < -0.3:
            continue
        if inside and spec.get("crease_filter") and n_v.length > 1e-9:
            # 実在確認(2026-07-10、crease_filterフラグ制): 本当に体内なら自法線の
            # 外向きレイは体表を貫いて出る。へそ・背骨溝・臀裂・股間などの凹面を
            # 橋渡しする頂点は最近傍符号では「体内」に読めるが、外向きレイは
            # 何も叩かない(橋の下は空気)— 正中線残留の正体。
            # ※全部位に適用してはいけない: 腿では内腿の接触票が消えて coherence が
            #   跳ね上がり、rigid_shift 3連発で腿が脚上方へずり上がった(膝172mm露出)
            if not _escapes_through_body(body_trees, world, n_v.normalized(),
                                         dist * 3.0 + 0.02):
                inside = False
        total += 1
        signed = -dist if inside else dist
        if inside:
            intrusions += 1
            max_depth = max(max_depth, dist)
            push += normal  # accumulate outward direction
            in_cen += world
            in_zmin = min(in_zmin, world.z)
            in_zmax = max(in_zmax, world.z)
        min_clear = min(min_clear, signed)
    if total == 0:
        return {"measured": 0, "pass": True, "note": "no body under this part"}
    ratio = intrusions / total
    push_dir = push.normalized() if push.length > 1e-6 else Vector((0.0, -BODY_FACING, 0.0))
    # how directional the intrusion is: 1.0 = every intruding vertex wants the
    # same way out (a mis-seated plate), ~0 = surrounded (a tube on a limb)
    coherence = (push.length / intrusions) if intrusions else 0.0
    passed = ratio <= FIT_MAX_INTRUSION_RATIO and max_depth <= FIT_MAX_INTRUSION_M
    extra = {}
    if intrusions:
        # どこが痛いかを報告する(貫通の重心とz帯) — 偽陽性の切り分けに必須
        c = in_cen / intrusions
        extra = {"intrusion_centroid": [round(v, 3) for v in c],
                 "intrusion_z": [round(in_zmin, 3), round(in_zmax, 3)]}
    return {
        **extra,
        "measured": total,
        "intrusion_ratio": round(ratio, 4),
        "max_intrusion_mm": round(max_depth * 1000, 1),
        "min_clearance_mm": round(min_clear * 1000, 1),
        # reforge is driven by how deep the armor sinks in, not lack of air
        "deficit_m": max(0.0, max_depth),
        "push_dir": [round(v, 3) for v in push_dir],
        "push_coherence": round(coherence, 3),
        "pass": bool(passed),
    }


def conform_to_body(obj, module, body_trees, gap_m, relax_passes=2, skip=None, z_floor=None,
                    push_cap=None):
    """Wearable-fit reforge: push only the armor vertices that sink into the
    body out to gap_m along the body normal. Outer features (crests, horns,
    edges) already clear the body, so they are untouched. Each vertex moves at
    most its own intrusion depth — this operation cannot balloon a part.

    A light Laplacian relax on the moved vertices keeps the conformed inner
    wall smooth. Returns how many vertices were conformed and the max push."""
    bpy.context.view_layer.update()
    matrix = obj.matrix_world
    inv = matrix.inverted()
    mesh = obj.data
    moved = {}
    max_push = 0.0
    for v in mesh.vertices:
        if skip is not None and v.index in skip:
            continue
        world = matrix @ v.co
        if z_floor is not None and world.z < z_floor:
            continue
        near = _nearest_body(body_trees, world)
        if near is None:
            continue
        dist, inside, location, normal = near
        signed = -dist if inside else dist
        if signed < gap_m:
            push = (gap_m - signed)
            if push_cap is not None and push > push_cap:
                # a vertex demanding a huge shove is geometry that WANTS to
                # fold (belt pods, drape edges) — leaving it beats wrinkling
                continue
            target_world = location + normal * gap_m
            v.co = inv @ target_world
            max_push = max(max_push, push)
            moved[v.index] = True
    if moved and relax_passes:
        neighbors = {}
        for edge in mesh.edges:
            a, b = edge.vertices
            neighbors.setdefault(a, []).append(b)
            neighbors.setdefault(b, []).append(a)
        for _ in range(relax_passes):
            updates = {}
            for idx in moved:
                nbrs = neighbors.get(idx, [])
                if not nbrs:
                    continue
                avg = Vector((0.0, 0.0, 0.0))
                for n in nbrs:
                    avg += mesh.vertices[n].co
                avg /= len(nbrs)
                updates[idx] = mesh.vertices[idx].co.lerp(avg, 0.3)
            for idx, co in updates.items():
                mesh.vertices[idx].co = co
    mesh.update()
    return {"conformed_verts": len(moved), "max_push_mm": round(max_push * 1000, 1)}


def enclose_scale(obj, module, armature, body_trees, gap_m, skip=None, z_floor=None,
                  target_ratio=None):
    """Grow a closed enclosing shell (helmet) uniformly around the head until
    almost no head vertex pokes through. Uniform scale keeps the dome smooth,
    unlike per-vertex conform which would pucker a deeply-embedded dome.

    Pass rule here is RATIO ONLY: the face is supposed to sit inside the visor
    recess (that reveal is design, and it reads as metres-deep 'intrusion').
    Chasing the depth rule made helmets balloon 1.4x — the exact 頭でかい bug."""
    rule = PLACEMENT[module]
    head, _ = bone_points(armature, rule["anchor"])
    limit = FIT_MAX_INTRUSION_RATIO if target_ratio is None else target_ratio
    scale_total = 1.0
    for _ in range(6):
        report = measure_clearance(module, obj, armature, body_trees, skip=skip, z_floor=z_floor)
        ratio_ok = report.get("intrusion_ratio", 0.0) <= limit
        if ratio_ok or report.get("measured", 0) == 0:
            report["pass"] = True
            report["note"] = "enclose: ratio-only rule (visor reveal is design)"
            return report, scale_total
        bump = 1.06
        for v in obj.data.vertices:
            world = obj.matrix_world @ v.co
            grown = head + (world - head) * bump
            v.co = obj.matrix_world.inverted() @ grown
        obj.data.update()
        scale_total *= bump
        place_part(obj, module, armature)
        if scale_total > 1.7:
            break
    report = measure_clearance(module, obj, armature, body_trees, skip=skip, z_floor=z_floor)
    if report.get("intrusion_ratio", 1.0) <= FIT_MAX_INTRUSION_RATIO:
        report["pass"] = True
        report["note"] = "enclose: ratio-only rule (visor reveal is design)"
    return report, scale_total


def reforge_until_fit(body_trees, obj, module, armature):
    """適合審査ループ: measure body intrusion, then reforge to clear it.
    Closed enclosing shells (helmet) grow uniformly around the joint; every
    other plate conforms only its intruding vertices out to the air gap.
    Re-measure after each pass; converges fast because each pass only fixes the
    residue the previous relax pulled back in."""
    spec = PROBE[module]
    gap = spec["gap_m"]
    trail = []
    if spec.get("reforge") == "enclose":
        skip = _emissive_vert_mask(obj)  # visor glass verts are design reveal
        # ...and so is the WINDOW around it: the face inside the visor
        # opening reads as intrusion and conform shoves the frame outward,
        # denting the band (the nose bulge that splits wide visors). Mask
        # every vertex inside the glass's own window volume + margin.
        if skip:
            anchor_pt = bone_points(armature, PLACEMENT[module]["anchor"])[0]
            matrix = obj.matrix_world
            glass = [matrix @ obj.data.vertices[i].co for i in skip]
            zmin = min(w.z for w in glass) - 0.015
            zmax = max(w.z for w in glass) + 0.015
            def _ang(w):
                return abs(math.atan2((w.x - anchor_pt.x),
                                      (w.y - anchor_pt.y) * BODY_FACING))
            half_window = max(_ang(w) for w in glass) + math.radians(8.0)
            window = set(skip)
            for i, v in enumerate(obj.data.vertices):
                w = matrix @ v.co
                if zmin <= w.z <= zmax and _ang(w) <= half_window:
                    window.add(i)
            skip = window
        # the rim below the chin skirts the neck NEXT TO the shoulders —
        # that airspace must not be judged against the trapezius surface
        z_floor = None
        try:
            z_floor = bone_points(armature, PLACEMENT[module]["anchor"])[0].z - 0.01
        except RuntimeError:
            pass
        # Hybrid rule (measured 2026-07-09): with the head-calibrated worn
        # size, the residual intrusions are shallow cheek grazes (<=12mm at
        # +-30..60deg) — exactly what per-vertex conform is for. Uniform
        # enclose growth is reserved for GROSS misfit only; growing a snug
        # helmet to satisfy a few cheek vertices is how helmets balloon.
        total_conformed = 0
        for attempt in range(FIT_REFORGE_MAX_PASSES + 1):
            report = measure_clearance(module, obj, armature, body_trees,
                                       skip=skip, z_floor=z_floor)
            report["attempt"] = attempt
            ratio = report.get("intrusion_ratio", 0.0)
            if ratio <= FIT_MAX_INTRUSION_RATIO or report.get("measured", 0) == 0:
                report["pass"] = True
                report["note"] = "enclose-hybrid: ratio-only rule (visor reveal is design)"
                trail.append(report)
                break
            if ratio > 0.08:  # gross misfit: grow uniformly first
                after, scale_total = enclose_scale(obj, module, armature, body_trees, gap,
                                                   skip=skip, z_floor=z_floor,
                                                   target_ratio=0.08)
                report["reforge_applied"] = {"mode": "enclose",
                                             "scale_total": round(scale_total, 3)}
            else:  # shallow local grazes: push just those vertices out
                relax = 2 if attempt < 2 else 0
                applied = conform_to_body(obj, module, body_trees, gap,
                                          relax_passes=relax, skip=skip, z_floor=z_floor)
                total_conformed += applied["conformed_verts"]
                applied["mode"] = "conform"
                report["reforge_applied"] = applied
                report["total_conformed"] = total_conformed
            trail.append(report)
        return trail
    # 股間ガード: 全周リング(腰)の下端は脚の間の空中を通る — そこを審査しない
    crotch = None
    if spec.get("crotch_guard"):
        try:
            crotch = (bone_points(armature, "hips")[0].z - 0.03, 0.10)
        except RuntimeError:
            pass
    # Stage 0 — rigid reseat: a deep intrusion whose escape directions agree
    # is a mis-seated plate (bbox recentering digs the inner wall into the
    # body when layered fronts deepen the part). Cosplay logic applies: move
    # the whole breastplate outward, never crush its layer stack.
    for rigid_pass in range(3):
        report = measure_clearance(module, obj, armature, body_trees,
                                   crotch_guard=crotch)
        deficit = report.get("deficit_m", 0.0)
        coherence = report.get("push_coherence", 0.0)
        if (report.get("pass") or report.get("measured", 0) == 0
                or deficit < gap * 1.5 or coherence < 0.55):
            break
        shift = Vector(report["push_dir"]) * min(0.06, deficit * 0.9)
        obj.matrix_world.translation += shift
        bpy.context.view_layer.update()
        report["attempt"] = f"rigid{rigid_pass}"
        report["reforge_applied"] = {"mode": "rigid_shift",
                                     "shift_mm": [round(v * 1000, 1) for v in shift]}
        trail.append(report)
    total_conformed = 0
    prev_ratio = None
    rescues = 0
    for attempt in range(FIT_REFORGE_MAX_PASSES + 1):
        report = measure_clearance(module, obj, armature, body_trees,
                                   crotch_guard=crotch)
        report["attempt"] = attempt
        report["total_conformed"] = total_conformed
        # a part with a push cap DECIDED not to move its fold-prone verts —
        # judge it on ratio alone, like the visor reveal.
        # per-part max_ratio: 密着リングは縁(木口)頂点が構造的に
        # 「シェル厚ぶん体内」に読める(内壁除外・実在確認レイでも残る、
        # レンダ不可視 — 2026-07-10に貫通重心で特定)
        if (spec.get("push_cap")
                and report.get("intrusion_ratio", 1.0)
                    <= spec.get("max_ratio", FIT_MAX_INTRUSION_RATIO)):
            report["pass"] = True
            report["note"] = "push_cap: ratio-only rule"
        trail.append(report)
        if report.get("pass") or report.get("measured", 0) == 0:
            break
        ratio = report.get("intrusion_ratio", 0.0)
        deficit = report.get("deficit_m", 0.0)
        cap = spec.get("push_cap")
        # 膠着レスキュー: capped conform は cap より深い貫通を原理的に消せない。
        # 改善が止まったら(前回比85%未満に縮んでいない)平均脱出方向へ剛体シフト。
        # coherence 条件は問わない — 膠着時点で他に打つ手がない(2026-07-10:
        # 乱数違いの腰が coherence 0.48 で第0段を逃し 4.6%/28.8mm で5パス膠着した)
        if (rescues < 2 and prev_ratio is not None and cap
                and deficit > cap and ratio > prev_ratio * 0.85):
            shift = Vector(report["push_dir"]) * min(0.04, deficit * 0.9)
            obj.matrix_world.translation += shift
            bpy.context.view_layer.update()
            check = measure_clearance(module, obj, armature, body_trees,
                                      crotch_guard=crotch)
            if check.get("intrusion_ratio", 1.0) > ratio * 0.85:
                # 締まり嵌め(全周リング)は動かすと反対側が食う — 戻して打ち切り
                # (2026-07-10実測: 腰を+26mm上げたら上端が腹へ同量食い込んだ)
                obj.matrix_world.translation -= shift
                bpy.context.view_layer.update()
                rescues = 99
                report["reforge_applied"] = {"mode": "rigid_rescue_rolled_back",
                                             "shift_mm": [round(v * 1000, 1) for v in shift]}
            else:
                rescues += 1
                report["reforge_applied"] = {"mode": "rigid_rescue",
                                             "shift_mm": [round(v * 1000, 1) for v in shift]}
            prev_ratio = ratio
            continue
        prev_ratio = ratio
        # final passes tighten with no relax so residual pockets fully clear
        relax = 2 if attempt < 2 else 0
        applied = conform_to_body(obj, module, body_trees, gap, relax_passes=relax,
                                  push_cap=cap)
        total_conformed += applied["conformed_verts"]
        report["reforge_applied"] = applied
    return trail


def world_bbox(obj):
    bpy.context.view_layer.update()
    matrix = obj.matrix_world
    ws = [matrix @ v.co for v in obj.data.vertices]
    mins = Vector((min(v.x for v in ws), min(v.y for v in ws), min(v.z for v in ws)))
    maxs = Vector((max(v.x for v in ws), max(v.y for v in ws), max(v.z for v in ws)))
    return mins, maxs


def _axis_extent(obj, origin, axis):
    bpy.context.view_layer.update()
    matrix = obj.matrix_world
    projections = [(matrix @ v.co - origin).dot(axis) for v in obj.data.vertices]
    return min(projections), max(projections)


def mesh_audit(obj):
    """メッシュ検品 — the fit audit's sibling for GEOMETRY quality.

    Counts what makes a mesh bad downstream: degenerate faces (zero area),
    sliver triangles (quality = 4*sqrt(3)*A / sum(edge^2), 1.0 = equilateral),
    zero-length edges, non-manifold edges (>2 faces) and loose vertices.
    Boundary edges are reported separately — open shells legitimately have
    them. Report-only: measurement precedes rules."""
    mesh = obj.data
    mesh.calc_loop_triangles()
    degenerate = 0
    sliver = 0
    tri_count = len(mesh.loop_triangles)
    verts = mesh.vertices
    for tri in mesh.loop_triangles:
        a = verts[tri.vertices[0]].co
        b = verts[tri.vertices[1]].co
        c = verts[tri.vertices[2]].co
        ab = b - a
        ac = c - a
        area = ab.cross(ac).length * 0.5
        if area < 1e-9:
            degenerate += 1
            continue
        l2 = ab.length_squared + ac.length_squared + (c - b).length_squared
        if l2 > 1e-12 and (6.928203230275509 * area / l2) < 0.05:
            sliver += 1
    bm = bmesh.new()
    bm.from_mesh(mesh)
    zero_edges = 0
    boundary = 0
    nonmanifold = 0
    for e in bm.edges:
        n = len(e.link_faces)
        if n == 1:
            boundary += 1
        elif n > 2:
            nonmanifold += 1
        if e.calc_length() < 1e-6:
            zero_edges += 1
    loose_verts = sum(1 for v in bm.verts if not v.link_faces)
    bm.free()
    return {
        "triangles": tri_count,
        "vertices": len(verts),
        "degenerate_faces": degenerate,
        "sliver_faces": sliver,
        "zero_length_edges": zero_edges,
        "boundary_edges": boundary,
        "nonmanifold_edges": nonmanifold,
        "loose_vertices": loose_verts,
    }


_CULL_TILT = 0.7  # ray fan spread: normal +- ~35deg


def cull_hidden_faces(obj, body_trees, max_dist=0.05):
    """隠れ面カリング — delete faces no light path can reach.

    The layered costume construction (plates over shells, studs on plates,
    solidified inner walls around a worn body) ships faces that are never
    visible. A face is culled only when ALL 7 probe rays (surface normal plus
    a tilted fan) hit geometry — its own part or the body — within max_dist.
    One escaping ray keeps the face: vents, grooves and visor recesses stay
    because their normal ray exits through the opening."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    ev = obj.evaluated_get(depsgraph)
    mesh_eval = ev.to_mesh()
    mesh_eval.transform(ev.matrix_world)
    self_bvh = BVHTree.FromPolygons(
        [v.co.copy() for v in mesh_eval.vertices],
        [tuple(p.vertices) for p in mesh_eval.polygons])
    ev.to_mesh_clear()

    matrix = obj.matrix_world
    nmat = matrix.to_3x3().inverted_safe().transposed()
    mesh = obj.data
    # emissive surfaces (visor glass, glow strips) are design statements that
    # sit in deep recesses by construction — and their RECESS WALLS face each
    # other, so every probe ray is blocked and the whole pit gets eaten,
    # leaving see-through holes around the glass (measured on patrol-01).
    # Exempt the emissive faces plus a 2-ring dilation around them.
    emissive_idx = builder.ZONE_ORDER.index("emissive")
    protected_verts = set()
    for poly in mesh.polygons:
        if poly.material_index == emissive_idx:
            protected_verts.update(poly.vertices)
    exempt = set()
    for _ in range(2):
        grown = set(protected_verts)
        for poly in mesh.polygons:
            if poly.index in exempt:
                continue
            if any(v in protected_verts for v in poly.vertices):
                exempt.add(poly.index)
                grown.update(poly.vertices)
        protected_verts = grown
    hidden = []
    for poly in mesh.polygons:
        if poly.material_index == emissive_idx or poly.index in exempt:
            continue
        center = matrix @ poly.center
        n = (nmat @ poly.normal)
        if n.length < 1e-9:
            continue
        n.normalize()
        u = n.cross(Vector((0.0, 0.0, 1.0)))
        if u.length < 1e-6:
            u = n.cross(Vector((1.0, 0.0, 0.0)))
        u.normalize()
        v = n.cross(u)
        origin = center + n * 0.0015
        covered = True
        for d in (n,
                  (n + u * _CULL_TILT).normalized(), (n - u * _CULL_TILT).normalized(),
                  (n + v * _CULL_TILT).normalized(), (n - v * _CULL_TILT).normalized(),
                  (n + (u + v) * 0.5).normalized(), (n - (u + v) * 0.5).normalized()):
            loc = self_bvh.ray_cast(origin, d, max_dist)[0]
            if loc is None:
                blocked = False
                for tree in body_trees:
                    if tree.ray_cast(origin, d, max_dist)[0] is not None:
                        blocked = True
                        break
                if not blocked:
                    covered = False
                    break
        if covered:
            hidden.append(poly.index)
    if not hidden:
        return 0
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.faces[i] for i in hidden], context="FACES")
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return len(hidden)


def cleanup_mesh(obj):
    """退化ジオメトリ掃除 — dissolve what the audit flagged, and nothing more.

    dissolve_degenerate at 0.12mm kills zero-area faces / zero-length edges
    from conform crushes; loose vertices left behind are swept afterwards.
    The intentional double rows at feature borders sit ~2mm apart, an order
    of magnitude above the threshold.

    MEASURED LESSON (2026-07-09): do NOT add dissolve_limit here. Subsurf
    output steps only ~0.2deg per face on smooth curvature, so even a 0.5deg
    coplanar merge flattens visor recesses and collars into ngon shards.
    Sliver reduction belongs upstream (band injection widths), not here."""
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    before = len(bm.faces)
    # protect the emissive glass boundary: conform skips glass verts while
    # pushing their frame neighbours, leaving sub-0.12mm edges there BY
    # DESIGN — dissolving them merges glass into frame and the visor
    # collapses into grey pits (measured on patrol-01)
    emissive_idx = builder.ZONE_ORDER.index("emissive")
    protected = set()
    for f in bm.faces:
        if f.material_index == emissive_idx:
            protected.update(v.index for v in f.verts)
    edges = [e for e in bm.edges
             if e.verts[0].index not in protected and e.verts[1].index not in protected]
    bmesh.ops.dissolve_degenerate(bm, dist=0.00012, edges=edges)
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
    removed = before - len(bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    return removed


ADJACENT_PAIRS = [
    # chest~back is DESIGNED side overlap (two half-shells forming one torso)
    ("chest", "waist"),
    ("chest", "left_shoulder"), ("chest", "right_shoulder"),
    ("left_shoulder", "left_upperarm"), ("right_shoulder", "right_upperarm"),
    ("waist", "left_thigh"), ("waist", "right_thigh"),
    ("left_thigh", "left_shin"), ("right_thigh", "right_shin"),
]


def audit_part_overlaps(objs_by_module):
    """部品間適合審査 — parts must not run through EACH OTHER.

    Fit audit guards armor-vs-body; costume truth also demands armor-vs-armor
    clearance (a suit that self-intersects cannot exist, and the eye reads
    the overlap as fake). Measures interpenetration for adjacent pairs the
    same way: nearest point + normal sign. Report-first; the resolution
    (prescribed layering + trimming the under part) is the next stage."""
    depsgraph = bpy.context.evaluated_depsgraph_get()
    trees = {}
    for module, obj in objs_by_module.items():
        ev = obj.evaluated_get(depsgraph)
        mesh = ev.to_mesh()
        mesh.transform(ev.matrix_world)
        verts = [v.co.copy() for v in mesh.vertices]
        polys = [tuple(p.vertices) for p in mesh.polygons]
        if verts and polys:
            trees[module] = (BVHTree.FromPolygons(verts, polys), verts)
        ev.to_mesh_clear()
    out = {}
    for a, b in ADJACENT_PAIRS:
        if a not in trees or b not in trees:
            continue
        tree_b = trees[b][0]
        verts_a = trees[a][1]
        inside = 0
        max_depth = 0.0
        total = 0
        for i in range(0, len(verts_a), 6):
            p = verts_a[i]
            hit = tree_b.find_nearest(p)
            if hit is None or hit[0] is None:
                continue
            loc, normal, _, dist = hit
            total += 1
            if (p - loc).dot(normal) < 0.0:
                inside += 1
                max_depth = max(max_depth, dist)
        if total:
            out[f"{a}~{b}"] = {"ratio": round(inside / total, 4),
                               "max_mm": round(max_depth * 1000, 1)}
    return out


def audit_torso_coverage(objs_by_module, armature):
    """胴の被覆審査 — 腋下・脇腹の隙間を実測する(2026-07-10ユーザー指摘)。

    体表の頂点から法線方向へレイを飛ばし、9cm以内に胴装甲(chest/back/waist)が
    無ければ「未被覆」。帯(腋下/脇腹)ごとに未被覆率と最大連続未被覆角を報告。
    関節の逃げは仕様だが、胴の側面が縦一本空くのは衣装として嘘 — 数値で見張る。"""
    try:
        ua_z = bone_points(armature, "leftUpperArm")[0].z
        chest_z = bone_points(armature, "chest")[0].z
        hips_z = bone_points(armature, "hips")[0].z
        shoulder_x = abs(bone_points(armature, "leftUpperArm")[0].x)
    except RuntimeError:
        return {}
    depsgraph = bpy.context.evaluated_depsgraph_get()
    trees = []
    for module in ("chest", "back", "waist"):
        obj = objs_by_module.get(module)
        if obj is None:
            continue
        ev = obj.evaluated_get(depsgraph)
        mesh = ev.to_mesh()
        mesh.transform(ev.matrix_world)
        verts = [v.co.copy() for v in mesh.vertices]
        polys = [tuple(p.vertices) for p in mesh.polygons]
        if verts and polys:
            trees.append(BVHTree.FromPolygons(verts, polys))
        ev.to_mesh_clear()
    if not trees:
        return {}
    bands = {
        "armpit": (ua_z - 0.10, ua_z - 0.02),   # 腋の直下=上部肋側
        "flank": (hips_z + 0.06, chest_z),       # 脇腹(腰上〜胸骨下)
    }
    samples = []
    for obj in bpy.data.objects:
        if obj.type != "MESH" or obj.hide_render or obj.name.startswith("armor_"):
            continue
        ev = obj.evaluated_get(depsgraph)
        mesh = ev.to_mesh()
        mesh.transform(ev.matrix_world)
        for v in mesh.vertices:
            samples.append((v.co.copy(), v.normal.copy()))
        ev.to_mesh_clear()
    out = {}
    for band, (z0, z1) in bands.items():
        bins = {}
        for i in range(0, len(samples), 2):
            p, n = samples[i]
            # 腕の頂点を除外(T-poseの腕は肩関節より外)
            if not (z0 <= p.z <= z1) or abs(p.x) > shoulder_x * 0.92:
                continue
            covered = False
            for t in trees:
                hit = t.ray_cast(p + n * 0.002, n, 0.09)
                if hit and hit[0] is not None:
                    covered = True
                    break
            ang = int(math.degrees(math.atan2(p.x, -p.y)) // 5) * 5  # 前=0°
            tot, unc = bins.get(ang, (0, 0))
            bins[ang] = (tot + 1, unc + (0 if covered else 1))
        if not bins:
            continue
        total = sum(t for t, _ in bins.values())
        uncov = sum(u for _, u in bins.values())
        degs = sorted(bins.keys())
        flags = [bins[d][1] / bins[d][0] > 0.5 for d in degs]
        max_run = run = 0
        for f in flags + flags:  # 円環走査
            run = run + 5 if f else 0
            max_run = max(max_run, run)
        out[band] = {"uncovered_ratio": round(uncov / max(1, total), 4),
                     "max_gap_arc_deg": min(max_run, 360)}
    return out


def audit_joint_gaps(objs_by_module, armature):
    """Undersuit reveal between adjacent plates, measured along the limb
    axis (T-pose safe: arms are probed on X, legs on -Z, torso on Z)."""
    gaps = {}
    for joint, (upper, lower, chain_anchor, lo, hi) in JOINT_GAP_TARGETS_M.items():
        a = objs_by_module.get(upper)
        b = objs_by_module.get(lower)
        if a is None or b is None:
            continue
        if chain_anchor:
            head, _ = bone_points(armature, chain_anchor)
            nxt = NEXT_JOINT.get(chain_anchor)
            tail = bone_points(armature, nxt)[0] if nxt else head + Vector((0, 0, -0.1))
            axis = (tail - head).normalized()
            a_far = _axis_extent(a, head, axis)[1]
            b_near = _axis_extent(b, head, axis)[0]
            gap = round(b_near - a_far, 4)
        else:
            gap = round(world_bbox(a)[0].z - world_bbox(b)[1].z, 4)
        gaps[joint] = {"gap_m": gap, "target": [lo, hi], "pass": lo <= gap <= hi}
    return gaps


# physique group per module: which blueprint bulk multiplier applies
_PHYSIQUE_GROUP = {
    "helmet": "helmet_bulk",
    "chest": "torso_bulk", "back": "torso_bulk", "waist": "torso_bulk",
    "left_shoulder": "shoulder_bulk", "right_shoulder": "shoulder_bulk",
}


def _bulk_for(module: str, physique: dict | None) -> float:
    if not physique:
        return 1.0
    group = _PHYSIQUE_GROUP.get(module, "limb_bulk")
    try:
        return float(physique.get(group, 1.0))
    except (TypeError, ValueError):
        return 1.0


def scale_to_worn(obj, module, physique=None):
    """Scale by the SHELL contract (authored envelope -> worn), never by the
    measured bbox.

    MEASURED LESSON (chuuni-6, 2026-07-09): bbox normalization silently
    crushed every crest, horn and wing INTO the worn box — six different
    blueprints converged to one silhouette and only the colors differed.
    Features are silhouette; they are ALLOWED to exceed the worn box. The
    fit audit still guards the body, enclose still guards the head."""
    worn = WORN_SIZE[module]
    clearance = CLEARANCE.get(module, CLEARANCE["default"])
    bulk = _bulk_for(module, physique)
    env = builder.envelope_for(module)  # authored shell contract (x, h, d)
    sx = worn[0] * clearance * bulk / max(env[0], 1e-9)
    sy = worn[2] * clearance * bulk / max(env[2], 1e-9)
    sz = worn[1] / max(env[1], 1e-9)
    for v in obj.data.vertices:
        v.co.x *= sx
        v.co.y *= sy
        v.co.z *= sz
    obj.data.update()


LIMB_REVEAL_M = 0.018  # undersuit reveal reserved at each end of a limb plate


def fit_limb_length(obj, module, armature):
    """Rule: limb plate length = joint span - 2 * LIMB_REVEAL_M."""
    rule = PLACEMENT[module]
    if rule["mode"] != "along":
        return
    head, _ = bone_points(armature, rule["anchor"])
    nxt = NEXT_JOINT.get(rule["anchor"])
    if not nxt:
        return
    tail, _ = bone_points(armature, nxt)
    span = (tail - head).length - 2.0 * LIMB_REVEAL_M
    if span <= 0.02:
        return
    mins, maxs = object_bbox(obj)
    height = maxs.z - mins.z
    if height <= 1e-6:
        return
    factor = span / height
    center_z = (mins.z + maxs.z) * 0.5
    for v in obj.data.vertices:
        v.co.z = center_z + (v.co.z - center_z) * factor
    obj.data.update()


def place_part(obj, module, armature):
    rule = PLACEMENT[module]
    head, tail = bone_points(armature, rule["anchor"])
    mins, maxs = object_bbox(obj)
    center = (mins + maxs) * 0.5

    base_rot = math.pi if BODY_FACING > 0 else 0.0
    if rule.get("rotate_z_deg"):
        base_rot += math.radians(rule["rotate_z_deg"])

    delta = Vector(rule.get("delta", (0.0, 0.0, 0.0)))
    delta = Vector((delta.x, delta.y * -BODY_FACING, delta.z))

    debug = {"module": module, "mode": rule["mode"],
             "part_dims": [round(v, 3) for v in (maxs - mins)]}

    if rule["mode"] == "along":
        next_joint = NEXT_JOINT.get(rule["anchor"])
        if next_joint:
            tail, _ = bone_points(armature, next_joint)
        axis = tail - head
        length = axis.length
        if length < 0.02:
            key = "leg" if "Leg" in BONE_NAME[rule["anchor"]] else ("left" if module.startswith("left") else "right")
            axis = _FALLBACK_AXIS[key].copy()
            length = maxs.z - mins.z
        else:
            axis = axis / length
        quat = Vector((0.0, 0.0, 1.0)).rotation_difference(axis)
        obj.rotation_euler = quat.to_euler()
        mid = (head + tail) * 0.5 if length >= 0.02 else head + axis * length * 0.5
        obj.location = mid - (quat.to_matrix() @ center) + delta
        debug["bone_len"] = round(length, 3)
    elif rule["mode"] == "foot":
        obj.rotation_euler = Euler((0.0, 0.0, base_rot))
        loc = head - center + delta
        loc.z = -mins.z + 0.004  # sole on the ground
        obj.location = loc
    else:  # center
        obj.rotation_euler = Euler((0.0, 0.0, base_rot))
        obj.location = head - center + delta
    return debug


def studio(scene_center, size, palette):
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE"
    except TypeError:
        pass
    scene.render.resolution_x = 720
    scene.render.resolution_y = 1280
    world = scene.world or bpy.data.worlds.new("abp_world")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg is not None:
        bg.inputs[0].default_value = (0.035, 0.045, 0.06, 1.0)
    # honest lighting: 300W washed dark gloss to grey and made every palette
    # judgement a lie — the render must show what the DATA says
    key = bpy.data.objects.new("lab_key", bpy.data.lights.new("lab_key", "AREA"))
    key.data.energy = 170.0
    key.data.size = 2.4
    key.location = scene_center + Vector((1.6, -2.2, 1.6))
    key.rotation_euler = (scene_center - key.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(key)
    rim = bpy.data.objects.new("lab_rim", bpy.data.lights.new("lab_rim", "AREA"))
    rim.data.energy = 110.0
    rim.data.size = 2.0
    rim.data.color = builder._hex_rgba(palette.get("emissive", "#3AC7FF"))[:3]
    rim.location = scene_center + Vector((-1.8, 1.6, 1.9))
    rim.rotation_euler = (scene_center - rim.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(rim)
    fill = bpy.data.objects.new("lab_fill", bpy.data.lights.new("lab_fill", "AREA"))
    fill.data.energy = 90.0
    fill.data.size = 3.0
    fill.location = scene_center + Vector((-0.6, -2.4, 0.2))
    fill.rotation_euler = (scene_center - fill.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(fill)


def render_views(out_dir, label, body_height):
    scene = bpy.context.scene
    center = Vector((0.0, 0.0, body_height * 0.52))
    cam_data = bpy.data.cameras.new("lab_cam")
    cam = bpy.data.objects.new("lab_cam", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    scene.camera = cam
    dist = body_height * 1.9
    views = {
        "front": Vector((0.0, -dist, body_height * 0.55)),
        "three_quarter": Vector((dist * 0.62, -dist * 0.72, body_height * 0.58)),
        "side": Vector((dist, 0.0, body_height * 0.55)),
        # rear gear (scabbards, tanks, thrusters, light bars) lives here —
        # a suit evaluated only from the front hides half its story
        "back": Vector((0.0, dist, body_height * 0.55)),
    }
    paths = {}
    for name, loc in views.items():
        cam.location = loc
        cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
        path = os.path.join(out_dir, f"{label}_{name}.png")
        scene.render.filepath = path
        bpy.ops.render.render(write_still=True)
        paths[name] = path
    return paths


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
    blueprint_path = os.path.abspath(str(args.get("blueprint", "")))
    out_dir = os.path.abspath(str(args.get("out-dir", "output/blueprint-armor/fullbody")))
    quality = str(args.get("quality", "preview"))
    label = str(args.get("label", "suit"))
    with open(blueprint_path, encoding="utf-8") as fh:
        blueprint = json.load(fh)

    want_vrm = bool(args.get("export-vrm"))
    builder.reset_scene()
    armature = import_body(use_vrm_importer=want_vrm)
    palette = dict(blueprint.get("palette") or {})

    body_trees = build_body_bvh()
    helmet_cal = calibrate_helmet_to_head(armature)
    body_cal = calibrate_worn_from_body(armature)
    placed = []
    objs_by_module = {}
    cull = str(args.get("cull-hidden", "1")).lower() not in ("0", "false")
    for module in ALL_MODULES:
        obj, spec, part_bp, mirrored = builder.build_part_object(blueprint, module, quality, unwrap=False)
        scale_to_worn(obj, module, blueprint.get("physique"))
        fit_limb_length(obj, module, armature)
        info = place_part(obj, module, armature)
        info["fit_audit"] = reforge_until_fit(body_trees, obj, module, armature)
        if cull:
            try:
                info["culled_hidden_faces"] = cull_hidden_faces(obj, body_trees)
            except Exception as exc:  # noqa: BLE001 — culling must never kill a build
                print(f"CULL_FAILED {module}: {exc}")
        if str(args.get("cleanup-mesh", "1")).lower() not in ("0", "false"):
            try:
                info["cleaned_faces"] = cleanup_mesh(obj)
            except Exception as exc:  # noqa: BLE001
                print(f"CLEANUP_FAILED {module}: {exc}")
        try:
            info["mesh_audit"] = mesh_audit(obj)
        except Exception as exc:  # noqa: BLE001
            print(f"MESH_AUDIT_FAILED {module}: {exc}")
        info["triangles"] = sum(max(0, len(p.vertices) - 2) for p in obj.data.polygons)
        placed.append(info)
        objs_by_module[module] = obj
    joint_gaps = audit_joint_gaps(objs_by_module, armature)
    part_overlaps = audit_part_overlaps(objs_by_module)
    print("PART_OVERLAPS:" + json.dumps(part_overlaps))
    torso_coverage = audit_torso_coverage(objs_by_module, armature)
    print("TORSO_COVERAGE:" + json.dumps(torso_coverage))
    mesh_summary = {
        "culled_hidden_faces": sum(p.get("culled_hidden_faces", 0) for p in placed),
        "cleaned_faces": sum(p.get("cleaned_faces", 0) for p in placed),
        "triangles_after_cull": sum(p.get("triangles", 0) for p in placed),
        "degenerate_faces": sum((p.get("mesh_audit") or {}).get("degenerate_faces", 0) for p in placed),
        "sliver_faces": sum((p.get("mesh_audit") or {}).get("sliver_faces", 0) for p in placed),
        "nonmanifold_edges": sum((p.get("mesh_audit") or {}).get("nonmanifold_edges", 0) for p in placed),
        "zero_length_edges": sum((p.get("mesh_audit") or {}).get("zero_length_edges", 0) for p in placed),
        "loose_vertices": sum((p.get("mesh_audit") or {}).get("loose_vertices", 0) for p in placed),
    }
    print("MESH_AUDIT_SUMMARY:" + json.dumps(mesh_summary))

    body_height = 1.74
    studio(Vector((0.0, 0.0, body_height * 0.5)), body_height, palette)
    os.makedirs(out_dir, exist_ok=True)
    views = render_views(out_dir, label, body_height)

    blend_path = ""
    if args.get("save-blend"):
        # interactive mockup: open this in Blender and orbit the whole suit
        blend_path = os.path.join(out_dir, f"{label}.assembly.blend")
        bpy.ops.wm.save_as_mainfile(filepath=blend_path, copy=True)

    glb_path = ""
    if args.get("export-glb"):
        # whole assembled suit + body as one GLB for the browser orbit viewer
        glb_path = os.path.join(out_dir, f"{label}.assembly.glb")
        bpy.ops.object.select_all(action="DESELECT")
        for o in bpy.data.objects:
            if o.type == "MESH" and not o.hide_render:
                o.select_set(True)
        bpy.ops.export_scene.gltf(filepath=glb_path, export_format="GLB",
                                  use_selection=True, export_apply=True,
                                  export_yup=True, export_materials="EXPORT")

    # LOD chain: decimated companions for crowded scenes / weaker devices.
    # Runs on COPIES before rigging/VRM (those paths mutate the armor objects)
    lods = {}
    if args.get("export-lods") and glb_path:
        try:
            ratios = [float(x) for x in str(args.get("export-lods")).split(",") if x.strip()]
        except ValueError:
            ratios = []
        for li, ratio in enumerate(ratios, start=1):
            copies = []
            for obj in objs_by_module.values():
                c = obj.copy()
                c.data = obj.data.copy()
                bpy.context.scene.collection.objects.link(c)
                mod = c.modifiers.new("lod", "DECIMATE")
                mod.ratio = max(0.02, min(1.0, ratio))
                bpy.ops.object.select_all(action="DESELECT")
                c.select_set(True)
                bpy.context.view_layer.objects.active = c
                try:
                    bpy.ops.object.modifier_apply(modifier="lod")
                except RuntimeError as exc:
                    print(f"LOD_DECIMATE_SKIP {c.name}: {exc}")
                copies.append(c)
            lod_path = os.path.join(out_dir, f"{label}.lod{li}.glb")
            bpy.ops.object.select_all(action="DESELECT")
            for o in bpy.data.objects:
                if o.type == "MESH" and not o.hide_render and o not in objs_by_module.values():
                    o.select_set(True)
            for obj in objs_by_module.values():
                obj.select_set(False)  # full-res armor stays out of the LOD file
            for c in copies:
                c.select_set(True)
            bpy.ops.export_scene.gltf(filepath=lod_path, export_format="GLB",
                                      use_selection=True, export_apply=True,
                                      export_yup=True, export_materials="EXPORT")
            tris = sum(max(0, len(p.vertices) - 2) for c in copies for p in c.data.polygons)
            lods[f"lod{li}"] = {"path": lod_path, "ratio": ratio, "armor_triangles": tris}
            for c in copies:
                bpy.data.objects.remove(c, do_unlink=True)
        if lods:
            print("LOD_CHAIN:" + json.dumps({k: {"ratio": v["ratio"], "tris": v["armor_triangles"]}
                                             for k, v in lods.items()}))

    skinned_path = ""
    vrm_path = ""
    if args.get("export-skinned-glb") or want_vrm:
        # rig every plate to its anchor bone so the suit is poseable
        for module, obj in objs_by_module.items():
            rigid_skin_to_armature(obj, module, armature)
        if args.get("export-skinned-glb"):
            skinned_path = os.path.join(out_dir, f"{label}.skinned.glb")
            bpy.ops.object.select_all(action="DESELECT")
            armature.select_set(True)
            for o in bpy.data.objects:
                if o.type == "MESH" and not o.hide_render:
                    o.select_set(True)
            bpy.ops.export_scene.gltf(filepath=skinned_path, export_format="GLB",
                                      use_selection=True, export_apply=True,
                                      export_yup=True, export_materials="EXPORT",
                                      export_skins=True, export_rest_position_armature=True)
        if want_vrm:
            vrm_path = os.path.join(out_dir, f"{label}.vrm")
            # -- web-metaverse compatibility pass --------------------------
            # A 770k-tri / VRM1-only / onlyAuthor-meta avatar renders as an
            # error placeholder (red box) on most services. Three fixes:
            # 1) decimate the armor to an avatar poly budget (VRM file only —
            #    the GLBs above keep full detail)
            budget = 90000
            try:
                budget = int(str(args.get("vrm-budget-tris", "")) or 90000)
            except ValueError:
                pass
            armor_tris = sum(sum(max(0, len(p.vertices) - 2) for p in o.data.polygons)
                             for o in objs_by_module.values())
            decim = {"armor_tris": armor_tris, "budget": budget, "ratio": 1.0}
            if armor_tris > budget:
                ratio = max(0.02, budget / max(1, armor_tris))
                decim["ratio"] = round(ratio, 4)
                for o in objs_by_module.values():
                    mod = o.modifiers.new("vrm_decimate", "DECIMATE")
                    mod.ratio = ratio
                    bpy.ops.object.select_all(action="DESELECT")
                    o.select_set(True)
                    bpy.context.view_layer.objects.active = o
                    try:
                        bpy.ops.object.modifier_apply(modifier="vrm_decimate")
                    except RuntimeError as exc:
                        print(f"VRM_DECIMATE_SKIP {o.name}: {exc}")
            print("VRM_PORTABLE:" + json.dumps(decim))
            # 2) match the WORKING VRoid profile (diffed 2026-07-09):
            #    - one armor mesh / few skins, not 18 separate skins
            #    - every material MToon, never VRM_USE_GLTFSHADER
            #    - a thumbnail in meta.texture (statistics readers choke
            #      without it)
            armor_objs = [o for o in objs_by_module.values() if o and o.name in bpy.data.objects]
            suit_obj = armor_objs[0] if armor_objs else None
            if len(armor_objs) > 1:
                bpy.ops.object.select_all(action="DESELECT")
                for o in armor_objs:
                    o.select_set(True)
                bpy.context.view_layer.objects.active = armor_objs[0]
                bpy.ops.object.join()
                suit_obj = bpy.context.view_layer.objects.active
                suit_obj.name = "armor_suit"
            # avatar optimizers atlas textures by UV — a mesh without
            # TEXCOORD_0 hard-fails them (「UVアトリビュートが存在しません」).
            # Assembly builds parts with unwrap=False for speed, so unwrap
            # the joined (already decimated) suit once, here only.
            if suit_obj is not None and not suit_obj.data.uv_layers:
                builder.smart_uv(suit_obj)
                print(f"VRM_UV_UNWRAPPED: {suit_obj.name}")
            mats = {slot.material for o in bpy.data.objects if o.type == "MESH" and not o.hide_render
                    for slot in o.material_slots if slot.material}
            converted = sum(1 for m in mats if _mtoonify_material(m))
            print(f"MTOON_CONVERTED: {converted}/{len(mats)}")
            ext = getattr(armature.data, "vrm_addon_extension", None)
            if ext is not None:
                _apply_vrm_meta(ext, label)
                try:
                    thumb_src = views.get("front") if isinstance(views, dict) else None
                    if thumb_src and os.path.exists(thumb_src):
                        thumb = bpy.data.images.load(thumb_src)
                        thumb.scale(512, 512)
                        thumb.name = f"{label}_thumbnail"
                        ext.vrm0.meta.texture = thumb
                except Exception as exc:  # noqa: BLE001
                    print(f"VRM_THUMBNAIL_FAILED: {exc}")
                # 3) export as VRM 0.x, which every service parses
                try:
                    ext.spec_version = "0.0"
                except Exception as exc:  # noqa: BLE001
                    print(f"VRM0_SWITCH_FAILED (exporting as-is): {exc}")
            try:
                bpy.ops.export_scene.vrm(filepath=vrm_path)
            except Exception as exc:  # noqa: BLE001
                print(f"VRM_EXPORT_FAILED: {exc}")
                vrm_path = ""
            # keep validation copies OUTSIDE the git repo (user's VRM bench)
            if vrm_path:
                mirror_dir = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "VRM"))
                if os.path.isdir(mirror_dir):
                    import shutil
                    dest = os.path.join(mirror_dir, os.path.basename(vrm_path))
                    shutil.copy2(vrm_path, dest)
                    print("VRM_MIRRORED:" + dest)

    parts_pass = sum(1 for p in placed if p["fit_audit"][-1].get("pass"))
    joints_pass = sum(1 for v in joint_gaps.values() if v["pass"])
    summary = {"ok": True, "label": label, "quality": quality,
               "blueprint": blueprint.get("blueprint_id", ""),
               "views": views, "blend": blend_path, "glb": glb_path,
               "skinned_glb": skinned_path, "vrm": vrm_path,
               "helmet_calibration": helmet_cal,
               "body_calibration": body_cal,
               "part_overlaps": part_overlaps,
               "torso_coverage": torso_coverage,
               "mesh_summary": mesh_summary,
               "lods": lods,
               "fit_contract_version": "armor-body-fit.v1",
               "fit_summary": {
                   "parts_pass": parts_pass, "parts_total": len(placed),
                   "joints_pass": joints_pass, "joints_total": len(joint_gaps),
                   "max_intrusion_ratio": FIT_MAX_INTRUSION_RATIO,
                   "max_intrusion_m": FIT_MAX_INTRUSION_M,
               },
               "joint_gaps": joint_gaps, "parts": placed}
    with open(os.path.join(out_dir, f"{label}.assembly.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
    print("ARMOR_FULLBODY_RESULT:" + json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
