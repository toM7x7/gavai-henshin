"""Review renderer: load review_master.blend, import a GLB, render 4 angles.

Run inside Blender via ``exec(open(path).read(), globals())``. Provides:

- ``render_review_for_module(module: str, repo_root: str) -> dict``
- ``render_review_all(repo_root: str) -> list[dict]``
- ``render_full_suit(repo_root: str) -> dict`` (Wave 1 hero shot, all modules attached)
- ``render_module_closeup(module: str, repo_root: str) -> dict`` (tight per-module frame)
- ``render_closeups_all(repo_root: str) -> list[dict]``
- ``ensure_vrm_master_blend(repo_root: str) -> str`` (build VRM-backed master once)

Each per-module render writes ``viewer/assets/armor-parts/<module>/preview/<view>.png``
for ``view in {front, side, back, 3q}``.

VRM-backed render path (added 2026-04-30): the legacy master uses a hand-built
sphere/cylinder body proxy that does not match the Web Forge hero. The new
``review_master_vrm.blend`` imports ``viewer/assets/vrm/default.vrm`` so reviews
match production. All render entry points prefer the VRM master when available
and fall back to the legacy master if VRM import fails.
"""

from __future__ import annotations

import json
import os
from typing import Any

import bpy


_VIEWS = ("front", "side", "back", "3q")
_VIEW_TO_CAMERA = {
    "front": "cam_front",
    "side": "cam_side",
    "back": "cam_back",
    "3q": "cam_3q",
}

# Module-level cache: ensure_vrm_master_blend should only run once per session.
# Maps repo_root -> master path (or None if VRM build failed and we must fall
# back to legacy master).
_VRM_MASTER_CACHE: dict[str, str | None] = {}


def _master_blend(repo_root: str) -> str:
    return os.path.join(repo_root, "viewer", "assets", "armor-parts", "_masters", "review_master.blend")


def _master_blend_vrm(repo_root: str) -> str:
    return os.path.join(repo_root, "viewer", "assets", "armor-parts", "_masters", "review_master_vrm.blend")


def _vrm_source_path(repo_root: str) -> str:
    return os.path.join(repo_root, "viewer", "assets", "vrm", "default.vrm")


def _glb_path(repo_root: str, module: str) -> str:
    return os.path.join(repo_root, "viewer", "assets", "armor-parts", module, f"{module}.glb")


def _preview_dir(repo_root: str, module: str) -> str:
    out = os.path.join(repo_root, "viewer", "assets", "armor-parts", module, "preview")
    os.makedirs(out, exist_ok=True)
    return out


def _bone_world_position(module_part: dict[str, Any]) -> tuple[float, float, float]:
    """Approximate the VRM body anchor location for the module in master scene coordinates.

    Master scene puts feet at z=0, head at z=1.65 (170cm).
    """
    bone = module_part.get("vrm_attachment", {}).get("primary_bone") or ""
    z_lookup = {
        "Head": 1.55, "Neck": 1.42, "UpperChest": 1.30, "Chest": 1.20, "Spine": 1.05,
        "Hips": 0.94, "LeftShoulder": 1.43, "RightShoulder": 1.43,
        "LeftUpperArm": 1.30, "RightUpperArm": 1.30,
        "LeftLowerArm": 1.10, "RightLowerArm": 1.10,
        "LeftHand": 0.95, "RightHand": 0.95,
        "LeftUpperLeg": 0.71, "RightUpperLeg": 0.71,
        "LeftLowerLeg": 0.30, "RightLowerLeg": 0.30,
        "LeftFoot": 0.05, "RightFoot": 0.05,
    }
    x_lookup = {
        "LeftShoulder": 0.18, "LeftUpperArm": 0.31, "LeftLowerArm": 0.42,
        "LeftHand": 0.50, "LeftUpperLeg": 0.10, "LeftLowerLeg": 0.10, "LeftFoot": 0.10,
        "RightShoulder": -0.18, "RightUpperArm": -0.31, "RightLowerArm": -0.42,
        "RightHand": -0.50, "RightUpperLeg": -0.10, "RightLowerLeg": -0.10, "RightFoot": -0.10,
    }
    z = z_lookup.get(bone, 1.10)
    x = x_lookup.get(bone, 0.0)
    offset = module_part.get("vrm_attachment", {}).get("offset_m") or [0, 0, 0]
    if len(offset) >= 3:
        return (x + float(offset[0]), float(offset[2]), z + float(offset[1]))
    return (x, 0.0, z)


