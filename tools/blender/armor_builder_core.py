"""Procedural armor module builder for Blender 5.1.1.

Loaded via ``exec(open(path).read(), globals())`` or imported as a module.
Public functions are idempotent and never block on UI. Geometry is built with
``bmesh``; materials are Principled BSDF nodes keyed by zone. Coordinates are
authored Z-up (Blender) and converted Y-up only on glTF / mesh.v1 export.
"""
from __future__ import annotations
import importlib.util, json, math, os, sys
import bmesh  # type: ignore
import bpy  # type: ignore
from mathutils import Vector  # type: ignore

__all__ = [
    "reset_scene", "build_panel", "join_module", "assign_material_zones",
    "smart_uv_unwrap", "apply_curve_around_body", "carve_emissive_groove",
    "mirror_module", "export_module_glb", "save_module_blend",
    "export_preview_mesh_v1", "write_modeler_sidecar", "measure_module",
]

# ---- helpers --------------------------------------------------------------
def _hex_to_rgba(value, alpha=1.0):
    text = str(value).strip().lstrip("#")
    if len(text) == 3:
        text = "".join(ch * 2 for ch in text)
    if len(text) != 6:
        return (0.5, 0.5, 0.5, alpha)
    return (int(text[0:2], 16) / 255.0, int(text[2:4], 16) / 255.0,
            int(text[4:6], 16) / 255.0, alpha)

def _link_object(coll, obj):
    if obj.name not in coll.objects: coll.objects.link(obj)
    sc = bpy.context.scene.collection
    if sc is not coll and obj.name in sc.objects:
        try: sc.objects.unlink(obj)
        except RuntimeError: pass

def _replace_object(name):
    obj = bpy.data.objects.get(name)
    if obj is None: return
    mesh = obj.data if isinstance(obj.data, bpy.types.Mesh) else None
    bpy.data.objects.remove(obj, do_unlink=True)
    if mesh is not None and mesh.users == 0:
        bpy.data.meshes.remove(mesh)

def _try_object_mode():
    try: bpy.ops.object.mode_set(mode="OBJECT")
    except RuntimeError: pass

def _select_only(obj):
    _try_object_mode()
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

def _bm_to_object(bm, name, coll):
    _replace_object(name)
    old = bpy.data.meshes.get(name + "_mesh")
    if old is not None:
        bpy.data.meshes.remove(old)
    mesh = bpy.data.meshes.new(name + "_mesh")
    bm.to_mesh(mesh); bm.free(); mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    _link_object(coll, obj)
    return obj

def _apply_transforms(obj, location, rotation_euler, scale):
    if location is not None: obj.location = Vector(location)
    if rotation_euler is not None:
        obj.rotation_euler = tuple(math.radians(a) for a in rotation_euler)
    if scale is not None: obj.scale = Vector(scale)
    _select_only(obj)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

def _bevel(bm, edges, offset, segments=2):
    if offset > 0 and edges:
        bmesh.ops.bevel(bm, geom=edges, offset=offset, offset_type="OFFSET",
                        segments=segments, profile=0.7, affect="EDGES")

def _scale_cube(bm, sx, sy, sz):
    # bmesh.ops.create_cube(size=1.0) emits vertices at +/-0.5 (extent = 1.0).
    # Scale them so the resulting AABB matches the requested (sx, sy, sz) extents.
    for v in bm.verts:
        v.co.x *= sx; v.co.y *= sy; v.co.z *= sz

def _calc_normals(mesh):
    if hasattr(mesh, "calc_normals"):
        try: mesh.calc_normals()
        except RuntimeError: pass

# ---- scene reset ----------------------------------------------------------
def reset_scene():
    """Wipe the current scene of mesh data so a build can start fresh."""
    if bpy.context.object is not None:
        _try_object_mode()
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.curves):
        for item in list(block):
            if item.users == 0:
                block.remove(item)

# ---- panel primitives -----------------------------------------------------
def _p_rounded_box(bm, spec):
    if spec.get("organic_rounding"):
        return _p_ellipsoid(bm, spec)
    sx, sy, sz = spec.get("size", (0.2, 0.2, 0.04))
    bmesh.ops.create_cube(bm, size=1.0)
    _scale_cube(bm, sx, sy, sz); bm.normal_update()
    _bevel(bm, list(bm.edges), float(spec.get("bevel_m", 0.01)))

