# -*- coding: utf-8 -*-
"""蒸着モーション → VRM Animation (.vrma) 生成器.

VRMA はアバター非依存のヒューマノイドモーション規格 (VRMC_vrm_animation)。
ここで作る henshin.vrma は、どの生成スーツVRMにも「蒸着の見得」を再生できる。

Usage:
  blender --background --python tools/blender/make_henshin_vrma.py -- \
      --out output/blueprint-armor/henshin.vrma [--stills 1]

キーポーズ(約4.5秒 / 30fps):
  構え(気を付け) -> 溜め(半身) -> 十字受け(腕クロス) -> 展開(腕を斜め下へ一閃)
  -> 決め(右拳を突き上げる見得) -> ホールド
VRM アドオン必須 (bpy.ops.export_scene.vrma)。無ければ VRMA_ADDON_MISSING を出して終了。
"""
from __future__ import annotations

import json
import math
import os
import sys

import bpy  # type: ignore
from mathutils import Matrix, Vector  # type: ignore

_HERE = os.path.dirname(os.path.abspath(__file__))
VRM_PATH = os.path.abspath(os.path.join(_HERE, "..", "..", "viewer", "assets", "vrm", "default.vrm"))

FPS = 30


def _args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = {}
    key = None
    for token in argv:
        if token.startswith("--"):
            key = token[2:]
            out[key] = True
        elif key:
            out[key] = token
            key = None
    return out


def reset_scene():
    # NOTE: read_factory_settings would disable the user-profile VRM addon —
    # purge the scene by hand instead
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    for block in (bpy.data.meshes, bpy.data.armatures, bpy.data.materials,
                  bpy.data.images, bpy.data.actions):
        for item in list(block):
            if item.users == 0:
                block.remove(item)


def bone(armature, name):
    pb = armature.pose.bones.get(name)
    if pb is None:
        raise RuntimeError(f"pose bone not found: {name}")
    return pb


def world_rot(pb, axis, deg):
    """Rotate a pose bone in ARMATURE space around its own head."""
    head = pb.matrix.to_translation()
    rot = (Matrix.Translation(head)
           @ Matrix.Rotation(math.radians(deg), 4, axis)
           @ Matrix.Translation(-head))
    pb.matrix = rot @ pb.matrix
    bpy.context.view_layer.update()


def clear_pose(armature):
    for pb in armature.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()


DRIVEN = [
    "J_Bip_C_Hips", "J_Bip_C_Spine", "J_Bip_C_Chest", "J_Bip_C_UpperChest",
    "J_Bip_C_Neck", "J_Bip_C_Head",
    "J_Bip_L_Shoulder", "J_Bip_R_Shoulder",
    "J_Bip_L_UpperArm", "J_Bip_R_UpperArm",
    "J_Bip_L_LowerArm", "J_Bip_R_LowerArm",
    "J_Bip_L_Hand", "J_Bip_R_Hand",
    "J_Bip_L_UpperLeg", "J_Bip_R_UpperLeg",
    "J_Bip_L_LowerLeg", "J_Bip_R_LowerLeg",
]

# axes in armature space: +X = model left, -Y = front, +Z = up
X, Y, Z = "X", "Y", "Z"


def pose_idle(arm):
    """気を付け: arms down along the body."""
    world_rot(bone(arm, "J_Bip_L_UpperArm"), Y, 72)
    world_rot(bone(arm, "J_Bip_R_UpperArm"), Y, -72)


def pose_charge(arm):
    """溜め: slight crouch, fists pulled to the waist."""
    hips = bone(arm, "J_Bip_C_Hips")
    hips.location.z -= 0.05
    world_rot(bone(arm, "J_Bip_C_Chest"), X, -8)
    world_rot(bone(arm, "J_Bip_L_UpperArm"), Y, 65)
    world_rot(bone(arm, "J_Bip_R_UpperArm"), Y, -65)
    world_rot(bone(arm, "J_Bip_L_LowerArm"), X, -95)
    world_rot(bone(arm, "J_Bip_R_LowerArm"), X, -95)
    world_rot(bone(arm, "J_Bip_L_UpperLeg"), Y, -8)
    world_rot(bone(arm, "J_Bip_R_UpperLeg"), Y, 8)
    world_rot(bone(arm, "J_Bip_L_LowerLeg"), X, 12)
    world_rot(bone(arm, "J_Bip_R_LowerLeg"), X, 12)


def pose_cross(arm):
    """十字受け: forearms crossed in front of the chest.

    Axis note (measured): a sideways arm is parallel to the X axis, so
    X-rotations do nothing there — swing with Y (down) first, THEN X
    (forward), and bend the elbow with X + a Z pull toward the centre."""
    world_rot(bone(arm, "J_Bip_L_UpperArm"), Y, 62)
    world_rot(bone(arm, "J_Bip_R_UpperArm"), Y, -62)
    world_rot(bone(arm, "J_Bip_L_UpperArm"), X, -70)
    world_rot(bone(arm, "J_Bip_R_UpperArm"), X, -70)
    world_rot(bone(arm, "J_Bip_L_LowerArm"), X, -75)
    world_rot(bone(arm, "J_Bip_R_LowerArm"), X, -75)
    world_rot(bone(arm, "J_Bip_L_LowerArm"), Z, -35)
    world_rot(bone(arm, "J_Bip_R_LowerArm"), Z, 35)
    world_rot(bone(arm, "J_Bip_C_Head"), X, 6)