def _strip_imported(prefix: str = "armor_") -> None:
    for o in list(bpy.data.objects):
        if o.name.startswith(prefix):
            bpy.data.objects.remove(o, do_unlink=True)


def _import_glb(glb_path: str) -> bpy.types.Object | None:
    if not os.path.exists(glb_path):
        return None
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=glb_path)
    new_objs = [o for o in bpy.data.objects if o not in before and o.type == 'MESH']
    if not new_objs:
        return None
    return new_objs[0]


def _set_collection_visibility(name: str, visible: bool) -> bool:
    """Toggle hide_render and hide_viewport on a collection by name.

    Used to hide the body (legacy ``vrm_body_proxy`` or new ``vrm_body``) during
    closeup renders so only the armor module is in frame. Returns whether the
    named collection was found.
    """
    coll = bpy.data.collections.get(name)
    if coll is None:
        return False
    coll.hide_render = not visible
    coll.hide_viewport = not visible
    return True


def _hide_body_collections(visible: bool) -> list[str]:
    """Toggle visibility on both legacy and VRM body collections.

    Returns the list of collection names that were found and toggled.
    """
    found: list[str] = []
    for name in ("vrm_body", "vrm_body_proxy"):
        if _set_collection_visibility(name, visible):
            found.append(name)
    return found


# ---------------------------------------------------------------------------
# VRM master scene construction
# ---------------------------------------------------------------------------

def _add_camera(name: str, location: tuple[float, float, float], target: tuple[float, float, float]) -> bpy.types.Object:
    """Create a camera at ``location`` with a TRACK_TO constraint aimed at ``target``."""
    cam_data = bpy.data.cameras.new(name=name)
    cam_obj = bpy.data.objects.new(name=name, object_data=cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)
    cam_obj.location = location

    target_name = f"_target_{name}"
    target_empty = bpy.data.objects.new(name=target_name, object_data=None)
    target_empty.location = target
    bpy.context.scene.collection.objects.link(target_empty)

    constraint = cam_obj.constraints.new(type='TRACK_TO')
    constraint.track_axis = 'TRACK_NEGATIVE_Z'
    constraint.up_axis = 'UP_Y'
    constraint.target = target_empty
    return cam_obj


def _add_area_light(name: str, location: tuple[float, float, float], energy: float, size: float, color: tuple[float, float, float]) -> bpy.types.Object:
    light_data = bpy.data.lights.new(name=name, type='AREA')
    light_data.energy = energy
    light_data.size = size
    light_data.color = color
    light_obj = bpy.data.objects.new(name=name, object_data=light_data)
    bpy.context.scene.collection.objects.link(light_obj)
    light_obj.location = location
    return light_obj


