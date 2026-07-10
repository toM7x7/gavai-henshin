"""Variant and topping specs for procedural armor asset builds.

This module is intentionally Blender-free. It reads the static variant catalog
and derives buildable panel specs from the canonical 18 armor part specs.
"""

from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
import os
import re
import sys
from typing import Any


SPEC_CONTRACT_VERSION = "armor-variant-spec.v1"
CATALOG_CONTRACT_VERSION = "armor-part-variant-catalog.v1"
CATALOG_REL = os.path.join("viewer", "assets", "armor-parts", "variant_catalog.json")

CANONICAL_MODULES: tuple[str, ...] = (
    "helmet",
    "chest",
    "back",
    "waist",
    "left_shoulder",
    "right_shoulder",
    "left_upperarm",
    "right_upperarm",
    "left_forearm",
    "right_forearm",
    "left_hand",
    "right_hand",
    "left_thigh",
    "right_thigh",
    "left_shin",
    "right_shin",
    "left_boot",
    "right_boot",
)

P0_MODULES: tuple[str, ...] = (
    "helmet",
    "chest",
    "back",
    "waist",
    "left_shoulder",
    "right_shoulder",
    "left_shin",
    "right_shin",
)

P0_REQUIRED_TOPPING_SLOTS: dict[str, tuple[str, ...]] = {
    "helmet": ("crest", "visor_trim"),
    "chest": ("chest_core", "rib_trim"),
    "back": ("spine_ridge", "rear_core"),
    "waist": ("belt_buckle", "side_clip"),
    "left_shoulder": ("shoulder_fin", "edge_trim"),
    "right_shoulder": ("shoulder_fin", "edge_trim"),
    "left_shin": ("shin_spike", "ankle_cuff_trim"),
    "right_shin": ("shin_spike", "ankle_cuff_trim"),
}

MATERIAL_PALETTE: dict[str, str] = {
    "base_surface": "#E8EEF5",
    "accent": "#1B6FE0",
    "emissive": "#2EE6FF",
    "trim": "#1A2230",
}

_ASSET_KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _module_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def _repo_root_from_here() -> str:
    return os.path.abspath(os.path.join(_module_dir(), "..", ".."))