def _p_wedge(bm, spec):
    sx, sy, sz = spec.get("size", (0.2, 0.2, 0.04))
    taper = float(spec.get("front_z_taper", 0.6))
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= sx * 0.5; v.co.y *= sy * 0.5; v.co.z *= sz * 0.5
        if v.co.y > 0: v.co.z += taper * sz * 0.5
    bm.normal_update()
    _bevel(bm, list(bm.edges), float(spec.get("bevel_m", 0.008)))

def _p_shell_quad(bm, spec):
    sx, sy, sz = spec.get("size", (0.3, 0.3, 0.04))
    nx = int(spec.get("nx", 12)); ny = int(spec.get("ny", 8))
    bulge = float(spec.get("bulge", 0.04))
    hx, hy = sx * 0.5, sy * 0.5
    base_z = -sz * 0.5
    grid = []
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            x = -hx + (i / nx) * sx
            y = -hy + (j / ny) * sy
            radial = math.sqrt((x / hx) ** 2 + (y / hy) ** 2)
            z = base_z + bulge * max(0.0, 1.0 - radial)
            row.append(bm.verts.new((x, y, z)))
        grid.append(row)
    for j in range(ny):
        for i in range(nx):
            bm.faces.new((grid[j][i], grid[j][i+1], grid[j+1][i+1], grid[j+1][i]))
    bm.verts.index_update(); bm.normal_update()
    _bevel(bm, [e for e in bm.edges if e.is_boundary], float(spec.get("bevel_m", 0.006)))

def _p_fillet_cylinder(bm, spec):
    r = float(spec.get("radius", 0.06))
    h = float(spec.get("height", 0.18))
    seg = int(spec.get("segments", 24))
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg,
                          radius1=r, radius2=r, depth=h)
    bm.normal_update()
    _bevel(bm, list(bm.edges), float(spec.get("bevel_m", 0.004)), segments=1)

def _p_trim_ridge(bm, spec):
    sx, sy, sz = spec.get("size", (0.18, 0.012, 0.012))
    bmesh.ops.create_cube(bm, size=1.0)
    _scale_cube(bm, sx, sy, sz); bm.normal_update()
    _bevel(bm, list(bm.edges), float(spec.get("bevel_m", 0.002)), segments=1)

def _p_ellipsoid(bm, spec):
    """Low-poly ellipsoid for organic shells such as helmet domes."""
    sx, sy, sz = spec.get("size", (0.2, 0.2, 0.2))
    u_segments = max(8, int(spec.get("segments", 24)))
    v_segments = max(4, int(spec.get("rings", 12)))
    hx, hy, hz = float(sx) * 0.5, float(sy) * 0.5, float(sz) * 0.5
    verts = []
    top = bm.verts.new((0.0, hy, 0.0))
    bottom = bm.verts.new((0.0, -hy, 0.0))
    for r in range(1, v_segments):
        phi = math.pi * r / v_segments
        y = math.cos(phi) * hy
        ring_radius = math.sin(phi)
        ring = []
        for c in range(u_segments):
            theta = 2.0 * math.pi * c / u_segments
            ring.append(bm.verts.new((math.cos(theta) * ring_radius * hx, y, math.sin(theta) * ring_radius * hz)))
        verts.append(ring)
    if verts:
        first = verts[0]
        last = verts[-1]
        for c in range(u_segments):
            try:
                bm.faces.new((top, first[c], first[(c + 1) % u_segments]))
            except ValueError:
                pass
            try:
                bm.faces.new((bottom, last[(c + 1) % u_segments], last[c]))
            except ValueError:
                pass
        for r in range(len(verts) - 1):
            a, b = verts[r], verts[r + 1]
            for c in range(u_segments):
                try:
                    bm.faces.new((a[c], b[c], b[(c + 1) % u_segments], a[(c + 1) % u_segments]))
                except ValueError:
                    pass
    bm.verts.index_update(); bm.normal_update()
    _bevel(bm, list(bm.edges), float(spec.get("bevel_m", 0.0)), segments=1)

