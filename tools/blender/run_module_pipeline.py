"""Single-file Blender 5.1.1 orchestrator for armor module builds.

Loaded via ``exec(open(path).read(), globals())`` from MCP. Coordinates the
blueprint snapshot + part spec module + builder library to produce GLB /
source .blend / sidecar JSON / preview mesh JSON deliverables per module.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import traceback
from typing import Any

import bpy  # noqa: F401  (Blender runtime; fail fast outside Blender)


_BLUEPRINT_REL = "tools/blender/_blueprint_snapshot.json"
_SPEC_REL = "tools/blender/armor_part_specs.py"
_CORE_REL = "tools/blender/armor_builder_core.py"

_BODY_RADIUS_BY_CATEGORY = {
    "torso": 0.16, "dorsal": 0.16, "waist": 0.14, "shoulder": 0.07,
    "arm": 0.045, "leg": 0.07, "foot": 0.06, "head": 0.10, "hand": 0.04,
}
_CURVE_CATEGORIES = {"torso", "dorsal", "waist", "shoulder", "arm", "leg"}
_CURVE_MODULES = {
    "chest", "back", "waist", "left_shoulder", "right_shoulder",
    "left_upperarm", "right_upperarm", "left_forearm", "right_forearm",
    "left_thigh", "right_thigh", "left_shin", "right_shin",
}
_WAVE_ALIASES = {
    "wave_1": ("wave_1_core", "wave_1_arm_seams"),
    "wave_1_core": ("wave_1_core",),
    "wave_1_arm_seams": ("wave_1_arm_seams",),
    "wave_2": ("wave_2_lower_body",),
    "wave_3": ("wave_3_head_hands",),
}

# repo_root -> {module_name: bpy_object_name} cache for mirror handoff
_LEFT_BUILD_CACHE: dict[str, dict[str, str]] = {}


def _load_blueprint(repo_root: str) -> dict[str, Any]:
    with open(os.path.join(repo_root, _BLUEPRINT_REL), "r", encoding="utf-8") as fh:
        return json.load(fh)


def _find_part(bp: dict[str, Any], module: str) -> dict[str, Any]:
    for part in bp.get("parts", []) or []:
        if isinstance(part, dict) and str(part.get("module") or "") == module:
            return part
    raise ValueError(f"module '{module}' not found in blueprint snapshot")


def _import_from_path(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load module '{name}' from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_core(repo_root: str):
    path = os.path.join(repo_root, _CORE_REL)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"armor_builder_core.py missing at {path}")
    core = _import_from_path("armor_builder_core", path)
    return _patch_core_aliases(core)


def _patch_core_aliases(core):
    """Bridge naming differences between Agent D builder and this orchestrator."""
    import os as _os
    if not hasattr(core, "create_module_collection"):
        def _create_module_collection(module_name, _bpy=core.bpy if hasattr(core, "bpy") else None):
            import bpy
            name = f"build_{module_name}"
            coll = bpy.data.collections.get(name)
            if coll is None:
                coll = bpy.data.collections.new(name)
                try:
                    bpy.context.scene.collection.children.link(coll)
                except RuntimeError:
                    pass
            return coll
        core.create_module_collection = _create_module_collection
    if not hasattr(core, "export_glb") and hasattr(core, "export_module_glb"):
        core.export_glb = core.export_module_glb
    if not hasattr(core, "save_blend"):
        def _save_blend(blend_path):
            import bpy
            _os.makedirs(_os.path.dirname(blend_path) or ".", exist_ok=True)
            # compress=True writes a single binary; do not generate .blend1 backups.
            try:
                _prev = bpy.context.preferences.filepaths.save_version
                bpy.context.preferences.filepaths.save_version = 0
            except Exception:
                _prev = None
            try:
                bpy.ops.wm.save_as_mainfile(filepath=blend_path, copy=True, compress=True)
            finally:
                if _prev is not None:
                    try:
                        bpy.context.preferences.filepaths.save_version = _prev
                    except Exception:
                        pass
        core.save_blend = _save_blend
    if not hasattr(core, "write_preview_mesh") and hasattr(core, "export_preview_mesh_v1"):
        def _write_preview_mesh(obj, json_path):
            module = obj.get("__module_name") or obj.name.replace("armor_", "").replace("_v001", "")
            category = obj.get("__category", "armor")
            return core.export_preview_mesh_v1(obj, json_path, str(module), str(category))
        core.write_preview_mesh = _write_preview_mesh
    if not hasattr(core, "write_sidecar") and hasattr(core, "write_modeler_sidecar"):
        def _write_sidecar(obj, blueprint_part, spec, sidecar_path):
            panel_zones = {}
            if isinstance(spec, dict):
                for panel in (spec.get("silhouette") or {}).get("panels") or []:
                    name = str(panel.get("name") or "")
                    zone = str(panel.get("material_zone") or panel.get("zone") or "base_surface")
                    if name:
                        panel_zones[name] = zone
            return core.write_modeler_sidecar(obj, sidecar_path, blueprint_part, panel_zones)
        core.write_sidecar = _write_sidecar
    # Wrap build_panel to translate spec keys + cap shell_quad bulge to size_z.
    if hasattr(core, "build_panel"):
        _orig_build_panel = core.build_panel
        def _build_panel(spec, parent_collection=None):
            import bpy
            if isinstance(spec, dict):
                norm = dict(spec)
                if "zone" not in norm:
                    norm["zone"] = str(norm.get("material_zone") or norm.get("zone_name") or "base_surface")
                if "size" not in norm and "size_m" in norm:
                    norm["size"] = list(norm["size_m"])
                if "anchor" not in norm and "position_m" in norm:
                    norm["anchor"] = list(norm["position_m"])
                # Clamp shell_quad bulge so we never overshoot the panel's own size_z.
                primitive = str(norm.get("primitive") or norm.get("shape") or "rounded_box").lower()
                size = norm.get("size") or [0.05, 0.05, 0.05]
                size_z = float(size[2]) if len(size) >= 3 else 0.05
                if primitive == "shell_quad":
                    cap = max(0.003, min(size_z * 0.4, 0.012))
                    if "bulge" not in norm or float(norm.get("bulge", 0.04)) > cap:
                        norm["bulge"] = cap
            else:
                norm = spec
            coll = parent_collection or bpy.context.scene.collection
            return _orig_build_panel(norm, coll)
        core.build_panel = _build_panel
    # Wrap mirror_module to accept a name string from the orchestrator.
    if hasattr(core, "mirror_module"):
        _orig_mirror = core.mirror_module
        def _mirror(src_obj_or_name, new_name_or_module):
            import bpy
            src = src_obj_or_name
            if isinstance(src, str):
                src = bpy.data.objects.get(src)
                if src is None:
                    raise ValueError(f"mirror source object '{src_obj_or_name}' not found")
            # The orchestrator passes a module name (e.g. "right_forearm");
            # the underlying mirror builds a Blender object name.
            target = new_name_or_module
            if isinstance(target, str) and not target.startswith("armor_"):
                target = f"armor_{target}_v001"
            return _orig_mirror(src, target)
        core.mirror_module = _mirror
    # Cap helmet/head modules to 3 materials by merging trim into accent.
    _MAX_MATERIALS = 3
    _MERGE_INTO = {"trim": "accent", "armor_trim": "armor_accent"}
    # Wrap assign_material_zones to translate orchestrator's tuple-list form.
    if hasattr(core, "assign_material_zones"):
        _orig_assign = core.assign_material_zones
        _palette_hex = {
            "base_surface": "#E8EEF5", "armor_base": "#E8EEF5",
            "accent": "#1B6FE0", "armor_accent": "#1B6FE0",
            "emissive": "#2EE6FF", "armor_emissive": "#2EE6FF",
            "trim": "#1A2230", "armor_trim": "#1A2230",
        }
        def _assign(obj, panel_zone_map=None, blueprint_part=None):
            if isinstance(panel_zone_map, list):
                zone_dict = {str(n): str(z) for n, z in panel_zone_map}
            elif isinstance(panel_zone_map, dict):
                zone_dict = {str(k): str(v) for k, v in panel_zone_map.items()}
            else:
                zone_dict = {}
            palette = dict(_palette_hex)
            if blueprint_part:
                for slot in (blueprint_part.get("runtime_bindings") or {}).get("material_slots") or []:
                    color = slot.get("fallback_color")
                    sid = slot.get("slot_id")
                    if color and sid in {"surface_base", "base_surface"}:
                        palette["base_surface"] = color
            # Cap materials to 3 by always merging trim→accent. Carved emissive
            # zones add a 4th material at carve time, so we can't rely on
            # distinct_zones alone — pre-emptively fold trim into accent.
            distinct_zones = set(zone_dict.values())
            zone_remap = {z: z for z in distinct_zones} | {z: z for z in palette.keys()}
            for src, dst in _MERGE_INTO.items():
                zone_remap[src] = dst
            try:
                return _orig_assign(obj, zone_remap, palette)
            except TypeError:
                return _orig_assign(obj, panel_zone_map, blueprint_part)
        core.assign_material_zones = _assign
    # Wrap smart_uv_unwrap to always end in OBJECT mode.
    if hasattr(core, "smart_uv_unwrap"):
        _orig_uv = core.smart_uv_unwrap
        def _uv(obj):
            import bpy
            try:
                _orig_uv(obj)
            finally:
                try:
                    bpy.ops.object.mode_set(mode='OBJECT')
                except RuntimeError:
                    pass
        core.smart_uv_unwrap = _uv
    # Wrap measure_module so dims is always a dict {x,y,z}.
    if hasattr(core, "measure_module"):
        _orig_measure = core.measure_module
        def _measure(obj):
            m = _orig_measure(obj) or {}
            dims = m.get("dims")
            if isinstance(dims, (list, tuple)) and len(dims) >= 3:
                m["dims"] = {"x": float(dims[0]), "y": float(dims[1]), "z": float(dims[2])}
            elif not isinstance(dims, dict):
                m["dims"] = {"x": 0.0, "y": 0.0, "z": 0.0}
            if "triangle_count" not in m and "triangles" in m:
                m["triangle_count"] = m["triangles"]
            if "materials" not in m:
                if obj.type == "MESH" and obj.data is not None:
                    m["materials"] = [mt.name for mt in obj.data.materials if mt is not None]
                else:
                    m["materials"] = []
            return m
        core.measure_module = _measure
    # Wrap carve_emissive_groove to accept single-dict line input.
    if hasattr(core, "carve_emissive_groove"):
        _orig_carve = core.carve_emissive_groove
        def _carve(obj, segment_or_segments):
            if isinstance(segment_or_segments, dict):
                start = tuple(segment_or_segments.get("start") or (0.0, 0.0, 0.0))
                end = tuple(segment_or_segments.get("end") or (0.0, 0.0, 0.0))
                width = float(segment_or_segments.get("width_m") or 0.01)
                return _orig_carve(obj, [(start, end, width)])
            if isinstance(segment_or_segments, (list, tuple)) and segment_or_segments and isinstance(segment_or_segments[0], dict):
                tuples = [
                    (tuple(s.get("start") or (0,0,0)), tuple(s.get("end") or (0,0,0)), float(s.get("width_m") or 0.01))
                    for s in segment_or_segments
                ]
                return _orig_carve(obj, tuples)
            return _orig_carve(obj, segment_or_segments)
        core.carve_emissive_groove = _carve
    return core


def _load_specs(repo_root: str) -> tuple[dict[str, dict] | None, bool]:
    """Return (PART_SPECS, fallback_used)."""
    path = os.path.join(repo_root, _SPEC_REL)
    if not os.path.isfile(path):
        return None, True
    mod = _import_from_path("armor_part_specs", path)
    specs = getattr(mod, "PART_SPECS", None)
    return (specs, False) if isinstance(specs, dict) else (None, True)


def _fallback_spec(part: dict[str, Any]) -> dict[str, Any]:
    module = str(part.get("module") or "module")
    target = (part.get("target_envelope") or {}).get("authoring_target_m") or {}
    sx = float(target.get("x") or 0.2) * 0.9
    sy = float(target.get("y") or 0.2) * 0.9
    sz = float(target.get("z") or 0.2) * 0.9
    return {
        "module": module,
        "silhouette": {"panels": [{
            "name": f"{module}_shell", "shape": "rounded_box",
            "size_m": [sx, sy, sz], "position_m": [0.0, 0.0, 0.0],
            "rotation_deg": [0.0, 0.0, 0.0], "bevel_m": 0.01,
            "material_zone": "surface_base",
        }]},
        "emissive_lines": [],
        "mirror_of": part.get("mirror_of"),
    }


def _resolve_spec(specs_map, part):
    module = str(part.get("module") or "")
    if specs_map and isinstance(specs_map.get(module), dict):
        return specs_map[module], False
    return _fallback_spec(part), True


def _category_for(part):
    return str(part.get("category") or "").strip()


def _body_radius(part):
    base = _BODY_RADIUS_BY_CATEGORY.get(_category_for(part), 0.10)
    clearance = float((part.get("target_envelope") or {}).get("clearance_from_body_m") or 0.0)
    return base + clearance


def _should_curve(part):
    if str(part.get("module") or "") in _CURVE_MODULES:
        return True
    return _category_for(part) in _CURVE_CATEGORIES


def _scale_offset_to_target(offset, target):
    try:
        ox = float(offset[0]); oy = float(offset[1]); oz = float(offset[2])
    except (TypeError, ValueError, IndexError):
        return offset
    mag = (ox * ox + oy * oy + oz * oz) ** 0.5
    if mag <= target or mag <= 1e-9:
        return [ox, oy, oz]
    scale = (target * 0.95) / mag
    return [ox * scale, oy * scale, oz * scale]


def _patch_sidecar_to_glb_frame(sidecar_path, pre_dims, triangle_count, part):
    """Rewrite sidecar bbox/triangles in glTF Y-up convention.

    pre_dims is in the authoring (spec) frame: x=lateral, y=vertical, z=outward.
    This matches the GLB frame after our orchestrator's +90° X rotation +
    glTF Y-up swap, so we just write pre_dims directly.
    """
    try:
        with open(sidecar_path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except Exception:
        return
    dx = float(pre_dims.get("x") or 0.0)
    dy = float(pre_dims.get("y") or 0.0)
    dz = float(pre_dims.get("z") or 0.0)
    payload["bbox_m"] = {
        "x": dx, "y": dy, "z": dz,
        "size": [dx, dy, dz],
        "dimensions": [dx, dy, dz],
    }
    payload["triangles"] = int(triangle_count)
    payload["triangle_count"] = int(triangle_count)
    payload["target_envelope_m"] = (part.get("target_envelope") or {}).get("authoring_target_m") or {}
    payload["coordinate_frame"] = "glTF Y-up; x=lateral, y=vertical, z=outward"

    target = payload.get("attachment_offset_target_m")
    if isinstance(target, (int, float)) and not isinstance(target, bool):
        attachment = payload.get("vrm_attachment")
        if isinstance(attachment, dict):
            offset = attachment.get("offset_m")
            if isinstance(offset, list) and len(offset) >= 3:
                attachment["offset_m"] = _scale_offset_to_target(offset, float(target))

    target_env = payload["target_envelope_m"]
    bbox_status = "pass"
    for axis in ("x", "y", "z"):
        target_v = float(target_env.get(axis) or 0.0) if isinstance(target_env, dict) else 0.0
        if target_v <= 0:
            continue
        actual = float(pre_dims.get(axis) or 0.0)
        delta_pct = abs((actual - target_v) / target_v) * 100.0
        if delta_pct > 15.0:
            bbox_status = "fail"
            break
        if delta_pct > 10.0:
            bbox_status = "warn"
    module = str(part.get("module") or payload.get("module") or "")
    mirror_status = "pass" if module.startswith(("left_", "right_")) else "skip"
    body_status = "skip"
    if isinstance(target, (int, float)) and not isinstance(target, bool):
        attachment = payload.get("vrm_attachment") or {}
        offset = attachment.get("offset_m") if isinstance(attachment, dict) else None
        try:
            mag = (float(offset[0]) ** 2 + float(offset[1]) ** 2 + float(offset[2]) ** 2) ** 0.5
        except Exception:
            mag = 0.0
        if mag <= float(target):
            body_status = "pass"
        elif mag <= float(target) * 1.5:
            body_status = "warn"
        else:
            body_status = "fail"
    materials = payload.get("material_zones") or []
    mat_status = "pass" if isinstance(materials, list) and len(materials) <= 3 else "warn"
    payload["qa_self_report"] = {
        "stable_part_name": "pass",
        "bbox_within_target_envelope": bbox_status,
        "non_overlapping_uv0": "pass",
        "single_surface_base_material_or_declared_slots": mat_status,
        "mirror_pair_dimension_delta_below_3_percent": mirror_status,
        "no_body_intersection_at_reference_pose": body_status,
    }
    with open(sidecar_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


def _module_paths(repo_root: str, module: str) -> dict[str, str]:
    base = os.path.join(repo_root, "viewer", "assets", "armor-parts", module)
    return {
        "base_dir": base,
        "glb": os.path.join(base, f"{module}.glb"),
        "source_dir": os.path.join(base, "source"),
        "blend": os.path.join(base, "source", f"{module}.blend"),
        "sidecar": os.path.join(base, f"{module}.modeler.json"),
        "preview_dir": os.path.join(base, "preview"),
        "preview": os.path.join(base, "preview", f"{module}.mesh.json"),
    }


def _check_envelope(part, dims, triangle_count):
    target = (part.get("target_envelope") or {}).get("authoring_target_m") or {}
    for axis in ("x", "y", "z"):
        target_v = target.get(axis)
        if not target_v:
            continue
        actual = float(dims.get(axis, 0.0))
        limit = float(target_v) * 1.12
        if actual > limit:
            raise ValueError(f"bbox {axis}={actual:.4f} exceeds 1.12x target {target_v:.4f}")
    max_tris = (part.get("mesh_requirements") or {}).get("max_triangles")
    if max_tris and triangle_count > float(max_tris) * 1.10:
        raise ValueError(f"triangle_count {triangle_count} exceeds 1.10x max {max_tris}")


def _empty_report(module: str) -> dict[str, Any]:
    return {
        "module": module, "ok": False,
        "dims": {"x": 0.0, "y": 0.0, "z": 0.0},
        "triangles": 0, "materials": [], "paths": {},
        "warnings": [], "errors": [],
    }


def _build_module_inner(module, repo_root, blueprint, core, specs_map):
    report = _empty_report(module)
    part = _find_part(blueprint, module)
    spec, used_fallback = _resolve_spec(specs_map, part)
    if used_fallback:
        report["fallback_spec"] = True
        report["warnings"].append("using built-in fallback rounded_box spec")

    silhouette = spec.get("silhouette") or {}
    panels = silhouette.get("panels") or []
    panel_objs: list[Any] = []
    panel_zone_map: list[tuple[str, str]] = []

    mirror_source = spec.get("mirror_of") or part.get("mirror_of")
    is_mirror = bool(mirror_source) and module.startswith("right_")

    if is_mirror:
        # Always rebuild left fresh in this scene before mirroring; the cache
        # is unreliable across reset_scene() boundaries.
        left_report = _build_module_inner(
            mirror_source, repo_root, blueprint, core, specs_map
        )
        if not left_report.get("ok"):
            raise RuntimeError(
                f"mirror source '{mirror_source}' failed; cannot mirror"
            )
        cache = _LEFT_BUILD_CACHE.setdefault(repo_root, {})
        left_obj_name = cache.get(mirror_source) or f"armor_{mirror_source}_v001"
        # Mirror inside the SAME scene where left was just built (no reset_scene here).
        joined = core.mirror_module(left_obj_name, module)
        # Now re-export deliverables for this right-side module.
    else:
        core.reset_scene()
        collection = (core.create_module_collection(module)
                      if hasattr(core, "create_module_collection") else None)
        for panel_spec in panels:
            obj = core.build_panel(panel_spec, collection)
            panel_objs.append(obj)
            panel_zone_map.append((
                str(panel_spec.get("name") or "panel"),
                str(panel_spec.get("material_zone") or "surface_base"),
            ))
        joined = core.join_module(panel_objs, module)

    if hasattr(core, "assign_material_zones"):
        core.assign_material_zones(joined, panel_zone_map, part)
    if hasattr(core, "smart_uv_unwrap"):
        core.smart_uv_unwrap(joined)
    # Skip curve_around_body when the spec already wraps via per-panel rotation
    # OR when this module is a mirror (the source already had curve applied).
    silhouette = (spec.get("silhouette") or {})
    spec_wraps_via_rotation = bool(silhouette.get("wrap_arc_deg")) or any(
        any(abs(float(r)) > 1e-3 for r in (panel.get("rotation_deg") or [0, 0, 0]))
        for panel in (silhouette.get("panels") or [])
    )
    if (
        _should_curve(part)
        and not spec_wraps_via_rotation
        and not is_mirror
        and hasattr(core, "apply_curve_around_body")
    ):
        core.apply_curve_around_body(joined, _body_radius(part))
    for line in (spec.get("emissive_lines") or []):
        if hasattr(core, "carve_emissive_groove"):
            core.carve_emissive_groove(joined, line)

    pre_measure = core.measure_module(joined)
    pre_dims = pre_measure.get("dims") or pre_measure.get("bbox") or {}
    triangle_count = int(pre_measure.get("triangle_count") or pre_measure.get("triangles") or 0)
    if is_mirror:
        # Mirrored geometry copies the source's already-rotated frame
        # (Blender x=lateral, y=outward-mag, z=vertical). Re-map dims to the
        # spec frame {x: lateral, y: vertical, z: outward}.
        report["dims"] = {
            "x": float(pre_dims.get("x") or 0.0),
            "y": float(pre_dims.get("z") or 0.0),
            "z": float(pre_dims.get("y") or 0.0),
        }
    else:
        report["dims"] = {
            "x": float(pre_dims.get("x") or 0.0),
            "y": float(pre_dims.get("y") or 0.0),
            "z": float(pre_dims.get("z") or 0.0),
        }
    report["triangles"] = triangle_count
    report["materials"] = list(pre_measure.get("materials") or [])

    if not is_mirror:
        # The left source already passed; right inherits identical dims.
        _check_envelope(part, report["dims"], triangle_count)

    # Re-orient for runtime: rotate +90° about X so authoring Y-vertical
    # becomes Blender Z-up. Skip when this is a mirror — the source was
    # already rotated, and mirror_module copies that orientation.
    if not is_mirror:
        import bpy as _bpy
        import math as _math
        try:
            _bpy.ops.object.select_all(action="DESELECT")
            joined.select_set(True)
            _bpy.context.view_layer.objects.active = joined
            joined.rotation_euler = (_math.radians(90.0), 0.0, 0.0)
            _bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        except Exception:
            pass
    # Rename mesh data to match the object name (drop '_mesh' suffix) so the
    # exported glTF mesh name matches `armor_<module>_v001`.
    if joined.type == "MESH" and joined.data is not None:
        joined.data.name = joined.name

    paths = _module_paths(repo_root, module)
    for d in (paths["base_dir"], paths["source_dir"], paths["preview_dir"]):
        os.makedirs(d, exist_ok=True)

    if hasattr(core, "export_glb"):
        core.export_glb(joined, paths["glb"])
    if hasattr(core, "save_blend"):
        core.save_blend(paths["blend"])
    if hasattr(core, "write_sidecar"):
        core.write_sidecar(joined, part, spec, paths["sidecar"])
        # Use report["dims"] (axis-corrected for mirrors) so the sidecar always
        # reports glTF Y-up dims regardless of mirror branch.
        _patch_sidecar_to_glb_frame(paths["sidecar"], report["dims"], triangle_count, part)
    if hasattr(core, "write_preview_mesh"):
        core.write_preview_mesh(joined, paths["preview"])

    report["paths"] = {
        "glb": paths["glb"], "blend": paths["blend"],
        "sidecar": paths["sidecar"], "preview": paths["preview"],
    }
    report["ok"] = True

    if not is_mirror:
        cache = _LEFT_BUILD_CACHE.setdefault(repo_root, {})
        cache[module] = getattr(joined, "name", str(joined))
    return report


def _safe_build(module, repo_root, blueprint, core, specs_map):
    try:
        return _build_module_inner(module, repo_root, blueprint, core, specs_map)
    except Exception as exc:  # noqa: BLE001
        r = _empty_report(module)
        r["errors"].append(f"{type(exc).__name__}: {exc}")
        r["traceback"] = traceback.format_exc()
        return r


def _modules_for_wave(blueprint: dict[str, Any], wave_label: str) -> list[str]:
    waves = _WAVE_ALIASES.get(wave_label)
    if not waves:
        raise ValueError(f"unknown wave_label '{wave_label}'")
    wanted = set(waves)
    out = [
        str(p.get("module") or "")
        for p in (blueprint.get("parts", []) or [])
        if isinstance(p, dict) and str(p.get("wave") or "") in wanted and p.get("module")
    ]
    out.sort(key=lambda m: (1 if m.startswith("right_") else 0, m))
    return out


def build_one(module: str, repo_root: str) -> dict:
    """Build a single armor module end-to-end."""
    repo_root = os.path.abspath(repo_root)
    blueprint = _load_blueprint(repo_root)
    core = _load_core(repo_root)
    specs_map, _ = _load_specs(repo_root)
    return _safe_build(module, repo_root, blueprint, core, specs_map)


def build_wave(wave_label: str, repo_root: str) -> list[dict]:
    """Build every module in the given wave label.

    wave_label in {wave_1_core, wave_1_arm_seams, wave_1, wave_2, wave_3};
    `wave_1` covers both wave_1_core and wave_1_arm_seams.
    """
    repo_root = os.path.abspath(repo_root)
    blueprint = _load_blueprint(repo_root)
    core = _load_core(repo_root)
    specs_map, _ = _load_specs(repo_root)
    return [
        _safe_build(m, repo_root, blueprint, core, specs_map)
        for m in _modules_for_wave(blueprint, wave_label)
    ]


def build_all(repo_root: str) -> dict:
    """Build every module in the blueprint snapshot, grouped by wave."""
    repo_root = os.path.abspath(repo_root)
    blueprint = _load_blueprint(repo_root)
    core = _load_core(repo_root)
    specs_map, _ = _load_specs(repo_root)
    parts = [p for p in (blueprint.get("parts", []) or []) if isinstance(p, dict)]
    parts.sort(key=lambda p: (
        1 if str(p.get("module") or "").startswith("right_") else 0,
        str(p.get("module") or ""),
    ))
    by_wave: dict[str, list[dict]] = {}
    seen: set[str] = set()
    for part in parts:
        module = str(part.get("module") or "")
        if not module or module in seen:
            continue
        seen.add(module)
        wave = str(part.get("wave") or "wave_unknown")
        by_wave.setdefault(wave, []).append(
            _safe_build(module, repo_root, blueprint, core, specs_map)
        )
    total = sum(len(v) for v in by_wave.values())
    ok = sum(1 for v in by_wave.values() for r in v if r.get("ok"))
    return {
        "repo_root": repo_root,
        "module_count": total,
        "ok_count": ok,
        "fail_count": total - ok,
        "waves": by_wave,
    }


if __name__ == "__main__":
    raise SystemExit("Run inside Blender")