def _import_from_path(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"could not load module '{name}' from {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _load_part_specs() -> dict[str, dict[str, Any]]:
    path = os.path.join(_module_dir(), "armor_part_specs.py")
    mod = _import_from_path("_armor_part_specs_for_variants", path)
    specs = getattr(mod, "PART_SPECS", None)
    if not isinstance(specs, dict):
        raise ValueError("armor_part_specs.PART_SPECS is missing or invalid")
    return specs


def catalog_path(repo_root: str | None = None) -> str:
    root = os.path.abspath(repo_root or _repo_root_from_here())
    return os.path.join(root, CATALOG_REL)


def load_catalog(repo_root: str | None = None) -> dict[str, Any]:
    path = catalog_path(repo_root)
    with open(path, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
    if not isinstance(payload, dict):
        raise ValueError(f"variant catalog must be a JSON object: {path}")
    return payload


def modules_from_catalog(catalog: dict[str, Any]) -> dict[str, Any]:
    modules = catalog.get("modules", catalog.get("parts"))
    if not isinstance(modules, dict):
        raise ValueError("variant catalog must expose a modules object")
    return modules


def asset_key_slug(value: str) -> str:
    """Return a path-safe local key.

    Catalog variant keys are canonical strings such as ``helmet:sleek``. Windows
    paths cannot use ``:``, so asset directories use the local segment.
    """
    text = str(value or "").strip()
    if ":" in text:
        text = text.split(":", 1)[1]
    text = text.replace("-", "_").lower()
    if not _ASSET_KEY_RE.fullmatch(text):
        raise ValueError(f"asset key must be lowercase snake_case: {value!r}")
    if text in {".", ".."} or "/" in text or "\\" in text:
        raise ValueError(f"asset key is not path-safe: {value!r}")
    return text


def canonical_variant_key(module: str, variant_key: str) -> str:
    slug = asset_key_slug(variant_key)
    text = str(variant_key or "").strip()
    if ":" in text:
        prefix, local = text.split(":", 1)
        if prefix and prefix != module:
            raise ValueError(f"variant key {variant_key!r} does not belong to {module!r}")
        return f"{module}:{asset_key_slug(local)}"
    return f"{module}:{slug}"


def _variant_records(module: str, catalog: dict[str, Any]) -> list[dict[str, Any]]:
    module_payload = modules_from_catalog(catalog).get(module)
    if not isinstance(module_payload, dict):
        raise KeyError(f"module {module!r} not found in variant catalog")
    raw = module_payload.get("variants")
    if isinstance(raw, dict):
        records = []
        for key, value in raw.items():
            if isinstance(value, dict):
                record = {"variant_key": value.get("variant_key", key), **value}
                records.append(record)
        return records
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    return []


def find_variant_record(module: str, variant_key: str, catalog: dict[str, Any]) -> dict[str, Any]:
    wanted = canonical_variant_key(module, variant_key)
    for record in _variant_records(module, catalog):
        if str(record.get("variant_key") or "") == wanted:
            return deepcopy(record)
    raise KeyError(f"variant {wanted!r} not found in catalog")


def _topping_slots(module: str, catalog: dict[str, Any]) -> list[dict[str, Any]]:
    module_payload = modules_from_catalog(catalog).get(module)
    if not isinstance(module_payload, dict):
        raise KeyError(f"module {module!r} not found in variant catalog")
    raw = module_payload.get("topping_slots")
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def find_topping_slot(module: str, topping_slot: str, catalog: dict[str, Any]) -> dict[str, Any]:
    wanted = asset_key_slug(topping_slot)
    for slot in _topping_slots(module, catalog):
        if str(slot.get("topping_slot") or "") == wanted:
            return deepcopy(slot)
    raise KeyError(f"topping slot {wanted!r} not found for {module!r}")


def _base_part_spec(module: str) -> dict[str, Any]:
    specs = _load_part_specs()
    spec = specs.get(module)
    if not isinstance(spec, dict):
        raise KeyError(f"canonical PART_SPECS missing {module!r}")
    return deepcopy(spec)


def _left_source_for(module: str) -> str | None:
    if module.startswith("right_"):
        return "left_" + module[len("right_"):]
    return None


def _mirror_panel_x(panel: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(panel)
    out["name"] = str(out.get("name") or "panel").replace("left", "right")
    anchor = list(out.get("anchor") or out.get("position_m") or [0.0, 0.0, 0.0])
    if len(anchor) >= 1:
        anchor[0] = -float(anchor[0])
    out["anchor"] = anchor
    rotation = list(out.get("rotation_deg") or [0.0, 0.0, 0.0])
    if len(rotation) >= 2:
        rotation[1] = -float(rotation[1])
    if len(rotation) >= 3:
        rotation[2] = -float(rotation[2])
    out["rotation_deg"] = rotation
    return out


def _mirror_variant_spec_x(spec: dict[str, Any], module: str, variant_key: str) -> dict[str, Any]:
    out = deepcopy(spec)
    out["module"] = module
    out["side"] = "right"
    out["mirror_of"] = _left_source_for(module)
    out["variant_key"] = canonical_variant_key(module, variant_key)
    silhouette = deepcopy(out.get("silhouette") or {})
    panels = silhouette.get("panels") or []
    silhouette["panels"] = [_mirror_panel_x(p) for p in panels if isinstance(p, dict)]
    out["silhouette"] = silhouette
    hint = out.get("vrm_attachment_hint")
    if isinstance(hint, dict):
        offset = list(hint.get("offset_m") or [0.0, 0.0, 0.0])
        if offset:
            offset[0] = -float(offset[0])
        hint["offset_m"] = offset
        bone = str(hint.get("primary_bone") or "")
        hint["primary_bone"] = bone.replace("left", "right").replace("Left", "Right")
    return out


def _envelope(spec: dict[str, Any]) -> dict[str, float]:
    raw = spec.get("target_envelope_m") or {}
    return {
        "x": float(raw.get("x") or 0.2),
        "y": float(raw.get("y") or 0.2),
        "z": float(raw.get("z") or 0.08),
    }


def _panel(
    name: str,
    primitive: str,
    anchor: tuple[float, float, float],
    size: tuple[float, float, float],
    *,
    rotation_deg: tuple[float, float, float] = (0.0, 0.0, 0.0),
    material_zone: str = "accent",
    bevel_m: float = 0.003,
    **extras: Any,
) -> dict[str, Any]:
    out = {
        "name": name,
        "primitive": primitive,
        "anchor": list(anchor),
        "size": list(size),
        "rotation_deg": list(rotation_deg),
        "material_zone": material_zone,
        "bevel_m": bevel_m,
    }
    out.update(extras)
    return out


def _side_sign(module: str) -> float:
    if module.startswith("right_"):
        return -1.0
    return 1.0


def _variant_overlay_panels(module: str, style: str, envelope: dict[str, float]) -> list[dict[str, Any]]:
    if style == "base":
        return []
    ex, ey, ez = envelope["x"], envelope["y"], envelope["z"]
    sx = _side_sign(module)
    prefix = f"{module}_{style}"

    if module == "helmet":
        if style == "sleek":
            return [
                _panel(f"{prefix}_visor_pin", "trim_ridge", (0.0, ey * 0.08, ez * 0.47), (ex * 0.78, ey * 0.055, 0.010), material_zone="emissive"),
                _panel(f"{prefix}_jaw_slit", "trim_ridge", (0.0, -ey * 0.30, ez * 0.38), (ex * 0.46, 0.010, 0.010), material_zone="trim"),
            ]
        return [
            _panel(f"{prefix}_brow_guard", "rounded_box", (0.0, ey * 0.10, ez * 0.48), (ex * 0.90, ey * 0.10, 0.024), material_zone="accent"),
            _panel(f"{prefix}_crest_blade", "wedge", (0.0, ey * 0.39, 0.0), (0.030, ey * 0.34, ez * 0.72), material_zone="accent", front_z_taper=0.9),
        ]
    if module == "chest":
        if style == "sleek":
            return [
                _panel(f"{prefix}_sternum_trace", "trim_ridge", (0.0, 0.0, ez * 0.48), (ex * 0.045, ey * 0.62, 0.010), material_zone="emissive"),
                _panel(f"{prefix}_rib_line_l", "trim_ridge", (ex * 0.28, -ey * 0.08, ez * 0.32), (ex * 0.22, 0.012, 0.010), rotation_deg=(0.0, -12.0, -8.0), material_zone="accent"),
                _panel(f"{prefix}_rib_line_r", "trim_ridge", (-ex * 0.28, -ey * 0.08, ez * 0.32), (ex * 0.22, 0.012, 0.010), rotation_deg=(0.0, 12.0, 8.0), material_zone="accent"),
            ]
        return [
            _panel(f"{prefix}_sternum_core", "rounded_box", (0.0, ey * 0.02, ez * 0.50), (ex * 0.18, ey * 0.22, 0.030), material_zone="accent"),
            _panel(f"{prefix}_core_light", "rounded_box", (0.0, ey * 0.02, ez * 0.52), (ex * 0.07, ey * 0.12, 0.012), material_zone="emissive"),
        ]
    if module == "back":
        z = -ez * 0.48
        if style == "sleek":
            return [_panel(f"{prefix}_spine_pin", "trim_ridge", (0.0, 0.0, z), (ex * 0.055, ey * 0.78, 0.010), material_zone="emissive")]
        return [
            _panel(f"{prefix}_rear_core", "rounded_box", (0.0, ey * 0.10, z), (ex * 0.22, ey * 0.22, 0.030), material_zone="accent"),
            _panel(f"{prefix}_spine_block", "rounded_box", (0.0, -ey * 0.15, z), (ex * 0.10, ey * 0.38, 0.026), material_zone="accent"),
        ]
    if module == "waist":
        if style == "sleek":
            return [_panel(f"{prefix}_driver_line", "trim_ridge", (0.0, 0.0, ez * 0.48), (ex * 0.40, ey * 0.16, 0.010), material_zone="emissive")]
        return [
            _panel(f"{prefix}_driver_buckle", "rounded_box", (0.0, 0.0, ez * 0.48), (ex * 0.28, ey * 0.80, 0.030), material_zone="accent"),
            _panel(f"{prefix}_buckle_lens", "rounded_box", (0.0, 0.0, ez * 0.51), (ex * 0.10, ey * 0.52, 0.010), material_zone="emissive"),
        ]
    if "shoulder" in module:
        if style == "sleek":
            return [_panel(f"{prefix}_edge_signal", "trim_ridge", (sx * ex * 0.40, 0.0, ez * 0.28), (0.012, ey * 0.86, ez * 0.32), material_zone="emissive")]
        return [_panel(f"{prefix}_fin", "wedge", (sx * ex * 0.38, ey * 0.08, ez * 0.28), (0.030, ey * 0.86, ez * 0.44), rotation_deg=(0.0, sx * -8.0, 0.0), material_zone="accent", front_z_taper=0.8)]
    if "shin" in module:
        if style == "sleek":
            return [
                _panel(f"{prefix}_center_trace", "trim_ridge", (0.0, 0.0, ez * 0.48), (ex * 0.070, ey * 0.70, 0.010), material_zone="emissive"),
                _panel(f"{prefix}_ankle_line", "trim_ridge", (0.0, -ey * 0.42, ez * 0.20), (ex * 0.78, 0.012, 0.018), material_zone="trim"),
            ]
        return [
            _panel(f"{prefix}_shin_blade", "wedge", (0.0, ey * 0.04, ez * 0.48), (ex * 0.32, ey * 0.48, 0.030), material_zone="accent", front_z_taper=1.0),
            _panel(f"{prefix}_knee_guard", "rounded_box", (0.0, ey * 0.43, ez * 0.36), (ex * 0.70, ey * 0.12, 0.028), material_zone="accent"),
        ]
    if "boot" in module and style != "base":
        return [_panel(f"{prefix}_sole_signal", "trim_ridge", (0.0, -ey * 0.44, ez * 0.08), (ex * 0.80, 0.010, ez * 0.52), material_zone="trim")]

    return [_panel(f"{prefix}_detail_ridge", "trim_ridge", (sx * ex * 0.34, 0.0, ez * 0.34), (0.010, ey * 0.45, 0.010), material_zone="accent")]


def get_variant_spec(module: str, variant_key: str, repo_root: str | None = None) -> dict[str, Any]:
    if module not in CANONICAL_MODULES:
        raise KeyError(f"unknown canonical module {module!r}")

    left_source = _left_source_for(module)
    if left_source:
        local_key = asset_key_slug(variant_key)
        left_spec = get_variant_spec(left_source, f"{left_source}:{local_key}", repo_root)
        spec = _mirror_variant_spec_x(left_spec, module, f"{module}:{local_key}")
    else:
        catalog = load_catalog(repo_root)
        record = find_variant_record(module, variant_key, catalog)
        spec = _base_part_spec(module)
        local_key = asset_key_slug(str(record.get("variant_key") or variant_key))
        spec["variant_key"] = canonical_variant_key(module, str(record.get("variant_key") or variant_key))
        silhouette = deepcopy(spec.get("silhouette") or {})
        panels = list(silhouette.get("panels") or [])
        panels.extend(_variant_overlay_panels(module, local_key, _envelope(spec)))
        silhouette["panels"] = panels
        spec["silhouette"] = silhouette

    catalog = load_catalog(repo_root)
    record = find_variant_record(module, variant_key, catalog)
    module_catalog = modules_from_catalog(catalog).get(module) or {}
    spec["contract_version"] = SPEC_CONTRACT_VERSION
    spec["asset_kind"] = "variant"
    spec["module"] = module
    spec["variant_key"] = canonical_variant_key(module, variant_key)
    spec["variant_asset_key"] = asset_key_slug(variant_key)
    spec["display_name"] = record.get("display_name") or record.get("label") or spec["variant_asset_key"]
    spec["base_motif_link"] = deepcopy(record.get("base_motif_link") or module_catalog.get("base_motif_link") or spec.get("base_motif_link") or {})
    spec["catalog_ref"] = {
        "path": CATALOG_REL.replace(os.sep, "/"),
        "contract_version": CATALOG_CONTRACT_VERSION,
        "module": module,
        "variant_key": spec["variant_key"],
    }
    spec["catalog_variant"] = deepcopy(record)
    if isinstance(module_catalog, dict):
        spec["catalog_topping_slots"] = deepcopy(module_catalog.get("topping_slots") or [])
    return spec


def _canonical_material_zone(value: Any) -> str:
    text = str(value or "").lower()
    if "emissive" in text or "glow" in text or "lens" in text:
        return "emissive"
    if "trim" in text or "cuff" in text or "sole" in text or "vent" in text:
        return "trim"
    if "base" in text or "surface" in text:
        return "base_surface"
    return "accent"


def _slot_transform_from_part_spec(parent_module: str, topping_slot: str) -> dict[str, Any] | None:
    spec = _base_part_spec(parent_module)
    for slot in spec.get("topping_slots") or []:
        if isinstance(slot, dict) and slot.get("topping_slot") == topping_slot:
            transform = slot.get("slot_transform")
            if isinstance(transform, dict):
                return deepcopy(transform)
    return None


def _slot_anchor_from_hint(parent_module: str, slot_record: dict[str, Any], parent_spec: dict[str, Any]) -> list[float]:
    env = _envelope(parent_spec)
    surface = str((slot_record.get("anchor_hint") or {}).get("parent_surface") or "").lower()
    side = _side_sign(parent_module)
    x = 0.0
    y = 0.0
    z = 0.0
    if any(token in surface for token in ("left_right", "sides", "outer", "cap_edges")):
        x = side * env["x"] * 0.36
    if any(token in surface for token in ("front", "motif_linked")):
        z = env["z"] * 0.43
    if any(token in surface for token in ("rear", "back")):
        z = -env["z"] * 0.43
    if any(token in surface for token in ("top", "upper", "crown")):
        y = env["y"] * 0.35
    if any(token in surface for token in ("lower", "bottom", "ankle")):
        y = -env["y"] * 0.35
    return [round(x, 5), round(y, 5), round(z, 5)]


def _slot_transform(parent_module: str, topping_slot: str, slot_record: dict[str, Any], parent_spec: dict[str, Any]) -> dict[str, Any]:
    transform = slot_record.get("slot_transform")
    if not isinstance(transform, dict):
        transform = _slot_transform_from_part_spec(parent_module, topping_slot)
    if not isinstance(transform, dict):
        transform = {"anchor": _slot_anchor_from_hint(parent_module, slot_record, parent_spec), "rotation_deg": [0.0, 0.0, 0.0]}
    out = deepcopy(transform)
    out.setdefault("anchor", [0.0, 0.0, 0.0])
    out.setdefault("rotation_deg", [0.0, 0.0, 0.0])
    return out


def _bbox_tuple(slot_record: dict[str, Any]) -> tuple[float, float, float]:
    raw = slot_record.get("max_bbox_m") or {}
    return (
        max(0.006, float(raw.get("x") or 0.05)),
        max(0.006, float(raw.get("y") or 0.05)),
        max(0.006, float(raw.get("z") or 0.02)),
    )


def _topping_panels(
    parent_module: str,
    topping_slot: str,
    topping_key: str,
    slot_record: dict[str, Any],
    transform: dict[str, Any],
) -> list[dict[str, Any]]:
    bx, by, bz = _bbox_tuple(slot_record)
    key = asset_key_slug(topping_key)
    scale = {"base": 0.62, "sleek": 0.50, "bold": 0.78}.get(key, 0.62)
    anchor = tuple(float(v) for v in (transform.get("anchor") or [0.0, 0.0, 0.0])[:3])
    rotation = tuple(float(v) for v in (transform.get("rotation_deg") or [0.0, 0.0, 0.0])[:3])
    zone = _canonical_material_zone(slot_record.get("material_zone"))
    prefix = f"{parent_module}_{topping_slot}_{key}"

    if any(token in topping_slot for token in ("fin", "spike", "crest", "vane")):
        return [
            _panel(prefix, "wedge", anchor, (bx * scale, by * scale, bz * scale), rotation_deg=rotation, material_zone=zone, front_z_taper=0.9)
        ]
    if any(token in topping_slot for token in ("trim", "cuff", "band", "rib", "sole", "rail")):
        return [
            _panel(prefix, "trim_ridge", anchor, (bx * scale, by * scale, bz * 0.55), rotation_deg=rotation, material_zone=zone)
        ]
    panels = [
        _panel(prefix, "rounded_box", anchor, (bx * scale, by * scale, bz * scale), rotation_deg=rotation, material_zone=zone)
    ]
    if key == "bold":
        cap_anchor = (anchor[0], anchor[1], anchor[2] + bz * 0.20)
        panels.append(_panel(f"{prefix}_lens", "rounded_box", cap_anchor, (bx * 0.34, by * 0.34, max(0.006, bz * 0.20)), rotation_deg=rotation, material_zone="emissive"))
    return panels


def get_topping_spec(
    parent_module: str,
    topping_slot: str,
    topping_key: str = "base",
    repo_root: str | None = None,
) -> dict[str, Any]:
    if parent_module not in CANONICAL_MODULES:
        raise KeyError(f"unknown canonical module {parent_module!r}")
    catalog = load_catalog(repo_root)
    slot_record = find_topping_slot(parent_module, topping_slot, catalog)
    parent_spec = _base_part_spec(parent_module)
    slot = asset_key_slug(topping_slot)
    key = asset_key_slug(topping_key)
    transform = _slot_transform(parent_module, slot, slot_record, parent_spec)
    panels = _topping_panels(parent_module, slot, key, slot_record, transform)
    return {
        "contract_version": SPEC_CONTRACT_VERSION,
        "asset_kind": "topping",
        "parent_module": parent_module,
        "module": f"{parent_module}__{slot}__{key}",
        "topping_slot": slot,
        "topping_key": key,
        "slot_transform": transform,
        "max_bbox_m": deepcopy(slot_record.get("max_bbox_m") or {}),
        "conflicts_with": list(slot_record.get("conflicts_with") or []),
        "material_zones_palette": dict(MATERIAL_PALETTE),
        "silhouette": {"panels": panels, "wrap_arc_deg": 0.0},
        "catalog_ref": {
            "path": CATALOG_REL.replace(os.sep, "/"),
            "contract_version": CATALOG_CONTRACT_VERSION,
            "module": parent_module,
            "topping_slot": slot,
            "topping_key": key,
        },
        "catalog_topping_slot": deepcopy(slot_record),
    }


def iter_variant_specs(repo_root: str | None = None, *, p0_only: bool = True) -> list[dict[str, Any]]:
    catalog = load_catalog(repo_root)
    modules = P0_MODULES if p0_only else CANONICAL_MODULES
    out: list[dict[str, Any]] = []
    for module in modules:
        for record in _variant_records(module, catalog):
            out.append(get_variant_spec(module, str(record.get("variant_key") or f"{module}:base"), repo_root))
    return out


def iter_topping_specs(
    repo_root: str | None = None,
    *,
    p0_only: bool = True,
    topping_key: str = "base",
) -> list[dict[str, Any]]:
    catalog = load_catalog(repo_root)
    modules = P0_MODULES if p0_only else CANONICAL_MODULES
    out: list[dict[str, Any]] = []
    for module in modules:
        wanted = set(P0_REQUIRED_TOPPING_SLOTS.get(module, ())) if p0_only else None
        for slot in _topping_slots(module, catalog):
            slot_name = str(slot.get("topping_slot") or "")
            if wanted is not None and slot_name not in wanted:
                continue
            out.append(get_topping_spec(module, slot_name, topping_key, repo_root))
    return out


def validate(repo_root: str | None = None, *, p0_only: bool = False) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        catalog = load_catalog(repo_root)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "errors": [f"catalog_load_failed: {exc}"], "warnings": []}

    if catalog.get("contract_version") != CATALOG_CONTRACT_VERSION:
        errors.append("catalog contract_version mismatch")
    catalog_modules = modules_from_catalog(catalog)
    catalog_parts = catalog.get("canonical_parts")
    if list(catalog_parts or []) != list(CANONICAL_MODULES):
        errors.append("catalog canonical_parts must preserve canonical 18 order")
    for module in CANONICAL_MODULES:
        if module not in catalog_modules:
            errors.append(f"catalog missing module: {module}")
    try:
        part_specs = _load_part_specs()
        missing_specs = [module for module in CANONICAL_MODULES if module not in part_specs]
        if missing_specs:
            errors.append(f"PART_SPECS missing canonical modules: {missing_specs}")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"PART_SPECS load failed: {exc}")

    modules_to_check = P0_MODULES if p0_only else CANONICAL_MODULES
    variant_count = 0
    topping_slot_count = 0
    for module in modules_to_check:
        variants = _variant_records(module, catalog)
        variant_count += len(variants)
        if not variants:
            errors.append(f"{module}: no variants declared")
        for record in variants:
            try:
                canonical_variant_key(module, str(record.get("variant_key") or ""))
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{module}: invalid variant key: {exc}")
        slots = _topping_slots(module, catalog)
        topping_slot_count += len(slots)
        slot_names = {str(slot.get("topping_slot") or "") for slot in slots}
        for required in P0_REQUIRED_TOPPING_SLOTS.get(module, ()):
            if required not in slot_names:
                errors.append(f"{module}: missing required P0 topping slot {required}")
        for slot in slots:
            try:
                asset_key_slug(str(slot.get("topping_slot") or ""))
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{module}: invalid topping slot: {exc}")
            if "slot_transform" not in slot:
                warnings.append(f"{module}.{slot.get('topping_slot')}: slot_transform inferred")

    return {
        "ok": not errors,
        "contract_version": SPEC_CONTRACT_VERSION,
        "catalog_path": catalog_path(repo_root),
        "canonical_module_count": len(CANONICAL_MODULES),
        "checked_module_count": len(modules_to_check),
        "variant_count": variant_count,
        "topping_slot_count": topping_slot_count,
        "errors": errors,
        "warnings": warnings,
    }


__all__ = [
    "CANONICAL_MODULES",
    "P0_MODULES",
    "P0_REQUIRED_TOPPING_SLOTS",
    "SPEC_CONTRACT_VERSION",
    "asset_key_slug",
    "canonical_variant_key",
    "catalog_path",
    "get_topping_spec",
    "get_variant_spec",
    "iter_topping_specs",
    "iter_variant_specs",
    "load_catalog",
    "validate",
]