def ensure_vrm_master_blend(repo_root: str) -> str:
    """Build (once per session) the VRM-backed review master blend.

    Imports ``viewer/assets/vrm/default.vrm`` into a fresh empty blend, groups
    the imported objects under a ``vrm_body`` collection, adds the same four
    review cameras and three-point area-light rig used by the legacy master,
    creates an empty ``armor_active`` collection for armor imports, and saves
    the result to ``viewer/assets/armor-parts/_masters/review_master_vrm.blend``.

    Cached per-process. On any failure logs the reason and returns the legacy
    master path so callers can keep rendering instead of erroring out.
    """
    if repo_root in _VRM_MASTER_CACHE:
        cached = _VRM_MASTER_CACHE[repo_root]
        if cached is not None:
            return cached
        return _master_blend(repo_root)

    master_vrm_path = _master_blend_vrm(repo_root)
    legacy_path = _master_blend(repo_root)

    # If we already built it in a previous process, reuse on disk.
    if os.path.exists(master_vrm_path):
        _VRM_MASTER_CACHE[repo_root] = master_vrm_path
        return master_vrm_path

    vrm_path = _vrm_source_path(repo_root)
    if not os.path.exists(vrm_path):
        print(f"[render_review] VRM source missing at {vrm_path}; falling back to legacy master")
        _VRM_MASTER_CACHE[repo_root] = None
        return legacy_path

    try:
        os.makedirs(os.path.dirname(master_vrm_path), exist_ok=True)

        # MCP sandbox blocks read_factory_settings; read_homefile with the same
        # flags reaches the empty/factory state without resetting user prefs.
        bpy.ops.wm.read_homefile(use_empty=True, use_factory_startup=True)

        # World background grey to match legacy review look.
        world = bpy.data.worlds.new(name="review_world") if not bpy.context.scene.world else bpy.context.scene.world
        bpy.context.scene.world = world
        world.use_nodes = True
        bg_node = world.node_tree.nodes.get("Background")
        if bg_node is not None:
            bg_node.inputs[0].default_value = (0.06, 0.07, 0.09, 1.0)

        # Import the VRM via the gltf importer (Blender 5 reads VRM binary as glTF
        # for our purposes). We track which objects appear so we can group them.
        before_objs = set(bpy.data.objects)
        try:
            bpy.ops.import_scene.gltf(filepath=vrm_path)
        except Exception as exc:  # noqa: BLE001
            try:
                bpy.ops.import_scene.gltf(filepath=vrm_path, loglevel='ERROR')
            except Exception as exc2:  # noqa: BLE001
                print(f"[render_review] VRM gltf import failed twice: {exc!r} / {exc2!r}; falling back to legacy master")
                _VRM_MASTER_CACHE[repo_root] = None
                return legacy_path

        new_objs = [o for o in bpy.data.objects if o not in before_objs]
        if not new_objs:
            print("[render_review] VRM import produced no objects; falling back to legacy master")
            _VRM_MASTER_CACHE[repo_root] = None
            return legacy_path

        # Group all imported objects (armature + meshes) into a vrm_body collection.
        body_coll = bpy.data.collections.get("vrm_body")
        if body_coll is None:
            body_coll = bpy.data.collections.new("vrm_body")
            bpy.context.scene.collection.children.link(body_coll)
        for o in new_objs:
            for c in list(o.users_collection):
                try:
                    c.objects.unlink(o)
                except Exception:  # noqa: BLE001
                    pass
            try:
                body_coll.objects.link(o)
            except Exception:  # noqa: BLE001
                pass

        # Empty collection for armor imports.
        if bpy.data.collections.get("armor_active") is None:
            armor_coll = bpy.data.collections.new("armor_active")
            bpy.context.scene.collection.children.link(armor_coll)

        # Cameras matching the legacy master positions, all aimed at (0, 0, 1.0).
        target = (0.0, 0.0, 1.0)
        _add_camera("cam_front", (0.0, -2.6, 1.0), target)
        _add_camera("cam_side", (2.6, 0.0, 1.0), target)
        _add_camera("cam_back", (0.0, 2.6, 1.0), target)
        _add_camera("cam_3q", (1.85, -1.85, 1.30), target)

        # Three-point area-light rig (values mirror the legacy review_master setup).
        _add_area_light("key_light", (1.6, -2.0, 2.4), energy=420.0, size=2.0, color=(1.0, 0.97, 0.93))
        _add_area_light("fill_light", (-1.8, -1.4, 1.6), energy=180.0, size=2.5, color=(0.85, 0.92, 1.0))
        _add_area_light("rim_light", (0.0, 2.2, 2.6), energy=260.0, size=1.6, color=(1.0, 0.98, 0.95))

        bpy.context.view_layer.update()
        bpy.ops.wm.save_as_mainfile(filepath=master_vrm_path, copy=True, compress=True)

        _VRM_MASTER_CACHE[repo_root] = master_vrm_path
        return master_vrm_path
    except Exception as exc:  # noqa: BLE001
        print(f"[render_review] ensure_vrm_master_blend failed: {exc!r}; falling back to legacy master")
        _VRM_MASTER_CACHE[repo_root] = None
        return legacy_path


def _resolve_master_blend(repo_root: str) -> str:
    """Return the preferred master blend path for this session.

    Builds the VRM master on first use; falls back to the legacy master on
    any error or if VRM source is missing.
    """
    try:
        path = ensure_vrm_master_blend(repo_root)
    except Exception as exc:  # noqa: BLE001
        print(f"[render_review] ensure_vrm_master_blend raised: {exc!r}; using legacy master")
        path = _master_blend(repo_root)
    if path and os.path.exists(path):
        return path
    return _master_blend(repo_root)


