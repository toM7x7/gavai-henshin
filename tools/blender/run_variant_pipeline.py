"""Blender orchestrator for armor variants and toppings.

The module is import-safe outside Blender. Dry-run and validation commands only
touch local JSON/Python specs; build commands import ``bpy`` through
``armor_builder_core.py`` at execution time.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import sys
import traceback
from typing import Any


_BLUEPRINT_REL = os.path.join("tools", "blender", "_blueprint_snapshot.json")
_CORE_REL = os.path.join("tools", "blender", "armor_builder_core.py")
_VARIANT_SPEC_REL = os.path.join("tools", "blender", "armor_variant_specs.py")


def _repo_root_from_here() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _import_from_path(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load module '{name}' from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_variant_specs(repo_root: str):
    path = os.path.join(repo_root, _VARIANT_SPEC_REL)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"armor_variant_specs.py missing at {path}")
    return _import_from_path("armor_variant_specs", path)


def _load_core(repo_root: str):
    path = os.path.join(repo_root, _CORE_REL)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"armor_builder_core.py missing at {path}")
    return _import_from_path("armor_builder_core", path)


def _load_blueprint(repo_root: str) -> dict[str, Any]:
    path = os.path.join(repo_root, _BLUEPRINT_REL)
    with open(path, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
    if not isinstance(payload, dict):
        raise ValueError(f"blueprint snapshot must be a JSON object: {path}")
    return payload


def _find_part(blueprint: dict[str, Any], module: str) -> dict[str, Any]:
    for part in blueprint.get("parts", []) or []:
        if isinstance(part, dict) and part.get("module") == module:
            return part
    raise KeyError(f"module {module!r} not found in blueprint snapshot")


def _asset_root(repo_root: str) -> str:
    return os.path.join(repo_root, "viewer", "assets", "armor-parts")


def _variant_paths(repo_root: str, module: str, variant_key: str, specs_mod) -> dict[str, str]:
    slug = specs_mod.asset_key_slug(variant_key)
    stem = f"{module}__{slug}"
    base = os.path.join(_asset_root(repo_root), module, "variants", slug)
    return {
        "asset_dir": base,
        "source_dir": os.path.join(base, "source"),
        "preview_dir": os.path.join(base, "preview"),
        "glb": os.path.join(base, f"{stem}.glb"),
        "blend": os.path.join(base, "source", f"{stem}.blend"),
        "sidecar": os.path.join(base, f"{stem}.modeler.json"),
        "preview_mesh": os.path.join(base, "preview", f"{stem}.mesh.json"),
        "stem": stem,
        "asset_key": slug,
    }


def _topping_paths(repo_root: str, parent_module: str, topping_slot: str, topping_key: str, specs_mod) -> dict[str, str]:
    slot = specs_mod.asset_key_slug(topping_slot)
    key = specs_mod.asset_key_slug(topping_key)
    stem = f"{parent_module}__{slot}__{key}"
    base = os.path.join(_asset_root(repo_root), parent_module, "toppings", slot, key)
    return {
        "asset_dir": base,
        "source_dir": os.path.join(base, "source"),
        "preview_dir": os.path.join(base, "preview"),
        "glb": os.path.join(base, f"{stem}.glb"),
        "blend": os.path.join(base, "source", f"{stem}.blend"),
        "sidecar": os.path.join(base, f"{stem}.modeler.json"),
        "preview_mesh": os.path.join(base, "preview", f"{stem}.mesh.json"),
        "stem": stem,
        "slot": slot,
        "asset_key": key,
    }


def _normalize_panel(panel: dict[str, Any]) -> dict[str, Any]:
    out = dict(panel)
    if "zone" not in out:
        out["zone"] = str(out.get("material_zone") or "base_surface")
    if "size" not in out and "size_m" in out:
        out["size"] = list(out["size_m"])
    if "anchor" not in out and "position_m" in out:
        out["anchor"] = list(out["position_m"])
    out.setdefault("rotation_deg", [0.0, 0.0, 0.0])
    out.setdefault("bevel_m", 0.003)
    return out


def _create_collection(label: str):
    import bpy  # type: ignore

    name = f"build_{label}"
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        try:
            bpy.context.scene.collection.children.link(coll)
        except RuntimeError:
            pass
    return coll


def _safe_save_blend(path: str) -> None:
    import bpy  # type: ignore

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    previous = None
    try:
        previous = bpy.context.preferences.filepaths.save_version
        bpy.context.preferences.filepaths.save_version = 0
    except Exception:
        previous = None
    try:
        bpy.ops.wm.save_as_mainfile(filepath=path, copy=True, compress=True)
    finally:
        if previous is not None:
            try:
                bpy.context.preferences.filepaths.save_version = previous
            except Exception:
                pass


def _apply_runtime_orientation(obj: Any) -> None:
    import bpy  # type: ignore

    try:
        try:
            bpy.ops.object.mode_set(mode="OBJECT")
        except RuntimeError:
            pass
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        obj.rotation_euler = (math.radians(90.0), 0.0, 0.0)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    except Exception:
        pass


def _measure_dict(core: Any, obj: Any) -> dict[str, Any]:
    raw = core.measure_module(obj) or {}
    dims = raw.get("dims") or raw.get("bbox") or [0.0, 0.0, 0.0]
    if isinstance(dims, dict):
        dims_dict = {
            "x": float(dims.get("x") or 0.0),
            "y": float(dims.get("y") or 0.0),
            "z": float(dims.get("z") or 0.0),
        }
    else:
        dims_list = list(dims) if isinstance(dims, (list, tuple)) else [0.0, 0.0, 0.0]
        dims_dict = {
            "x": float(dims_list[0]) if len(dims_list) > 0 else 0.0,
            "y": float(dims_list[1]) if len(dims_list) > 1 else 0.0,
            "z": float(dims_list[2]) if len(dims_list) > 2 else 0.0,
        }
    materials = []
    if getattr(obj, "type", None) == "MESH" and getattr(obj, "data", None) is not None:
        materials = [mat.name for mat in obj.data.materials if mat is not None]
    return {
        "dims": dims_dict,
        "triangles": int(raw.get("triangle_count") or raw.get("triangles") or 0),
        "vertex_count": int(raw.get("vertex_count") or 0),
        "materials": materials,
        "bbox_min": raw.get("bbox_min"),
        "bbox_max": raw.get("bbox_max"),
    }


def _build_object_from_spec(core: Any, spec: dict[str, Any], object_label: str):
    core.reset_scene()
    collection = _create_collection(object_label)
    panels = (spec.get("silhouette") or {}).get("panels") or []
    if not panels:
        raise ValueError(f"{object_label}: no buildable silhouette panels")

    objects = []
    zone_map: dict[str, str] = {}
    for panel in panels:
        if not isinstance(panel, dict):
            continue
        normalized = _normalize_panel(panel)
        obj = core.build_panel(normalized, collection)
        objects.append(obj)
        zone = str(normalized.get("zone") or "base_surface")
        zone_map[zone] = zone

    joined = core.join_module(objects, object_label)
    for groove in spec.get("emissive_lines") or []:
        if hasattr(core, "carve_emissive_groove"):
            segments = groove
            if isinstance(groove, dict):
                segments = [(
                    tuple(groove.get("start") or [0.0, 0.0, 0.0]),
                    tuple(groove.get("end") or [0.0, 0.0, 0.0]),
                    float(groove.get("width_m") or 0.01),
                )]
            core.carve_emissive_groove(joined, segments)

    palette = spec.get("material_zones_palette")
    if not isinstance(palette, dict):
        palette = {
            "base_surface": "#E8EEF5",
            "accent": "#1B6FE0",
            "emissive": "#2EE6FF",
            "trim": "#1A2230",
        }
    core.assign_material_zones(joined, zone_map, palette)
    core.smart_uv_unwrap(joined)
    _apply_runtime_orientation(joined)
    if getattr(joined, "type", None) == "MESH" and getattr(joined, "data", None) is not None:
        joined.data.name = joined.name
    return joined


def _write_preview_mesh(core: Any, obj: Any, path: str, part: str, category: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    core.export_preview_mesh_v1(obj, path, part, category)


def _write_sidecar(path: str, payload: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)


def _export_deliverables(core: Any, obj: Any, paths: dict[str, str], preview_part: str, category: str) -> None:
    for key in ("asset_dir", "source_dir", "preview_dir"):
        os.makedirs(paths[key], exist_ok=True)
    core.export_module_glb(obj, paths["glb"])
    _safe_save_blend(paths["blend"])
    _write_preview_mesh(core, obj, paths["preview_mesh"], preview_part, category)


def _report_base(asset_kind: str, paths: dict[str, str]) -> dict[str, Any]:
    return {
        "asset_kind": asset_kind,
        "ok": False,
        "paths": {
            "glb": paths.get("glb"),
            "blend": paths.get("blend"),
            "sidecar": paths.get("sidecar"),
            "preview_mesh": paths.get("preview_mesh"),
        },
        "dims": {"x": 0.0, "y": 0.0, "z": 0.0},
        "triangles": 0,
        "materials": [],
        "warnings": [],
        "errors": [],
    }


def build_variant(module: str, variant_key: str, repo_root: str | None = None) -> dict[str, Any]:
    repo_root = os.path.abspath(repo_root or _repo_root_from_here())
    specs_mod = _load_variant_specs(repo_root)
    spec = specs_mod.get_variant_spec(module, variant_key, repo_root)
    paths = _variant_paths(repo_root, module, spec["variant_key"], specs_mod)
    report = _report_base("variant", paths)
    report.update({"module": module, "variant_key": spec["variant_key"], "variant_asset_key": paths["asset_key"]})
    try:
        blueprint = _load_blueprint(repo_root)
        part = _find_part(blueprint, module)
        core = _load_core(repo_root)
        obj = _build_object_from_spec(core, spec, paths["stem"])
        measure = _measure_dict(core, obj)
        _export_deliverables(core, obj, paths, module, str(part.get("category") or "armor"))
        sidecar = {
            "contract_version": "modeler-part-variant-sidecar.v1",
            "asset_kind": "variant",
            "module": module,
            "variant_key": spec["variant_key"],
            "variant_asset_key": paths["asset_key"],
            "base_motif_link": spec.get("base_motif_link"),
            "catalog_ref": spec.get("catalog_ref"),
            "catalog_variant": spec.get("catalog_variant"),
            "bbox_m": {"x": measure["dims"]["x"], "y": measure["dims"]["y"], "z": measure["dims"]["z"]},
            "triangle_count": measure["triangles"],
            "material_zones": measure["materials"],
            "source_canonical_module": module,
            "preserves_canonical_part": True,
            "coordinate_frame": "glTF Y-up export; authored x=lateral, y=vertical, z=outward",
        }
        _write_sidecar(paths["sidecar"], sidecar)
        report.update({
            "ok": True,
            "dims": measure["dims"],
            "triangles": measure["triangles"],
            "materials": measure["materials"],
        })
    except Exception as exc:  # noqa: BLE001
        report["errors"].append(f"{type(exc).__name__}: {exc}")
        report["traceback"] = traceback.format_exc()
    return report


def build_topping(
    parent_module: str,
    topping_slot: str,
    topping_key: str = "base",
    repo_root: str | None = None,
) -> dict[str, Any]:
    repo_root = os.path.abspath(repo_root or _repo_root_from_here())
    specs_mod = _load_variant_specs(repo_root)
    spec = specs_mod.get_topping_spec(parent_module, topping_slot, topping_key, repo_root)
    paths = _topping_paths(repo_root, parent_module, spec["topping_slot"], spec["topping_key"], specs_mod)
    report = _report_base("topping", paths)
    report.update({
        "parent_module": parent_module,
        "topping_slot": spec["topping_slot"],
        "topping_key": spec["topping_key"],
    })
    try:
        blueprint = _load_blueprint(repo_root)
        _find_part(blueprint, parent_module)
        core = _load_core(repo_root)
        obj = _build_object_from_spec(core, spec, paths["stem"])
        measure = _measure_dict(core, obj)
        _export_deliverables(core, obj, paths, paths["stem"], "topping")
        sidecar = {
            "contract_version": "modeler-topping-sidecar.v1",
            "asset_kind": "topping",
            "parent_module": parent_module,
            "topping_slot": spec["topping_slot"],
            "topping_key": spec["topping_key"],
            "slot_transform": spec.get("slot_transform"),
            "max_bbox_m": spec.get("max_bbox_m"),
            "conflicts_with": spec.get("conflicts_with"),
            "catalog_ref": spec.get("catalog_ref"),
            "catalog_topping_slot": spec.get("catalog_topping_slot"),
            "bbox_m": {"x": measure["dims"]["x"], "y": measure["dims"]["y"], "z": measure["dims"]["z"]},
            "triangle_count": measure["triangles"],
            "material_zones": measure["materials"],
            "coordinate_frame": "parent-module local authored frame; glTF Y-up export",
        }
        _write_sidecar(paths["sidecar"], sidecar)
        report.update({
            "ok": True,
            "dims": measure["dims"],
            "triangles": measure["triangles"],
            "materials": measure["materials"],
        })
    except Exception as exc:  # noqa: BLE001
        report["errors"].append(f"{type(exc).__name__}: {exc}")
        report["traceback"] = traceback.format_exc()
    return report


def build_p0(repo_root: str | None = None, *, kind: str = "all", topping_key: str = "base") -> dict[str, Any]:
    repo_root = os.path.abspath(repo_root or _repo_root_from_here())
    specs_mod = _load_variant_specs(repo_root)
    results: dict[str, Any] = {"repo_root": repo_root, "kind": kind, "variants": [], "toppings": []}
    if kind in {"all", "variants"}:
        for spec in specs_mod.iter_variant_specs(repo_root, p0_only=True):
            results["variants"].append(build_variant(spec["module"], spec["variant_key"], repo_root))
    if kind in {"all", "toppings"}:
        for spec in specs_mod.iter_topping_specs(repo_root, p0_only=True, topping_key=topping_key):
            results["toppings"].append(build_topping(spec["parent_module"], spec["topping_slot"], spec["topping_key"], repo_root))
    total = len(results["variants"]) + len(results["toppings"])
    ok = sum(1 for key in ("variants", "toppings") for item in results[key] if item.get("ok"))
    results["ok"] = ok == total
    results["ok_count"] = ok
    results["fail_count"] = total - ok
    return results


def dry_run(repo_root: str | None = None, *, kind: str = "all", p0_only: bool = True, topping_key: str = "base") -> dict[str, Any]:
    repo_root = os.path.abspath(repo_root or _repo_root_from_here())
    specs_mod = _load_variant_specs(repo_root)
    payload: dict[str, Any] = {
        "ok": True,
        "repo_root": repo_root,
        "kind": kind,
        "p0_only": p0_only,
        "validation": specs_mod.validate(repo_root, p0_only=p0_only),
        "planned_variants": [],
        "planned_toppings": [],
    }
    if kind in {"all", "variants"}:
        for spec in specs_mod.iter_variant_specs(repo_root, p0_only=p0_only):
            paths = _variant_paths(repo_root, spec["module"], spec["variant_key"], specs_mod)
            payload["planned_variants"].append({
                "module": spec["module"],
                "variant_key": spec["variant_key"],
                "output_dir": paths["asset_dir"],
                "glb": paths["glb"],
                "sidecar": paths["sidecar"],
            })
    if kind in {"all", "toppings"}:
        for spec in specs_mod.iter_topping_specs(repo_root, p0_only=p0_only, topping_key=topping_key):
            paths = _topping_paths(repo_root, spec["parent_module"], spec["topping_slot"], spec["topping_key"], specs_mod)
            payload["planned_toppings"].append({
                "parent_module": spec["parent_module"],
                "topping_slot": spec["topping_slot"],
                "topping_key": spec["topping_key"],
                "output_dir": paths["asset_dir"],
                "glb": paths["glb"],
                "sidecar": paths["sidecar"],
            })
    payload["ok"] = bool(payload["validation"].get("ok"))
    return payload


def _print_json(payload: Any) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate or build armor variant/topping assets.")
    parser.add_argument("--repo-root", default=_repo_root_from_here())
    sub = parser.add_subparsers(dest="command", required=True)

    validate_p = sub.add_parser("validate", help="Validate local variant catalog/spec integration.")
    validate_p.add_argument("--p0-only", action="store_true")

    dry_p = sub.add_parser("dry-run", help="Print planned outputs without importing Blender.")
    dry_p.add_argument("--kind", choices=("all", "variants", "toppings"), default="all")
    dry_p.add_argument("--all-modules", action="store_true", help="Plan all 18 modules instead of P0 only.")
    dry_p.add_argument("--topping-key", default="base")

    bv = sub.add_parser("build-variant", help="Build one variant. Run inside Blender.")
    bv.add_argument("--module", required=True)
    bv.add_argument("--variant-key", required=True)

    bt = sub.add_parser("build-topping", help="Build one topping. Run inside Blender.")
    bt.add_argument("--parent-module", required=True)
    bt.add_argument("--topping-slot", required=True)
    bt.add_argument("--topping-key", default="base")

    bp0 = sub.add_parser("build-p0", help="Build P0 variants and/or toppings. Run inside Blender.")
    bp0.add_argument("--kind", choices=("all", "variants", "toppings"), default="all")
    bp0.add_argument("--topping-key", default="base")
    return parser


def main(argv: list[str] | None = None) -> int:
    if argv is None and "--" in sys.argv:
        argv = sys.argv[sys.argv.index("--") + 1 :]
    parser = _build_parser()
    args = parser.parse_args(argv)
    repo_root = os.path.abspath(args.repo_root)
    specs_mod = _load_variant_specs(repo_root)

    if args.command == "validate":
        payload = specs_mod.validate(repo_root, p0_only=bool(args.p0_only))
        _print_json(payload)
        return 0 if payload.get("ok") else 1
    if args.command == "dry-run":
        payload = dry_run(repo_root, kind=args.kind, p0_only=not args.all_modules, topping_key=args.topping_key)
        _print_json(payload)
        return 0 if payload.get("ok") else 1
    if args.command == "build-variant":
        payload = build_variant(args.module, args.variant_key, repo_root)
        _print_json(payload)
        return 0 if payload.get("ok") else 1
    if args.command == "build-topping":
        payload = build_topping(args.parent_module, args.topping_slot, args.topping_key, repo_root)
        _print_json(payload)
        return 0 if payload.get("ok") else 1
    if args.command == "build-p0":
        payload = build_p0(repo_root, kind=args.kind, topping_key=args.topping_key)
        _print_json(payload)
        return 0 if payload.get("ok") else 1
    parser.error(f"unknown command {args.command!r}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