def pose_burst(arm):
    """展開: arms flung out diagonal-down, chest opened — 蒸着の一閃."""
    world_rot(bone(arm, "J_Bip_L_UpperArm"), Y, 35)
    world_rot(bone(arm, "J_Bip_R_UpperArm"), Y, -35)
    world_rot(bone(arm, "J_Bip_C_UpperChest"), X, 8)
    world_rot(bone(arm, "J_Bip_C_Head"), X, -8)
    world_rot(bone(arm, "J_Bip_L_UpperLeg"), Y, -10)
    world_rot(bone(arm, "J_Bip_R_UpperLeg"), Y, 10)


def pose_hero(arm):
    """決め: right fist thrust up-forward, left fist at the hip."""
    hips = bone(arm, "J_Bip_C_Hips")
    hips.location.z -= 0.03
    world_rot(bone(arm, "J_Bip_C_Chest"), Z, -14)
    # right punch: swing the sideways arm to the FRONT with Z, then raise
    world_rot(bone(arm, "J_Bip_R_UpperArm"), Z, 80)
    world_rot(bone(arm, "J_Bip_R_UpperArm"), X, -55)
    world_rot(bone(arm, "J_Bip_R_LowerArm"), X, -15)
    world_rot(bone(arm, "J_Bip_L_UpperArm"), Y, 68)
    world_rot(bone(arm, "J_Bip_L_LowerArm"), X, -85)
    world_rot(bone(arm, "J_Bip_C_Head"), Z, 10)
    world_rot(bone(arm, "J_Bip_C_Head"), X, -6)
    world_rot(bone(arm, "J_Bip_L_UpperLeg"), Y, -12)
    world_rot(bone(arm, "J_Bip_R_UpperLeg"), Y, 12)


KEYS = [
    (0.0, pose_idle, "idle"),
    (0.9, pose_charge, "charge"),
    (1.6, pose_cross, "cross"),
    (2.3, pose_burst, "burst"),
    (3.3, pose_hero, "hero"),
    (4.5, pose_hero, "hold"),
]


def keyframe_all(arm, frame):
    for name in DRIVEN:
        pb = bone(arm, name)
        pb.keyframe_insert("rotation_quaternion", frame=frame)
        if name == "J_Bip_C_Hips":
            pb.keyframe_insert("location", frame=frame)


def render_still(arm, path, frame):
    scene = bpy.context.scene
    scene.frame_set(frame)
    cam_data = bpy.data.cameras.new("mo_cam")
    cam = bpy.data.objects.new("mo_cam", cam_data)
    scene.collection.objects.link(cam)
    cam.location = (0.0, -3.4, 1.05)
    cam.rotation_euler = (math.pi / 2, 0.0, 0.0)
    scene.camera = cam
    key = bpy.data.objects.new("mo_key", bpy.data.lights.new("mo_key", "SUN"))
    key.data.energy = 3.5
    key.rotation_euler = (math.radians(50), 0.2, 0.4)
    scene.collection.objects.link(key)
    try:
        scene.render.engine = "BLENDER_EEVEE"
    except TypeError:
        pass
    scene.render.resolution_x = 420
    scene.render.resolution_y = 640
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True)
    bpy.data.objects.remove(key, do_unlink=True)


def main():
    args = _args()
    out_path = os.path.abspath(str(args.get("out", "output/blueprint-armor/henshin.vrma")))
    want_stills = bool(args.get("stills"))

    reset_scene()
    try:
        bpy.ops.import_scene.vrm(filepath=VRM_PATH)
    except AttributeError:
        print("VRMA_ADDON_MISSING: VRM addon not available")
        return
    arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
    if arm is None:
        raise RuntimeError("no armature")
    bpy.context.view_layer.objects.active = arm

    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.frame_start = 0
    scene.frame_end = int(KEYS[-1][0] * FPS)

    arm.animation_data_create()
    action = bpy.data.actions.new("GAVAI_HENSHIN")
    arm.animation_data.action = action
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"

    stills_dir = os.path.join(os.path.dirname(out_path), "henshin-stills")
    for t, fn, label in KEYS:
        clear_pose(arm)
        fn(arm)
        frame = int(t * FPS)
        keyframe_all(arm, frame)
        if want_stills:
            os.makedirs(stills_dir, exist_ok=True)
            render_still(arm, os.path.join(stills_dir, f"{frame:03d}_{label}.png"), frame)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    try:
        bpy.ops.export_scene.vrma(filepath=out_path)
    except AttributeError:
        print("VRMA_EXPORT_OP_MISSING: addon has no export_scene.vrma")
        return
    except Exception as exc:  # noqa: BLE001
        print(f"VRMA_EXPORT_FAILED: {exc}")
        return
    print("VRMA_DONE:" + out_path)
    mirror_dir = os.path.abspath(os.path.join(_HERE, "..", "..", "..", "VRM"))
    if os.path.isdir(mirror_dir):
        import shutil
        shutil.copy2(out_path, os.path.join(mirror_dir, os.path.basename(out_path)))
        print("VRMA_MIRRORED:" + os.path.join(mirror_dir, os.path.basename(out_path)))


if __name__ == "__main__":
    main()