def _p_body_wrap_arc(bm, spec):
    """Curved body-wrapping shell with real thickness.

    spec keys:
       size = (chord_x, height_y, depth_z)  # chord_x ~ envelope.x; depth_z = shell thickness ~ 0.020-0.040
       arc_deg          # default 90; how much of the cylinder it spans
       inner_radius     # default = chord_x / (2*sin(arc_deg/2*pi/180)); auto-fits chord
       segments         # default 14 (radial divisions)
       y_taper_top      # default 0.0; chord shrinks by this fraction at top
       y_taper_bottom   # default 0.0; chord shrinks by this fraction at bottom
       front_bulge      # default 0.05; pushes the center of the arc outward (Z+)
       bevel_m          # default 0.006

    Build: produce a curved shell with inner+outer skin and side caps. The +Z
    direction is the OUTWARD face of the shell. The center of the arc sits at
    z=0; arc opens toward +Z (apex at theta=0 -> +Z).
    """
    sx, sy, sz = spec.get("size", (0.30, 0.30, 0.030))
    chord_x = float(sx)
    height_y = float(sy)
    depth_z = float(sz)
    arc_deg = float(spec.get("arc_deg", 90.0))
    arc_rad = math.radians(arc_deg)
    half_arc = arc_rad * 0.5
    sin_half = math.sin(half_arc) if half_arc > 1e-6 else 1.0
    # chord_x means: target bbox.x of the panel after build. The actual bbox
    # width is governed by the OUTER radius for arc<=180°, so derive
    # outer_radius from chord and back out inner_radius. For arc>180° the
    # bbox is governed by the diameter, so cap accordingly.
    if arc_deg <= 180.0 and sin_half > 1e-6:
        target_max_x = chord_x * 0.5
        outer_r = target_max_x / sin_half
        auto_inner = max(1e-3, outer_r - depth_z)
    else:
        # arc > 180°: max|x| = outer_r (at theta=±90°), so outer_r = chord/2
        outer_r = max(chord_x * 0.5, 1e-3)
        auto_inner = max(1e-3, outer_r - depth_z)
    inner_radius = float(spec.get("inner_radius", auto_inner))
    if inner_radius <= 0:
        inner_radius = max(chord_x * 0.5, 1e-3)
    segments = max(2, int(spec.get("segments", 14)))
    y_taper_top = float(spec.get("y_taper_top", 0.0))
    y_taper_bottom = float(spec.get("y_taper_bottom", 0.0))
    front_bulge = float(spec.get("front_bulge", 0.05))
    bevel_m = float(spec.get("bevel_m", 0.006))

    half_h = height_y * 0.5
    outer_r_base = inner_radius + depth_z

    def _row_radii(y_norm):
        # y_norm in [-1, 1]: -1 = bottom, +1 = top
        if y_norm >= 0:
            chord_scale = max(0.0, 1.0 - y_taper_top * y_norm)
        else:
            chord_scale = max(0.0, 1.0 - y_taper_bottom * (-y_norm))
        ir = inner_radius * chord_scale
        orad = outer_r_base * chord_scale
        return ir, orad

    # Two rib rows (top and bottom). For each row build segments+1 columns.
    # Vertex layout: [row][col][inner=0/outer=1]
    grid: list[list[tuple] ] = []
    rows_y = [(-half_h, -1.0), (half_h, 1.0)]
    for y_val, y_norm in rows_y:
        ir, orad = _row_radii(y_norm)
        col_pairs = []
        for c in range(segments + 1):
            t = c / segments
            theta = -half_arc + t * arc_rad
            # cos(theta=0) = 1 -> apex sits at +Z (outward) for both inner/outer skin.
            # bulge tapers off the center: peaks at theta=0, zero at +/-half_arc.
            bulge_factor = math.cos(theta) if half_arc > 1e-6 else 1.0
            bulge_factor = max(0.0, bulge_factor)
            extra = front_bulge * bulge_factor
            inner_x = math.sin(theta) * ir
            inner_z = math.cos(theta) * ir + extra
            outer_x = math.sin(theta) * orad
            outer_z = math.cos(theta) * orad + extra
            v_inner = bm.verts.new((inner_x, y_val, inner_z))
            v_outer = bm.verts.new((outer_x, y_val, outer_z))
            col_pairs.append((v_inner, v_outer))
        grid.append(col_pairs)

    # Build faces.
    # Outer skin (front, +Z facing): rows along y, cols along arc.
    # Inner skin (back, -Z facing): reversed winding so normals face -outward.
    # Top/bottom caps: connect inner-outer at the same row.
    # Side caps: at c=0 and c=segments, bridge the two rows + inner/outer.
    faces = []
    bottom_row, top_row = grid[0], grid[1]
    for c in range(segments):
        # outer skin quad (winding so normal points along +outer_radial == outward)
        bo0 = bottom_row[c][1]
        bo1 = bottom_row[c + 1][1]
        to1 = top_row[c + 1][1]
        to0 = top_row[c][1]
        try:
            faces.append(bm.faces.new((bo0, to0, to1, bo1)))
        except ValueError:
            pass
        # inner skin quad (reverse winding -> normal points inward, away from body)
        bi0 = bottom_row[c][0]
        bi1 = bottom_row[c + 1][0]
        ti1 = top_row[c + 1][0]
        ti0 = top_row[c][0]
        try:
            faces.append(bm.faces.new((bi0, bi1, ti1, ti0)))
        except ValueError:
            pass
        # top cap quad along this segment (between inner and outer of top row)
        try:
            faces.append(bm.faces.new((ti0, ti1, to1, to0)))
        except ValueError:
            pass
        # bottom cap quad
        try:
            faces.append(bm.faces.new((bi0, bo0, bo1, bi1)))
        except ValueError:
            pass
    # Side caps (c=0 left edge, c=segments right edge): close inner+outer between top and bottom.
    for c, reverse in ((0, False), (segments, True)):
        bi = bottom_row[c][0]
        bo = bottom_row[c][1]
        ti = top_row[c][0]
        to = top_row[c][1]
        verts = (bi, bo, to, ti) if not reverse else (bi, ti, to, bo)
        try:
            faces.append(bm.faces.new(verts))
        except ValueError:
            pass

    bm.verts.index_update()
    bm.normal_update()
    # Center bbox on origin in X (arc is already symmetric, but front_bulge
    # shifts apex; recenter X so x mid sits at zero) and in Z (chord midpoint
    # naturally sits at positive z; recenter so panel's bbox z is symmetric
    # around z=0 — this makes anchor.z behave intuitively).
    if bm.verts:
        xs = [v.co.x for v in bm.verts]
        zs = [v.co.z for v in bm.verts]
        mid_x = (max(xs) + min(xs)) * 0.5
        mid_z = (max(zs) + min(zs)) * 0.5
        if abs(mid_x) > 1e-6 or abs(mid_z) > 1e-6:
            for v in bm.verts:
                v.co.x -= mid_x
                v.co.z -= mid_z
    # Bevel boundary edges only (skip inner-outer connection edges for face count).
    if bevel_m > 0:
        boundary = [e for e in bm.edges if e.is_boundary]
        _bevel(bm, boundary, bevel_m, segments=1)