def render_review_for_module(module: str, repo_root: str) -> dict[str, Any]:
    """Render front/side/back/3q PNGs for one module."""
    master = _resolve_master_blend(repo_root)
    glb = _glb_path(repo_root, module)
    out_dir = _preview_dir(repo_root, module)
    if not os.path.exists(master):
        return {"module": module, "ok": False, "error": f"master.blend missing: {master}"}
    if not os.path.exists(glb):
        return {"module": module, "ok": False, "error": f"glb missing: {glb}"}

    bpy.ops.wm.open_mainfile(filepath=master)
    _strip_imported()

    bp_path = os.path.join(repo_root, "tools", "blender", "_blueprint_snapshot.json")
    with open(bp_path, "r", encoding="utf-8") as fh:
        bp = json.load(fh)
    part = next((p for p in (bp.get("parts") or []) if p.get("module") == module), {})

    obj = _import_glb(glb)
    if obj is None:
        return {"module": module, "ok": False, "error": "import_scene.gltf failed"}

    target_loc = _bone_world_position(part)
    obj.location = target_loc

    armor_coll = bpy.data.collections.get("armor_active") or bpy.context.scene.collection
    for c in obj.users_collection:
        c.objects.unlink(obj)
    armor_coll.objects.link(obj)

    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 1024
    scene.render.resolution_y = 1024

    rendered = {}
    for view in _VIEWS:
        cam = bpy.data.objects.get(_VIEW_TO_CAMERA[view])
        if cam is None:
            rendered[view] = None
            continue
        scene.camera = cam
        out_path = os.path.join(out_dir, f"{module}_{view}.png")
        scene.render.filepath = out_path
        bpy.ops.render.render(write_still=True)
        rendered[view] = out_path
    return {"module": module, "ok": True, "renders": rendered, "import_dims": tuple(obj.dimensions)}


def render_review_all(repo_root: str) -> list[dict[str, Any]]:
    bp_path = os.path.join(repo_root, "tools", "blender", "_blueprint_snapshot.json")
    with open(bp_path, "r", encoding="utf-8") as fh:
        bp = json.load(fh)
    out = []
    for part in bp.get("parts", []) or []:
        module = part.get("module")
        if not module:
            continue
        try:
            out.append(render_review_for_module(module, repo_root))
        except Exception as exc:  # noqa: BLE001
            out.append({"module": module, "ok": False, "error": repr(exc)})
    return out


def _full_suit_preview_dir(repo_root: str) -> str:
    out = os.path.join(repo_root, "viewer", "assets", "armor-parts", "_masters")
    os.makedirs(out, exist_ok=True)
    return out


