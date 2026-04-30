"""Static validator for armor_part_specs.PART_SPECS.

Catches design-time mistakes in `tools/blender/armor_part_specs.py` without
running Blender:

* predicted per-module AABB derived from panel primitives must stay between
  0.5x and 1.10x of the authoring target envelope (per axis).
* every panel declares a `material_zone` from the allowed palette.
* per-module material zone count is 3 or fewer (warn at 4+).
* mirror modules point at an existing PART_SPECS entry.
* non-mirror modules carry at least one panel.

Run:

    python tools/check_armor_part_specs.py

Exit code 0 = all pass. Exit code 1 = at least one module failed.
"""

from __future__ import annotations

import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any, Iterable


_REPO_ROOT = Path(__file__).resolve().parents[1]
_SPEC_PATH = _REPO_ROOT / "tools" / "blender" / "armor_part_specs.py"
_SNAPSHOT_PATH = _REPO_ROOT / "tools" / "blender" / "_blueprint_snapshot.json"


ALLOWED_MATERIAL_ZONES = {"base_surface", "accent", "emissive", "trim"}
MAX_MATERIAL_ZONES_OK = 3
MAX_MATERIAL_ZONES_WARN = 4
ENVELOPE_UPPER_MULT = 1.10
ENVELOPE_LOWER_MULT = 0.5


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def load_part_specs(spec_path: Path = _SPEC_PATH) -> dict[str, dict[str, Any]]:
    """Import `armor_part_specs` as a standalone module and return PART_SPECS."""

    spec = importlib.util.spec_from_file_location("armor_part_specs", spec_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module spec from {spec_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["armor_part_specs"] = module
    spec.loader.exec_module(module)
    if not hasattr(module, "PART_SPECS"):
        raise RuntimeError("armor_part_specs module is missing PART_SPECS")
    return module.PART_SPECS  # type: ignore[no-any-return]


def load_blueprint_targets(snapshot_path: Path = _SNAPSHOT_PATH) -> dict[str, dict[str, float]]:
    """Read authoring_target_m from the blueprint snapshot, keyed by module."""

    data = json.loads(snapshot_path.read_text(encoding="utf-8"))
    parts = data.get("parts") if isinstance(data.get("parts"), list) else []
    targets: dict[str, dict[str, float]] = {}
    for part in parts:
        if not isinstance(part, dict):
            continue
        module = str(part.get("module") or "").strip()
        if not module:
            continue
        envelope = part.get("target_envelope") if isinstance(part.get("target_envelope"), dict) else {}
        target = envelope.get("authoring_target_m")
        if isinstance(target, dict):
            targets[module] = {
                "x": float(target.get("x", 0.0)),
                "y": float(target.get("y", 0.0)),
                "z": float(target.get("z", 0.0)),
            }
    return targets


# ---------------------------------------------------------------------------
# Per-primitive AABB heuristic
# ---------------------------------------------------------------------------


def _half_diag(sx: float, sy: float, sz: float) -> float:
    """Conservative half-diagonal: covers any rotation of the box."""

    return math.sqrt((sx * 0.5) ** 2 + (sy * 0.5) ** 2 + (sz * 0.5) ** 2)


def _box_aabb_after_rotation(
    sx: float, sy: float, sz: float, rotation_deg: tuple[float, float, float]
) -> tuple[float, float, float]:
    """Return half-extents after rotation_deg about X, Y, Z (in order).

    Rotates the 8 corners of an axis-aligned box centered on origin and
    returns (hx, hy, hz) of the resulting AABB. Cheaper than half-diag
    when only one or two axes are rotated, and tight when no rotation is
    applied (the half-diag heuristic was too pessimistic for accent panels).
    """

    rx, ry, rz = (math.radians(a) for a in rotation_deg)
    cx, cy, cz = math.cos(rx), math.cos(ry), math.cos(rz)
    sxr, syr, szr = math.sin(rx), math.sin(ry), math.sin(rz)
    hx = sx * 0.5
    hy = sy * 0.5
    hz = sz * 0.5
    max_x = max_y = max_z = 0.0
    for ix in (-1, 1):
        for iy in (-1, 1):
            for iz in (-1, 1):
                x, y, z = ix * hx, iy * hy, iz * hz
                # Apply rotations in order X, Y, Z to match Blender extrinsic euler.
                x1, y1, z1 = x, y * cx - z * sxr, y * sxr + z * cx
                x2, y2, z2 = x1 * cy + z1 * syr, y1, -x1 * syr + z1 * cy
                x3, y3, z3 = x2 * cz - y2 * szr, x2 * szr + y2 * cz, z2
                if abs(x3) > max_x:
                    max_x = abs(x3)
                if abs(y3) > max_y:
                    max_y = abs(y3)
                if abs(z3) > max_z:
                    max_z = abs(z3)
    return max_x, max_y, max_z


def _wrap_arc_extent(
    chord_x: float,
    height_y: float,
    depth_z: float,
    arc_deg: float,
    front_bulge: float,
) -> tuple[float, float, float]:
    """Geometric bbox extent (full size, not half) of a body_wrap_arc panel
    in its OWN centered local frame (X and Z recentered around origin).

    Matches the formula in tools/blender/armor_builder_core.py::_p_body_wrap_arc.
    """

    arc_rad = math.radians(arc_deg)
    half = arc_rad * 0.5
    sin_half = math.sin(half) if half > 1e-6 else 1.0
    if arc_deg <= 180.0 and sin_half > 1e-6:
        outer_r = chord_x / 2.0 / sin_half
    else:
        outer_r = chord_x / 2.0
    inner_r = max(1e-3, outer_r - depth_z)
    cos_half = math.cos(half)
    # x extent: 2 * sin(half) * outer_r for arc<=180 (chord_x), or 2*outer_r for arc>180
    if arc_deg <= 180.0:
        x_ext = 2.0 * sin_half * outer_r
    else:
        x_ext = 2.0 * outer_r
    # z extent: max_z (apex+bulge) - min_z (inner verts at theta=±half_arc * cos)
    z_max = outer_r + front_bulge
    z_min = inner_r * cos_half  # for arc<=180, cos>0 -> positive; arc>180, cos<0
    z_ext = z_max - z_min
    return x_ext, height_y, z_ext


def panel_aabb(panel: dict[str, Any]) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """Return ((min_x, min_y, min_z), (max_x, max_y, max_z)) for one panel.

    Per primitive:
      rounded_box / wedge / trim_ridge / solid_shell:
        Tight rotation-aware AABB (no longer half-diag) so accent panels
        rotated about a single axis don't overshoot the prediction.
      shell_quad:
        rotation-aware on x/y; on z, anchor.z +/- (size_z + bulge),
        bulge = min(size_z * 0.4, 0.012).
      body_wrap_arc:
        Geometric formula matching armor_builder_core._p_body_wrap_arc:
        chord_x defines bbox.x for arc<=180°, height_y is bbox.y, and
        bbox.z = (outer_r+bulge) - inner_r*cos(half_arc). The panel is
        centered in its own X/Z frame, so anchor.{x,z} sits at the bbox
        midpoint after rotation.
      fillet_cylinder:
        radius and height as specified.
    """

    primitive = str(panel.get("primitive") or "").strip()
    anchor = panel.get("anchor") or [0.0, 0.0, 0.0]
    size = panel.get("size") or [0.0, 0.0, 0.0]
    rotation_deg = panel.get("rotation_deg") or [0.0, 0.0, 0.0]
    ax, ay, az = (float(anchor[0]), float(anchor[1]), float(anchor[2]))
    sx, sy, sz = (float(size[0]), float(size[1]), float(size[2]))
    rx, ry, rz = (float(rotation_deg[0]), float(rotation_deg[1]), float(rotation_deg[2]))

    if primitive in {"rounded_box", "wedge", "trim_ridge", "solid_shell"}:
        hx, hy, hz = _box_aabb_after_rotation(sx, sy, sz, (rx, ry, rz))
        return (ax - hx, ay - hy, az - hz), (ax + hx, ay + hy, az + hz)

    if primitive == "shell_quad":
        hx, hy, _ = _box_aabb_after_rotation(sx, sy, sz, (rx, ry, rz))
        bulge = min(sz * 0.4, 0.012)
        z_extent = sz + bulge
        return (
            (ax - hx, ay - hy, az - z_extent),
            (ax + hx, ay + hy, az + z_extent),
        )

    if primitive == "body_wrap_arc":
        arc_deg = float(panel.get("arc_deg", 90.0))
        front_bulge = float(panel.get("front_bulge", 0.05))
        x_ext, y_ext, z_ext = _wrap_arc_extent(sx, sy, sz, arc_deg, front_bulge)
        # Rotation: rotate the centered AABB and take new half-extents.
        hx, hy, hz = _box_aabb_after_rotation(x_ext, y_ext, z_ext, (rx, ry, rz))
        return (ax - hx, ay - hy, az - hz), (ax + hx, ay + hy, az + hz)

    if primitive == "fillet_cylinder":
        radius = float(panel.get("radius", max(sx, sz) * 0.5))
        height = float(panel.get("height", sy))
        return (
            (ax - radius, ay - height * 0.5, az - radius),
            (ax + radius, ay + height * 0.5, az + radius),
        )

    # Unknown primitive: fall back to conservative half-diag, but flag.
    h = _half_diag(sx, sy, sz)
    return (ax - h, ay - h, az - h), (ax + h, ay + h, az + h)


def predicted_envelope(panels: Iterable[dict[str, Any]]) -> dict[str, float]:
    """Union AABB of all panels, expressed as full extent on each axis."""

    minx = miny = minz = math.inf
    maxx = maxy = maxz = -math.inf
    for panel in panels:
        (lx, ly, lz), (hx, hy, hz) = panel_aabb(panel)
        minx = min(minx, lx)
        miny = min(miny, ly)
        minz = min(minz, lz)
        maxx = max(maxx, hx)
        maxy = max(maxy, hy)
        maxz = max(maxz, hz)
    if minx == math.inf:
        return {"x": 0.0, "y": 0.0, "z": 0.0}
    return {
        "x": maxx - minx,
        "y": maxy - miny,
        "z": maxz - minz,
    }


# ---------------------------------------------------------------------------
# Per-module checks
# ---------------------------------------------------------------------------


def _silhouette_panels(spec: dict[str, Any]) -> list[dict[str, Any]]:
    silhouette = spec.get("silhouette") if isinstance(spec.get("silhouette"), dict) else {}
    panels = silhouette.get("panels")
    return list(panels) if isinstance(panels, list) else []


def check_module(
    module: str,
    spec: dict[str, Any],
    target: dict[str, float] | None,
    part_specs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    issues: list[str] = []
    warnings: list[str] = []
    status = "pass"

    mirror_of = spec.get("mirror_of")
    silhouette = spec.get("silhouette") if isinstance(spec.get("silhouette"), dict) else {}

    if mirror_of:
        if mirror_of not in part_specs:
            issues.append(f"mirror_of='{mirror_of}' not present in PART_SPECS")
        if silhouette.get("mirror") is not True:
            warnings.append("mirror module silhouette missing 'mirror': True flag")
        return {
            "module": module,
            "is_mirror": True,
            "mirror_of": mirror_of,
            "panels": [],
            "panel_count": 0,
            "predicted": None,
            "target": target,
            "issues": issues,
            "warnings": warnings,
            "status": "fail" if issues else "pass",
            "material_zones": [],
        }

    panels = _silhouette_panels(spec)
    if not panels:
        issues.append("non-mirror module has zero panels in silhouette")

    material_zones: list[str] = []
    seen_zones: set[str] = set()
    panels_summary: list[dict[str, Any]] = []
    for panel in panels:
        zone = str(panel.get("material_zone") or "").strip()
        name = str(panel.get("name") or "")
        primitive = str(panel.get("primitive") or "")
        if not zone:
            issues.append(f"panel '{name}' missing material_zone")
        elif zone not in ALLOWED_MATERIAL_ZONES:
            issues.append(
                f"panel '{name}' material_zone '{zone}' not in {sorted(ALLOWED_MATERIAL_ZONES)}"
            )
        else:
            if zone not in seen_zones:
                material_zones.append(zone)
                seen_zones.add(zone)
        panels_summary.append({"name": name, "primitive": primitive, "zone": zone})

    if len(material_zones) > MAX_MATERIAL_ZONES_OK:
        if len(material_zones) >= MAX_MATERIAL_ZONES_WARN:
            warnings.append(
                f"material zone count {len(material_zones)} >= {MAX_MATERIAL_ZONES_WARN}"
                " (orchestrator merges down to 3)"
            )

    predicted = predicted_envelope(panels) if panels else {"x": 0.0, "y": 0.0, "z": 0.0}

    if target is None:
        warnings.append("no blueprint target_envelope_m available for comparison")
    else:
        for axis in ("x", "y", "z"):
            t = float(target.get(axis, 0.0))
            p = float(predicted.get(axis, 0.0))
            upper = t * ENVELOPE_UPPER_MULT
            lower = t * ENVELOPE_LOWER_MULT
            if t <= 0.0:
                continue
            if p > upper:
                issues.append(
                    f"axis {axis}: predicted {p:.4f} > 1.10x target {t:.4f} (cap {upper:.4f})"
                )
            elif p < lower:
                issues.append(
                    f"axis {axis}: predicted {p:.4f} < 0.50x target {t:.4f} (floor {lower:.4f})"
                )

    if issues:
        status = "fail"
    elif warnings:
        status = "warn"

    return {
        "module": module,
        "is_mirror": False,
        "mirror_of": None,
        "panels": panels_summary,
        "panel_count": len(panels),
        "predicted": predicted,
        "target": target,
        "issues": issues,
        "warnings": warnings,
        "status": status,
        "material_zones": material_zones,
    }


# ---------------------------------------------------------------------------
# Top-level
# ---------------------------------------------------------------------------


def run_checks(
    *,
    spec_path: Path = _SPEC_PATH,
    snapshot_path: Path = _SNAPSHOT_PATH,
) -> dict[str, Any]:
    part_specs = load_part_specs(spec_path)
    targets = load_blueprint_targets(snapshot_path)

    reports: list[dict[str, Any]] = []
    for module in sorted(part_specs.keys()):
        spec = part_specs[module]
        target = targets.get(module)
        reports.append(check_module(module, spec, target, part_specs))

    fails = [r for r in reports if r["status"] == "fail"]
    warns = [r for r in reports if r["status"] == "warn"]
    return {
        "modules": reports,
        "fail_count": len(fails),
        "warn_count": len(warns),
        "pass_count": len(reports) - len(fails) - len(warns),
        "blueprint_modules": sorted(targets.keys()),
        "spec_modules": sorted(part_specs.keys()),
    }


def _fmt_xyz(values: dict[str, float] | None) -> str:
    if not values:
        return "n/a"
    return f"{values.get('x', 0.0):.3f} x {values.get('y', 0.0):.3f} x {values.get('z', 0.0):.3f}"


def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# armor_part_specs static check")
    lines.append("")
    lines.append(
        f"pass={report['pass_count']} warn={report['warn_count']} fail={report['fail_count']}"
    )
    lines.append("")
    lines.append("| module | status | panels | predicted (m) | target (m) | zones | notes |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for r in report["modules"]:
        if r["is_mirror"]:
            note = f"mirror_of={r['mirror_of']}"
            if r["issues"]:
                note += "; " + "; ".join(r["issues"])
            elif r["warnings"]:
                note += "; " + "; ".join(r["warnings"])
            lines.append(
                f"| {r['module']} | {r['status']} | (mirror) | (mirror) | {_fmt_xyz(r['target'])}"
                f" | -- | {note} |"
            )
            continue
        notes_pieces: list[str] = []
        if r["issues"]:
            notes_pieces.extend(r["issues"])
        if r["warnings"]:
            notes_pieces.extend(r["warnings"])
        notes_text = "; ".join(notes_pieces) if notes_pieces else "ok"
        zones = ",".join(r["material_zones"]) if r["material_zones"] else "-"
        lines.append(
            f"| {r['module']} | {r['status']} | {r['panel_count']} |"
            f" {_fmt_xyz(r['predicted'])} | {_fmt_xyz(r['target'])} | {zones} | {notes_text} |"
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    report = run_checks()
    sys.stdout.write(render_markdown(report))
    sys.stdout.write("\n")
    return 1 if report["fail_count"] > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