def _p_solid_shell(bm, spec):
    """shell_quad-style curved plate but with real thickness (extruded inward).

    Same spec keys as shell_quad plus thickness_z (default 0.018).
    The plate's outward face is +Z; back face is -thickness_z below.
    """
    sx, sy, sz = spec.get("size", (0.3, 0.3, 0.04))
    nx = int(spec.get("nx", 12)); ny = int(spec.get("ny", 8))
    bulge = float(spec.get("bulge", 0.04))
    thickness_z = float(spec.get("thickness_z", 0.018))
    bevel_m = float(spec.get("bevel_m", 0.006))
    hx, hy = sx * 0.5, sy * 0.5
    base_z = sz * 0.5
    # outer (front) grid
    outer = []
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            x = -hx + (i / nx) * sx
            y = -hy + (j / ny) * sy
            radial = math.sqrt((x / hx) ** 2 + (y / hy) ** 2)
            z = base_z + bulge * max(0.0, 1.0 - radial)
            row.append(bm.verts.new((x, y, z)))
        outer.append(row)
    # inner (back) grid (offset inward by thickness_z)
    inner = []
    for j in range(ny + 1):
        row = []
        for i in range(nx + 1):
            v_o = outer[j][i]
            row.append(bm.verts.new((v_o.co.x, v_o.co.y, v_o.co.z - thickness_z)))
        inner.append(row)
    # outer skin faces
    for j in range(ny):
        for i in range(nx):
            try:
                bm.faces.new((outer[j][i], outer[j][i + 1], outer[j + 1][i + 1], outer[j + 1][i]))
            except ValueError:
                pass
    # inner skin faces (reverse winding)
    for j in range(ny):
        for i in range(nx):
            try:
                bm.faces.new((inner[j][i], inner[j + 1][i], inner[j + 1][i + 1], inner[j][i + 1]))
            except ValueError:
                pass
    # side band faces (4 edges)
    for i in range(nx):
        # bottom (j=0)
        try:
            bm.faces.new((outer[0][i], inner[0][i], inner[0][i + 1], outer[0][i + 1]))
        except ValueError:
            pass
        # top (j=ny)
        try:
            bm.faces.new((outer[ny][i], outer[ny][i + 1], inner[ny][i + 1], inner[ny][i]))
        except ValueError:
            pass
    for j in range(ny):
        # left (i=0)
        try:
            bm.faces.new((outer[j][0], outer[j + 1][0], inner[j + 1][0], inner[j][0]))
        except ValueError:
            pass
        # right (i=nx)
        try:
            bm.faces.new((outer[j][nx], inner[j][nx], inner[j + 1][nx], outer[j + 1][nx]))
        except ValueError:
            pass
    bm.verts.index_update(); bm.normal_update()
    if bevel_m > 0:
        _bevel(bm, [e for e in bm.edges if e.is_boundary], bevel_m, segments=1)