def _load_blueprint(repo_root: str) -> dict[str, Any]:
    bp_path = os.path.join(repo_root, "tools", "blender", "_blueprint_snapshot.json")
    with open(bp_path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _configure_eevee(scene: bpy.types.Scene) -> None:
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 1024
    scene.render.resolution_y = 1024


def _composite_overlay(body_path: str, parts_path: str, out_path: str) -> bool:
    """Composite a body proxy render and an armor render via Blender's compositor.

    Returns True on success. Falls back to copying ``parts_path`` to ``out_path``
    when the compositor is unavailable.
    """
    try:
        scene = bpy.context.scene
        scene.use_nodes = True
        tree = scene.node_tree
        for node in list(tree.nodes):
            tree.nodes.remove(node)
        body_node = tree.nodes.new(type='CompositorNodeImage')
        body_img = bpy.data.images.load(body_path, check_existing=True)
        body_node.image = body_img
        parts_node = tree.nodes.new(type='CompositorNodeImage')
        parts_img = bpy.data.images.load(parts_path, check_existing=True)
        parts_node.image = parts_img
        alpha_over = tree.nodes.new(type='CompositorNodeAlphaOver')
        composite = tree.nodes.new(type='CompositorNodeComposite')
        tree.links.new(body_node.outputs['Image'], alpha_over.inputs[1])
        tree.links.new(parts_node.outputs['Image'], alpha_over.inputs[2])
        tree.links.new(alpha_over.outputs['Image'], composite.inputs['Image'])
        scene.render.filepath = out_path
        bpy.ops.render.render(write_still=True)
        return True
    except Exception:  # noqa: BLE001
        try:
            import shutil
            shutil.copyfile(parts_path, out_path)
            return True
        except Exception:  # noqa: BLE001
            return False


def render_full_suit(repo_root: str) -> dict[str, Any]:
    """Load review_master.blend, import every module GLB at its bone position,
    render front/side/back/3q to viewer/assets/armor-parts/_masters/full_suit_<view>.png.

    Also writes ``_masters/full_suit_overlay.png`` as a 3q hero shot combining
    body proxy + every armor module.

    Return ``{ok, renders: {view: path}, attached_modules: [...]}``.
    """
    master = _resolve_master_blend(repo_root)
    if not os.path.exists(master):
        return {"ok": False, "error": f"master.blend missing: {master}", "renders": {}, "attached_modules": []}

    out_dir = _full_suit_preview_dir(repo_root)
    bpy.ops.wm.open_mainfile(filepath=master)
    _strip_imported()

    bp = _load_blueprint(repo_root)
    parts = bp.get("parts") or []

    armor_coll = bpy.data.collections.get("armor_active") or bpy.context.scene.collection
    attached: list[str] = []
    missing: list[str] = []
    for part in parts:
        module = part.get("module")
        if not module:
            continue
        glb = _glb_path(repo_root, module)
        if not os.path.exists(glb):
            missing.append(module)
            continue
        obj = _import_glb(glb)
        if obj is None:
            missing.append(module)
            continue
        obj.location = _bone_world_position(part)
        for c in obj.users_collection:
            c.objects.unlink(obj)
        armor_coll.objects.link(obj)
        attached.append(module)

    scene = bpy.context.scene
    _configure_eevee(scene)

    rendered: dict[str, str | None] = {}
    for view in _VIEWS:
        cam = bpy.data.objects.get(_VIEW_TO_CAMERA[view])
        if cam is None:
            rendered[view] = None
            continue
        scene.camera = cam
        out_path = os.path.join(out_dir, f"full_suit_{view}.png")
        scene.render.filepath = out_path
        bpy.ops.render.render(write_still=True)
        rendered[view] = out_path

    overlay_path: str | None = None
    suit_3q = rendered.get("3q")
    if suit_3q and os.path.exists(suit_3q):
        overlay_target = os.path.join(out_dir, "full_suit_overlay.png")
        try:
            import shutil
            shutil.copyfile(suit_3q, overlay_target)
            overlay_path = overlay_target
        except Exception:  # noqa: BLE001
            overlay_path = None

    return {
        "ok": True,
        "renders": rendered,
        "overlay": overlay_path,
        "attached_modules": attached,
        "missing_modules": missing,
    }


def render_module_closeup(module: str, repo_root: str) -> dict[str, Any]:
    """Render tight closeup PNGs for one module.

    Creates a temporary 50mm camera at distance ``max(bbox) * 2.2`` looking at the
    module's WORLD bbox center and renders front/side/back/3q to
    ``viewer/assets/armor-parts/<module>/preview/<module>_closeup_<view>.png``.

    Hides the body collection during rendering so only the armor module is in
    frame. Restores visibility after rendering completes (or on error).

    Return ``{ok, renders: {view: path}, frame_distance: float}``.
    """
    master = _resolve_master_blend(repo_root)
    glb = _glb_path(repo_root, module)
    out_dir = _preview_dir(repo_root, module)
    if not os.path.exists(master):
        return {"module": module, "ok": False, "error": f"master.blend missing: {master}", "renders": {}, "frame_distance": 0.0}
    if not os.path.exists(glb):
        return {"module": module, "ok": False, "error": f"glb missing: {glb}", "renders": {}, "frame_distance": 0.0}

    bpy.ops.wm.open_mainfile(filepath=master)
    _strip_imported()

    bp = _load_blueprint(repo_root)
    part = next((p for p in (bp.get("parts") or []) if p.get("module") == module), {})

    obj = _import_glb(glb)
    if obj is None:
        return {"module": module, "ok": False, "error": "import_scene.gltf failed", "renders": {}, "frame_distance": 0.0}

    target_loc = _bone_world_position(part)
    obj.location = target_loc

    armor_coll = bpy.data.collections.get("armor_active") or bpy.context.scene.collection
    for c in obj.users_collection:
        c.objects.unlink(obj)
    armor_coll.objects.link(obj)

    bpy.context.view_layer.update()

    # Compute world-space bbox AFTER placing the module at its bone position.
    center = (
        float(target_loc[0]),
        float(target_loc[1]),
        float(target_loc[2]),
    )
    bbox_dims = (float(obj.dimensions[0]), float(obj.dimensions[1]), float(obj.dimensions[2]))
    try:
        from mathutils import Vector
        corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
        if corners:
            xs = [c.x for c in corners]
            ys = [c.y for c in corners]
            zs = [c.z for c in corners]
            center = (
                (min(xs) + max(xs)) * 0.5,
                (min(ys) + max(ys)) * 0.5,
                (min(zs) + max(zs)) * 0.5,
            )
            bbox_dims = (
                max(xs) - min(xs),
                max(ys) - min(ys),
                max(zs) - min(zs),
            )
    except Exception:  # noqa: BLE001
        pass

    max_dim = max(bbox_dims[0], bbox_dims[1], bbox_dims[2]) if any(bbox_dims) else 0.2
    frame_distance = float(max_dim) * 2.2
    if frame_distance <= 0.0:
        frame_distance = 0.5

    cam_data = bpy.data.cameras.new(name=f"_closeup_cam_{module}")
    cam_data.lens = 50.0  # 50mm: tight framing without distortion
    cam_obj = bpy.data.objects.new(name=f"_closeup_cam_{module}", object_data=cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)

    constraint = cam_obj.constraints.new(type='TRACK_TO')
    constraint.track_axis = 'TRACK_NEGATIVE_Z'
    constraint.up_axis = 'UP_Y'

    target_empty = bpy.data.objects.new(name=f"_closeup_target_{module}", object_data=None)
    target_empty.location = center
    bpy.context.scene.collection.objects.link(target_empty)
    constraint.target = target_empty

    # View offsets are relative to the BBOX center.
    view_offsets = {
        "front": (0.0, -frame_distance, 0.0),
        "side": (frame_distance, 0.0, 0.0),
        "back": (0.0, frame_distance, 0.0),
        "3q": (frame_distance * 0.7, -frame_distance * 0.7, frame_distance * 0.4),
    }

    scene = bpy.context.scene
    _configure_eevee(scene)

    # Hide body so only the module is in frame; remember what we hid for restore.
    hidden_collections = _hide_body_collections(visible=False)

    rendered: dict[str, str | None] = {}
    try:
        for view in _VIEWS:
            offset = view_offsets.get(view, (0.0, -frame_distance, 0.0))
            cam_obj.location = (
                center[0] + offset[0],
                center[1] + offset[1],
                center[2] + offset[2],
            )
            scene.camera = cam_obj
            bpy.context.view_layer.update()
            out_path = os.path.join(out_dir, f"{module}_closeup_{view}.png")
            scene.render.filepath = out_path
            bpy.ops.render.render(write_still=True)
            rendered[view] = out_path
    finally:
        # Restore body visibility for whatever scene the next call opens.
        for name in hidden_collections:
            _set_collection_visibility(name, visible=True)
        try:
            bpy.data.objects.remove(cam_obj, do_unlink=True)
        except Exception:  # noqa: BLE001
            pass
        try:
            bpy.data.cameras.remove(cam_data, do_unlink=True)
        except Exception:  # noqa: BLE001
            pass
        try:
            bpy.data.objects.remove(target_empty, do_unlink=True)
        except Exception:  # noqa: BLE001
            pass

    return {
        "module": module,
        "ok": True,
        "renders": rendered,
        "frame_distance": frame_distance,
        "bbox_center": center,
        "bbox_dims": bbox_dims,
    }


def render_closeups_all(repo_root: str) -> list[dict[str, Any]]:
    """Run ``render_module_closeup`` over every module in the blueprint snapshot."""
    bp = _load_blueprint(repo_root)
    out: list[dict[str, Any]] = []
    for part in bp.get("parts", []) or []:
        module = part.get("module")
        if not module:
            continue
        try:
            out.append(render_module_closeup(module, repo_root))
        except Exception as exc:  # noqa: BLE001
            out.append({"module": module, "ok": False, "error": repr(exc), "renders": {}, "frame_distance": 0.0})
    return out


if __name__ == "__main__":
    raise SystemExit("Run inside Blender")