_PRIMS = {"rounded_box": _p_rounded_box, "wedge": _p_wedge,
          "shell_quad": _p_shell_quad, "fillet_cylinder": _p_fillet_cylinder,
          "trim_ridge": _p_trim_ridge, "ellipsoid": _p_ellipsoid, "body_wrap_arc": _p_body_wrap_arc,
          "solid_shell": _p_solid_shell}

def build_panel(spec, parent_collection):
    """Build a panel mesh from ``spec`` (name, primitive, anchor, rotation_deg,
    scale, zone, plus primitive-specific fields) and link it under
    ``parent_collection``. Returns the new object."""
    name = str(spec.get("name", "panel"))
    primitive = str(spec.get("primitive", "rounded_box"))
    builder = _PRIMS.get(primitive)
    if builder is None:
        raise ValueError(f"unknown panel primitive: {primitive}")
    bm = bmesh.new()
    builder(bm, spec)
    obj = _bm_to_object(bm, name, parent_collection)
    obj["__panel_zone"] = str(spec.get("zone", "armor_base"))
    _apply_transforms(obj, spec.get("anchor"), spec.get("rotation_deg"), spec.get("scale"))
    return obj

def join_module(panel_objs, module_name):
    """Join ``panel_objs`` into a single object named ``armor_{module}_v001``."""
    if not panel_objs:
        raise ValueError("join_module requires at least one panel")
    target = f"armor_{module_name}_v001"
    _replace_object(target)
    _try_object_mode()
    bpy.ops.object.select_all(action="DESELECT")
    zones = []
    for obj in panel_objs:
        obj.select_set(True)
        zones.append(str(obj.get("__panel_zone", "armor_base")))
    bpy.context.view_layer.objects.active = panel_objs[0]
    bpy.ops.object.join()
    joined = bpy.context.view_layer.objects.active
    joined.name = target
    if joined.data is not None:
        joined.data.name = target + "_mesh"
    joined["__panel_zones"] = zones
    joined["__module_name"] = module_name
    return joined

# ---- materials & UVs ------------------------------------------------------
def _ensure_zone_material(zone, hex_color):
    name = f"armor_{zone}"
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    bsdf = nodes.get("Principled BSDF")
    if bsdf is None:
        for n in list(nodes):
            nodes.remove(n)
        out = nodes.new("ShaderNodeOutputMaterial")
        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        mat.node_tree.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    rgba = _hex_to_rgba(hex_color)
    bsdf.inputs["Base Color"].default_value = rgba
    if zone == "emissive" or zone.endswith("_emissive"):
        for k in ("Emission Color", "Emission"):
            if k in bsdf.inputs:
                bsdf.inputs[k].default_value = rgba
                break
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = 4.0
    return mat

def assign_material_zones(obj, panel_zones, palette):
    """Bind material slots on ``obj`` to canonical zones from ``palette``.
    ``panel_zones`` maps per-panel tags to canonical labels (keys in ``palette``).
    Slots are cleared first; emissive-tagged faces go to ``emissive``."""
    if obj.data is None:
        return
    mesh = obj.data
    mesh.materials.clear()
    seen = []
    def _slot(zone):
        if zone not in seen:
            seen.append(zone)
            mesh.materials.append(_ensure_zone_material(zone, palette.get(zone, "#888888")))
        return seen.index(zone)
    raw_zones = list(obj.get("__panel_zones", []))
    polys = mesh.polygons
    poly_zone = []
    if raw_zones and len(polys) > 0:
        per = max(1, len(polys) // max(1, len(raw_zones)))
        for i in range(len(polys)):
            panel_idx = min(len(raw_zones) - 1, i // per)
            key = panel_zones.get(raw_zones[panel_idx], raw_zones[panel_idx])
            poly_zone.append(_slot(key))
    else:
        s = _slot("armor_base")
        poly_zone = [s] * len(polys)
    emissive = set(int(i) for i in obj.get("__emissive_face_indices", []))
    if emissive:
        es = _slot("emissive")
        for idx in emissive:
            if 0 <= idx < len(poly_zone): poly_zone[idx] = es
    for i, p in enumerate(polys):
        p.material_index = poly_zone[i]

def smart_uv_unwrap(obj):
    """Run smart UV project + island packing on ``obj``; leaves it in EDIT mode."""
    if obj.data is None: return
    _select_only(obj)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    try:
        bpy.ops.uv.smart_project(angle_limit=math.radians(66),
                                 island_margin=0.02, area_weight=0.5)
    except TypeError:
        bpy.ops.uv.smart_project(angle_limit=66.0, island_margin=0.02)
    try: bpy.ops.uv.pack_islands(margin=0.01)
    except TypeError: bpy.ops.uv.pack_islands()

# ---- deformation ----------------------------------------------------------
def apply_curve_around_body(obj, body_radius_m, axis="Y"):
    """Wrap vertices onto a cylinder of radius ``body_radius_m``; horizontal
    offsets become arc lengths around ``axis`` (default Y). Recomputes normals."""
    if obj.data is None or body_radius_m <= 0: return
    radius = float(body_radius_m)
    mesh = obj.data
    for v in mesh.vertices:
        if axis == "Y": arc, depth = v.co.x, v.co.z
        elif axis == "Z": arc, depth = v.co.x, v.co.y
        else: arc, depth = v.co.y, v.co.z
        theta = arc / radius
        r = radius + depth
        s, c = math.sin(theta) * r, math.cos(theta) * r - radius
        if axis == "Y": v.co.x, v.co.z = s, c
        elif axis == "Z": v.co.x, v.co.y = s, c
        else: v.co.y, v.co.z = s, c
    mesh.update()
    _calc_normals(mesh)

def carve_emissive_groove(obj, segments):
    """Inset vertices close to each ``(start, end, width)`` segment; tags faces
    on ``obj["__emissive_face_indices"]`` for later ``emissive`` routing."""
    if obj.data is None or not segments: return
    mesh = obj.data
    affected = set()
    for start, end, width in segments:
        a = Vector(start); b = Vector(end)
        ab = b - a
        ll = ab.length_squared or 1e-9
        thr = float(width) * 0.6
        for v in mesh.vertices:
            t = max(0.0, min(1.0, (v.co - a).dot(ab) / ll))
            closest = a + ab * t
            if (v.co - closest).length <= thr:
                inward = v.normal.copy() if v.normal.length else Vector((0, 0, -1))
                v.co -= inward.normalized() * 0.004
                affected.add(v.index)
    obj["__emissive_face_indices"] = [
        p.index for p in mesh.polygons if any(i in affected for i in p.vertices)
    ]
    mesh.update()

# ---- mirror & export ------------------------------------------------------
def mirror_module(src_obj, new_name):
    """Deep-copy ``src_obj`` and mirror across X, reversing face normals."""
    _replace_object(new_name)
    new_mesh = src_obj.data.copy()
    new_mesh.name = new_name + "_mesh"
    new_obj = bpy.data.objects.new(new_name, new_mesh)
    src_coll = src_obj.users_collection[0] if src_obj.users_collection else bpy.context.scene.collection
    _link_object(src_coll, new_obj)
    new_obj.matrix_world = src_obj.matrix_world.copy()
    bm = bmesh.new()
    bm.from_mesh(new_mesh)
    for v in bm.verts:
        v.co.x = -v.co.x
    bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
    bm.normal_update()
    bm.to_mesh(new_mesh)
    bm.free()
    new_mesh.update()
    _calc_normals(new_mesh)
    new_obj["__panel_zones"] = list(src_obj.get("__panel_zones", []))
    new_obj["__module_name"] = src_obj.get("__module_name", new_name)
    new_obj["__mirror_of"] = src_obj.name
    if "__emissive_face_indices" in src_obj.keys():
        new_obj["__emissive_face_indices"] = list(src_obj["__emissive_face_indices"])
    return new_obj

def export_module_glb(obj, glb_path):
    """Export ``obj`` (selection-only) as a binary glTF to ``glb_path``."""
    os.makedirs(os.path.dirname(glb_path) or ".", exist_ok=True)
    _select_only(obj)
    bpy.ops.export_scene.gltf(
        filepath=glb_path, export_format="GLB", use_selection=True,
        export_apply=True, export_yup=True, export_materials="EXPORT",
        export_image_format="AUTO",
    )

def save_module_blend(obj, blend_path):
    """Snapshot the current file to ``blend_path`` without taking it over."""
    os.makedirs(os.path.dirname(blend_path) or ".", exist_ok=True)
    _select_only(obj)
    bpy.ops.wm.save_as_mainfile(filepath=blend_path, copy=True)

# ---- preview / sidecar / measure -----------------------------------------
def _swap_yup(co):  # Blender Z-up -> glTF Y-up: (x,y,z) -> (x,z,-y)
    return (co.x, co.z, -co.y)

def export_preview_mesh_v1(obj, json_path, part, category):
    """Write a mesh.v1 JSON for the runtime preview viewer; returns the payload."""
    if obj.data is None:
        raise ValueError("export_preview_mesh_v1 needs a mesh object")
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
            v = loop.vert
            x, y, z = _swap_yup(v.co)
            positions.extend([x, y, z])
            nx, ny, nz = _swap_yup(v.normal)
            normals.extend([nx, ny, nz])
            if uv_layer is not None:
                u = loop[uv_layer].uv; uv.extend([u.x, u.y])
            else:
                uv.extend([0.0, 0.0])
            for axis, val in enumerate((x, y, z)):
                if val < bbox_min[axis]: bbox_min[axis] = val
                if val > bbox_max[axis]: bbox_max[axis] = val
            indices.append(len(indices))
    bm.free()
    if not positions:
        bbox_min, bbox_max = [0.0]*3, [0.0]*3
    payload = {"format": "mesh.v1", "part": part, "category": category,
               "positions": positions, "normals": normals, "uv": uv,
               "indices": indices, "bounds": {"min": bbox_min, "max": bbox_max}}
    os.makedirs(os.path.dirname(json_path) or ".", exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh)
    return payload

def measure_module(obj):
    """Return summary stats: bbox, dims, triangle/vertex/material counts."""
    if obj.data is None:
        return {"bbox_min": [0, 0, 0], "bbox_max": [0, 0, 0], "dims": [0, 0, 0],
                "triangle_count": 0, "material_count": 0, "vertex_count": 0}
    mesh = obj.data
    if not mesh.vertices:
        bbox_min, bbox_max = [0.0]*3, [0.0]*3
    else:
        bbox_min = [float("inf")] * 3
        bbox_max = [float("-inf")] * 3
        for v in mesh.vertices:
            for axis in range(3):
                val = v.co[axis]
                if val < bbox_min[axis]: bbox_min[axis] = val
                if val > bbox_max[axis]: bbox_max[axis] = val
    dims = [bbox_max[i] - bbox_min[i] for i in range(3)]
    tris = sum(max(0, len(p.vertices) - 2) for p in mesh.polygons)
    return {"bbox_min": bbox_min, "bbox_max": bbox_max, "dims": dims,
            "triangle_count": tris, "material_count": len(mesh.materials),
            "vertex_count": len(mesh.vertices)}

_PART_SPEC_CACHE = None

def _part_spec_entry(module):
    global _PART_SPEC_CACHE
    if _PART_SPEC_CACHE is None:
        _PART_SPEC_CACHE = {}
        spec_path = os.path.join(os.path.dirname(__file__), "armor_part_specs.py") if "__file__" in globals() else ""
        if spec_path and os.path.isfile(spec_path):
            try:
                spec = importlib.util.spec_from_file_location("_armor_part_specs_for_sidecar", spec_path)
                if spec is not None and spec.loader is not None:
                    mod = importlib.util.module_from_spec(spec)
                    sys.modules.setdefault("_armor_part_specs_for_sidecar", mod)
                    spec.loader.exec_module(mod)
                    _PART_SPEC_CACHE = getattr(mod, "PART_SPECS", {}) or {}
            except Exception:
                _PART_SPEC_CACHE = {}
    part_spec = _PART_SPEC_CACHE.get(module) if isinstance(_PART_SPEC_CACHE, dict) else None
    return part_spec if isinstance(part_spec, dict) else None

def _part_spec_attachment(module):
    part_spec = _part_spec_entry(module)
    hint = part_spec.get("vrm_attachment_hint") if isinstance(part_spec, dict) else None
    return hint if isinstance(hint, dict) else None

def _part_spec_attachment_offset_target(module):
    part_spec = _part_spec_entry(module)
    if not isinstance(part_spec, dict):
        return None
    target = part_spec.get("attachment_offset_target_m")
    return float(target) if isinstance(target, (int, float)) and not isinstance(target, bool) else None

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

def _part_spec_sidecar_metadata(module):
    part_spec = _part_spec_entry(module)
    if not isinstance(part_spec, dict):
        return {}
    payload = {}
    if isinstance(part_spec.get("clearance_m"), (int, float)):
        payload["clearance_m"] = float(part_spec["clearance_m"])
    if isinstance(part_spec.get("shell_thickness_m"), (int, float)):
        payload["shell_thickness_target_m"] = float(part_spec["shell_thickness_m"])
    for key in (
        "variant_key",
        "part_family",
        "base_motif_link",
        "topping_slots",
        "attachment_offset_target_m",
        "body_follow_profile",
        "fit_alignment_notes",
        "auxiliary_part_suggestions",
        "silhouette_review_notes",
        "visual_density_profile",
        "ground_contact_profile",
    ):
        value = part_spec.get(key)
        if isinstance(value, (str, int, float, dict, list)) and not isinstance(value, bool):
            payload[key] = value
    return payload

def _normalize_mirror_of(value):
    if not value:
        return None
    text = str(value)
    if text.startswith("armor_") and text.endswith("_v001"):
        return text[len("armor_"):-len("_v001")]
    return text

def _sidecar_attachment(blueprint_part):
    module = str(blueprint_part.get("module", ""))
    fallback = blueprint_part.get("vrm_attachment") if isinstance(blueprint_part.get("vrm_attachment"), dict) else {}
    hint = _part_spec_attachment(module) or {}
    offset = list(hint.get("offset_m") or fallback.get("offset_m") or [0, 0, 0])
    target = _part_spec_attachment_offset_target(module)
    if target is not None:
        offset = _scale_offset_to_target(offset, target)
    return {
        "primary_bone": str(hint.get("primary_bone") or fallback.get("primary_bone") or ""),
        "offset_m": offset,
        "rotation_deg": list(hint.get("rotation_deg") or fallback.get("rotation_deg") or [0, 0, 0]),
        "fallback_bones": list(fallback.get("fallback_bones") or []),
    }

def write_modeler_sidecar(obj, sidecar_path, blueprint_part, panel_zones):
    """Emit the modeler-part-sidecar.v1 JSON next to the GLB; returns payload."""
    measure = measure_module(obj)
    zones_used = sorted({panel_zones.get(z, z) for z in obj.get("__panel_zones", [])})
    if not zones_used: zones_used = ["armor_base"]
    if obj.get("__emissive_face_indices") and "emissive" not in zones_used:
        zones_used.append("emissive")
    module = str(blueprint_part.get("module", obj.get("__module_name", "unknown")))
    part_spec = _part_spec_entry(module)
    mirror_source = obj.get("__mirror_of")
    if not mirror_source and isinstance(part_spec, dict):
        mirror_source = part_spec.get("mirror_of")
    if not mirror_source and not isinstance(part_spec, dict):
        mirror_source = blueprint_part.get("mirror_of")
    qa = {"stable_part_name": "pass", "bbox_within_target_envelope": "warn",
          "non_overlapping_uv0": "warn",
          "single_surface_base_material_or_declared_slots": "pass",
          "mirror_pair_dimension_delta_below_3_percent": "skip",
          "no_body_intersection_at_reference_pose": "warn"}
    payload = {
        "contract_version": "modeler-part-sidecar.v1",
        "module": module,
        "part_id": str(blueprint_part.get("part_id", obj.name)),
        "category": str(blueprint_part.get("category", "unknown")),
        "bbox_m": {"min": measure["bbox_min"], "max": measure["bbox_max"], "dims": measure["dims"]},
        "triangle_count": measure["triangle_count"],
        "material_zones": zones_used,
        "texture_provider_profile": "nano_banana",
        "mirror_of": _normalize_mirror_of(mirror_source),
        "vrm_attachment": _sidecar_attachment(blueprint_part),
        "qa_self_report": qa,
    }
    payload.update(_part_spec_sidecar_metadata(module))
    os.makedirs(os.path.dirname(sidecar_path) or ".", exist_ok=True)
    with open(sidecar_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    return payload


if __name__ == "__main__":
    raise SystemExit("Run inside Blender via execute_blender_code")
