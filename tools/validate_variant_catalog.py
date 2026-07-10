"""Validate the Wave 2 armor variant catalog.

By default the validator fails structural errors and broken local references,
while reporting migration gaps as warnings. Strict flags promote selected
migration gaps to failures once that portion of the catalog is normalized.
"""

from __future__ import annotations

import argparse
import json
import sys
import struct
from pathlib import Path
from typing import Any, Iterable


DEFAULT_CATALOG_PATH = Path("viewer/assets/armor-parts/variant_catalog.json")
CATALOG_CONTRACT_VERSION = "armor-part-variant-catalog.v1"
EXPECTED_VARIANT_ASSET_COUNT = 54
EXPECTED_TOPPING_ASSET_COUNT = 32
VARIANT_SIDECAR_CONTRACT_VERSIONS = {
    "modeler-part-variant-sidecar.v1",
    "modeler-part-sidecar.v1",
}
TOPPING_SIDECAR_CONTRACT_VERSIONS = {
    "modeler-topping-sidecar.v1",
    "modeler-part-sidecar.v1",
}
GLB_MAGIC = b"glTF"
GLB_VERSION = 2
GLB_JSON_CHUNK_TYPE = 0x4E4F534A

EXPECTED_MODULES = (
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

P0_REQUIRED_TOPPING_SLOTS = {
    "helmet": ("crest", "visor_trim"),
    "chest": ("chest_core", "rib_trim"),
    "back": ("spine_ridge", "rear_core"),
    "waist": ("belt_buckle", "side_clip"),
    "left_shoulder": ("shoulder_fin", "edge_trim"),
    "right_shoulder": ("shoulder_fin", "edge_trim"),
    "left_shin": ("shin_spike", "ankle_cuff_trim"),
    "right_shin": ("shin_spike", "ankle_cuff_trim"),
}

SLOT_KINDS = {"micro", "detail", "topping"}
AXES = ("x", "y", "z")
CANONICAL_SURFACE_ZONES = {"base_surface", "accent", "emissive", "trim"}

MIRROR_OF_BY_MODULE = {
    "right_shoulder": "left_shoulder",
    "right_upperarm": "left_upperarm",
    "right_forearm": "left_forearm",
    "right_hand": "left_hand",
    "right_thigh": "left_thigh",
    "right_shin": "left_shin",
    "right_boot": "left_boot",
}


def validate_variant_catalog(
    catalog_path: str | Path = DEFAULT_CATALOG_PATH,
    *,
    expected_modules: Iterable[str] = EXPECTED_MODULES,
    strict_mirror_of: bool = False,
    strict_recommended_slots: bool = False,
) -> dict[str, Any]:
    """Read and validate a variant catalog file."""

    path = Path(catalog_path)
    if not path.exists():
        return {
            "ok": False,
            "status": "fail",
            "catalog_path": str(path),
            "module_count": 0,
            "reasons": [f"variant catalog missing: {path.as_posix()}"],
            "warnings": [],
            "modules": {},
        }

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "status": "fail",
            "catalog_path": str(path),
            "module_count": 0,
            "reasons": [f"variant catalog unreadable: {path.as_posix()}: {exc}"],
            "warnings": [],
            "modules": {},
        }

    return validate_catalog_payload(
        payload,
        catalog_path=path,
        expected_modules=tuple(expected_modules),
        strict_mirror_of=strict_mirror_of,
        strict_recommended_slots=strict_recommended_slots,
    )


def validate_delivered_asset_inventory(
    assets_root: str | Path = DEFAULT_CATALOG_PATH.parent,
    *,
    catalog_path: str | Path | None = DEFAULT_CATALOG_PATH,
    expected_variant_count: int = EXPECTED_VARIANT_ASSET_COUNT,
    expected_topping_count: int = EXPECTED_TOPPING_ASSET_COUNT,
    require_catalog_membership: bool = True,
) -> dict[str, Any]:
    """Validate delivered Wave 2 variant/topping assets and their companions."""

    root = Path(assets_root)
    reasons: list[str] = []
    warnings: list[str] = []
    variants: list[dict[str, Any]] = []
    toppings: list[dict[str, Any]] = []

    catalog_variant_keys: dict[str, set[str]] = {}
    catalog_slot_names: dict[str, set[str]] = {}
    if catalog_path is not None:
        catalog_result = _catalog_membership_sets(catalog_path)
        reasons.extend(catalog_result["reasons"])
        warnings.extend(catalog_result["warnings"])
        catalog_variant_keys = catalog_result["variant_keys"]
        catalog_slot_names = catalog_result["slot_names"]

    for glb_path in sorted(root.glob("*/variants/*/*.glb")):
        entry = _validate_variant_asset(
            glb_path,
            catalog_variant_keys=catalog_variant_keys,
            require_catalog_membership=require_catalog_membership,
        )
        variants.append(entry)
        reasons.extend(entry["reasons"])
        warnings.extend(entry["warnings"])

    for glb_path in sorted(root.glob("*/toppings/*/*/*.glb")):
        entry = _validate_topping_asset(
            glb_path,
            catalog_slot_names=catalog_slot_names,
            require_catalog_membership=require_catalog_membership,
        )
        toppings.append(entry)
        reasons.extend(entry["reasons"])
        warnings.extend(entry["warnings"])

    if len(variants) != expected_variant_count:
        reasons.append(f"delivered variant GLB count must be {expected_variant_count}, got {len(variants)}")
    if len(toppings) != expected_topping_count:
        reasons.append(f"delivered topping GLB count must be {expected_topping_count}, got {len(toppings)}")

    status = "fail" if reasons else "warn" if warnings else "pass"
    return {
        "ok": not reasons,
        "status": status,
        "assets_root": str(root),
        "catalog_path": str(catalog_path) if catalog_path is not None else None,
        "variant_count": len(variants),
        "expected_variant_count": expected_variant_count,
        "topping_count": len(toppings),
        "expected_topping_count": expected_topping_count,
        "reasons": reasons,
        "warnings": warnings,
        "variants": variants,
        "toppings": toppings,
    }


def validate_catalog_payload(
    payload: Any,
    *,
    catalog_path: str | Path | None = None,
    expected_modules: Iterable[str] = EXPECTED_MODULES,
    strict_mirror_of: bool = False,
    strict_recommended_slots: bool = False,
) -> dict[str, Any]:
    """Validate an already-decoded catalog payload."""

    expected = tuple(expected_modules)
    reasons: list[str] = []
    warnings: list[str] = []
    module_reports: dict[str, Any] = {}

    if not isinstance(payload, dict):
        return _result(
            catalog_path=catalog_path,
            modules={},
            reasons=["variant catalog root must be a JSON object"],
            warnings=[],
        )

    if payload.get("contract_version") != CATALOG_CONTRACT_VERSION:
        reasons.append(f"contract_version must be {CATALOG_CONTRACT_VERSION}")
    schema_version = payload.get("schema_version")
    if schema_version is not None and schema_version != CATALOG_CONTRACT_VERSION:
        reasons.append(f"schema_version must be {CATALOG_CONTRACT_VERSION}")

    raw_modules = payload.get("modules", payload.get("parts"))
    if not isinstance(raw_modules, dict):
        return _result(
            catalog_path=catalog_path,
            modules={},
            reasons=reasons + ["variant catalog must expose a modules object"],
            warnings=warnings,
        )

    _validate_canonical_parts(payload.get("canonical_parts"), expected, raw_modules, reasons, warnings)

    missing_modules = [module for module in expected if module not in raw_modules]
    extra_modules = [module for module in raw_modules if module not in expected]
    for module in missing_modules:
        reasons.append(f"{module}: required module missing from catalog")
    for module in extra_modules:
        warnings.append(f"{module}: extra module is not in the expected Wave 2 set")

    all_variant_keys = _collect_variant_keys(raw_modules)
    for module in expected:
        if module not in raw_modules:
            continue
        report = _validate_module(
            module,
            raw_modules[module],
            all_modules=raw_modules,
            all_variant_keys=all_variant_keys,
            strict_mirror_of=strict_mirror_of,
            strict_recommended_slots=strict_recommended_slots,
        )
        module_reports[module] = report
        reasons.extend(report["reasons"])
        warnings.extend(report["warnings"])

    return _result(catalog_path=catalog_path, modules=module_reports, reasons=reasons, warnings=warnings)


def _catalog_membership_sets(catalog_path: str | Path) -> dict[str, Any]:
    reasons: list[str] = []
    warnings: list[str] = []
    variant_keys: dict[str, set[str]] = {}
    slot_names: dict[str, set[str]] = {}
    path = Path(catalog_path)
    if not path.exists():
        return {
            "variant_keys": variant_keys,
            "slot_names": slot_names,
            "reasons": [f"variant catalog missing: {path.as_posix()}"],
            "warnings": warnings,
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        return {
            "variant_keys": variant_keys,
            "slot_names": slot_names,
            "reasons": [f"variant catalog unreadable: {path.as_posix()}: {exc}"],
            "warnings": warnings,
        }
    raw_modules = payload.get("modules", payload.get("parts")) if isinstance(payload, dict) else None
    if not isinstance(raw_modules, dict):
        return {
            "variant_keys": variant_keys,
            "slot_names": slot_names,
            "reasons": ["variant catalog must expose a modules object"],
            "warnings": warnings,
        }
    for module, module_payload in raw_modules.items():
        if not isinstance(module_payload, dict):
            continue
        variants = _variant_records(str(module), module_payload.get("variants"), errors=[])
        variant_keys[str(module)] = {
            str(variant["variant_key"]).strip()
            for variant in variants
            if _non_empty_string(variant.get("variant_key"))
        }
        slots = _topping_slot_records(str(module), module_payload.get("topping_slots"), errors=[])
        slot_names[str(module)] = {
            str(slot["topping_slot"]).strip()
            for slot in slots
            if _non_empty_string(slot.get("topping_slot"))
        }
    return {
        "variant_keys": variant_keys,
        "slot_names": slot_names,
        "reasons": reasons,
        "warnings": warnings,
    }


def _validate_variant_asset(
    glb_path: Path,
    *,
    catalog_variant_keys: dict[str, set[str]],
    require_catalog_membership: bool,
) -> dict[str, Any]:
    module = glb_path.parts[-4]
    variant_asset_key = glb_path.parts[-2]
    expected_stem = f"{module}__{variant_asset_key}"
    expected_variant_key = f"{module}:{variant_asset_key}"
    reasons: list[str] = []
    warnings: list[str] = []

    if glb_path.stem != expected_stem:
        reasons.append(f"{glb_path.as_posix()}: filename must be {expected_stem}.glb")
    _validate_required_asset_companions(glb_path, expected_stem, reasons)
    _validate_glb_header(glb_path, reasons)

    sidecar_path = glb_path.with_suffix(".modeler.json")
    payload = _load_json_object(sidecar_path, reasons)
    if payload is not None:
        _validate_sidecar_common(sidecar_path, payload, reasons)
        contract_version = payload.get("contract_version")
        if contract_version not in VARIANT_SIDECAR_CONTRACT_VERSIONS:
            reasons.append(
                f"{sidecar_path.as_posix()}: contract_version must be one of "
                f"{sorted(VARIANT_SIDECAR_CONTRACT_VERSIONS)}"
            )
        _validate_optional_module_field(sidecar_path, payload, "module", module, reasons)
        _validate_optional_module_field(sidecar_path, payload, "parent_module", module, reasons)
        variant_key = payload.get("variant_key") or _dict_get(payload.get("catalog_ref"), "variant_key")
        if variant_key != expected_variant_key:
            reasons.append(
                f"{sidecar_path.as_posix()}: variant_key must be {expected_variant_key}, got {variant_key!r}"
            )
        if "variant_asset_key" in payload and payload.get("variant_asset_key") != variant_asset_key:
            reasons.append(
                f"{sidecar_path.as_posix()}: variant_asset_key must be {variant_asset_key}"
            )
        catalog_ref = payload.get("catalog_ref")
        if isinstance(catalog_ref, dict):
            _validate_catalog_ref(sidecar_path, catalog_ref, module, expected_variant_key, None, None, reasons)
        catalog_variant = payload.get("catalog_variant")
        if isinstance(catalog_variant, dict) and catalog_variant.get("variant_key") != expected_variant_key:
            reasons.append(
                f"{sidecar_path.as_posix()}: catalog_variant.variant_key must be {expected_variant_key}"
            )

    if require_catalog_membership and expected_variant_key not in catalog_variant_keys.get(module, set()):
        reasons.append(f"{glb_path.as_posix()}: {expected_variant_key} is not declared in variant_catalog.json")

    return {
        "ok": not reasons,
        "path": glb_path.as_posix(),
        "module": module,
        "variant_asset_key": variant_asset_key,
        "variant_key": expected_variant_key,
        "sidecar_path": sidecar_path.as_posix(),
        "reasons": reasons,
        "warnings": warnings,
    }


def _validate_topping_asset(
    glb_path: Path,
    *,
    catalog_slot_names: dict[str, set[str]],
    require_catalog_membership: bool,
) -> dict[str, Any]:
    module = glb_path.parts[-5]
    topping_slot = glb_path.parts[-3]
    topping_key = glb_path.parts[-2]
    expected_stem = f"{module}__{topping_slot}__{topping_key}"
    expected_topping_ref = f"{module}:{topping_slot}:{topping_key}"
    reasons: list[str] = []
    warnings: list[str] = []

    if glb_path.stem != expected_stem:
        reasons.append(f"{glb_path.as_posix()}: filename must be {expected_stem}.glb")
    _validate_required_asset_companions(glb_path, expected_stem, reasons)
    _validate_glb_header(glb_path, reasons)

    sidecar_path = glb_path.with_suffix(".modeler.json")
    payload = _load_json_object(sidecar_path, reasons)
    if payload is not None:
        _validate_sidecar_common(sidecar_path, payload, reasons)
        contract_version = payload.get("contract_version")
        if contract_version not in TOPPING_SIDECAR_CONTRACT_VERSIONS:
            reasons.append(
                f"{sidecar_path.as_posix()}: contract_version must be one of "
                f"{sorted(TOPPING_SIDECAR_CONTRACT_VERSIONS)}"
            )
        _validate_optional_module_field(sidecar_path, payload, "module", module, reasons)
        if payload.get("parent_module") != module:
            reasons.append(f"{sidecar_path.as_posix()}: parent_module must be {module}")
        if payload.get("topping_slot") != topping_slot:
            reasons.append(f"{sidecar_path.as_posix()}: topping_slot must be {topping_slot}")
        if payload.get("topping_key") != topping_key:
            reasons.append(f"{sidecar_path.as_posix()}: topping_key must be {topping_key}")
        if "variant_key" in payload and payload.get("variant_key") != expected_topping_ref:
            reasons.append(f"{sidecar_path.as_posix()}: variant_key must be {expected_topping_ref}")
        catalog_ref = payload.get("catalog_ref")
        if isinstance(catalog_ref, dict):
            _validate_catalog_ref(sidecar_path, catalog_ref, module, None, topping_slot, topping_key, reasons)
        catalog_slot = payload.get("catalog_topping_slot")
        if isinstance(catalog_slot, dict) and catalog_slot.get("topping_slot") != topping_slot:
            reasons.append(
                f"{sidecar_path.as_posix()}: catalog_topping_slot.topping_slot must be {topping_slot}"
            )
        if not _has_anchor_contract(payload):
            reasons.append(f"{sidecar_path.as_posix()}: slot_transform or anchor_hint must declare placement")
        max_bbox = payload.get("max_bbox_m")
        if not isinstance(max_bbox, dict):
            reasons.append(f"{sidecar_path.as_posix()}: max_bbox_m must be an object")
        else:
            dims = [max_bbox.get(axis) for axis in AXES]
            if not _number_list(dims, expected_len=3) or not all(float(dim) > 0 for dim in dims):
                reasons.append(f"{sidecar_path.as_posix()}: max_bbox_m must provide positive x/y/z")
        conflicts = payload.get("conflicts_with")
        if conflicts is not None and not _string_list(conflicts):
            reasons.append(f"{sidecar_path.as_posix()}: conflicts_with must be a string list")

    if require_catalog_membership and topping_slot not in catalog_slot_names.get(module, set()):
        reasons.append(f"{glb_path.as_posix()}: {module}:{topping_slot} is not declared in variant_catalog.json")

    return {
        "ok": not reasons,
        "path": glb_path.as_posix(),
        "module": module,
        "topping_slot": topping_slot,
        "topping_key": topping_key,
        "topping_ref": expected_topping_ref,
        "sidecar_path": sidecar_path.as_posix(),
        "reasons": reasons,
        "warnings": warnings,
    }


def _validate_required_asset_companions(glb_path: Path, expected_stem: str, reasons: list[str]) -> None:
    required = (
        glb_path.with_suffix(".modeler.json"),
        glb_path.parent / "source" / f"{expected_stem}.blend",
        glb_path.parent / "preview" / f"{expected_stem}.mesh.json",
    )
    for path in required:
        if not path.is_file():
            reasons.append(f"{path.as_posix()}: required companion file missing")


def _validate_glb_header(path: Path, reasons: list[str]) -> None:
    try:
        data = path.read_bytes()
        if len(data) < 20:
            reasons.append(f"{path.as_posix()}: GLB too small for header")
            return
        magic, version, declared_length = struct.unpack_from("<4sII", data, 0)
        if magic != GLB_MAGIC:
            reasons.append(f"{path.as_posix()}: GLB magic must be glTF")
        if version != GLB_VERSION:
            reasons.append(f"{path.as_posix()}: GLB version must be 2")
        if declared_length != len(data):
            reasons.append(f"{path.as_posix()}: GLB declared length does not match file size")
        chunk_length, chunk_type = struct.unpack_from("<II", data, 12)
        if chunk_type != GLB_JSON_CHUNK_TYPE or chunk_length <= 0 or 20 + chunk_length > len(data):
            reasons.append(f"{path.as_posix()}: GLB first chunk must be a valid JSON chunk")
    except Exception as exc:  # noqa: BLE001
        reasons.append(f"{path.as_posix()}: GLB unreadable: {exc}")


def _load_json_object(path: Path, reasons: list[str]) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        reasons.append(f"{path.as_posix()}: JSON unreadable: {exc}")
        return None
    if not isinstance(payload, dict):
        reasons.append(f"{path.as_posix()}: JSON root must be an object")
        return None
    return payload


def _validate_sidecar_common(path: Path, payload: dict[str, Any], reasons: list[str]) -> None:
    bbox = payload.get("bbox_m")
    if not isinstance(bbox, dict):
        reasons.append(f"{path.as_posix()}: bbox_m must be an object")
    else:
        dims = [bbox.get(axis) for axis in AXES]
        if not _number_list(dims, expected_len=3) or not all(float(dim) > 0 for dim in dims):
            reasons.append(f"{path.as_posix()}: bbox_m must provide positive x/y/z")
    triangle_count = payload.get("triangle_count", payload.get("triangles"))
    if not isinstance(triangle_count, int) or isinstance(triangle_count, bool) or triangle_count <= 0:
        reasons.append(f"{path.as_posix()}: triangle_count must be a positive integer")
    material_zones = payload.get("material_zones")
    if not _string_list(material_zones):
        reasons.append(f"{path.as_posix()}: material_zones must be a non-empty string list")
    if not _non_empty_string(payload.get("coordinate_frame")):
        reasons.append(f"{path.as_posix()}: coordinate_frame missing")


def _validate_optional_module_field(
    path: Path,
    payload: dict[str, Any],
    field: str,
    expected_module: str,
    reasons: list[str],
) -> None:
    if field in payload and payload.get(field) != expected_module:
        reasons.append(f"{path.as_posix()}: {field} must be {expected_module}")


def _validate_catalog_ref(
    path: Path,
    catalog_ref: dict[str, Any],
    module: str,
    variant_key: str | None,
    topping_slot: str | None,
    topping_key: str | None,
    reasons: list[str],
) -> None:
    if catalog_ref.get("contract_version") != CATALOG_CONTRACT_VERSION:
        reasons.append(f"{path.as_posix()}: catalog_ref.contract_version must be {CATALOG_CONTRACT_VERSION}")
    if catalog_ref.get("module") != module:
        reasons.append(f"{path.as_posix()}: catalog_ref.module must be {module}")
    if variant_key is not None and catalog_ref.get("variant_key") != variant_key:
        reasons.append(f"{path.as_posix()}: catalog_ref.variant_key must be {variant_key}")
    if topping_slot is not None and catalog_ref.get("topping_slot") != topping_slot:
        reasons.append(f"{path.as_posix()}: catalog_ref.topping_slot must be {topping_slot}")
    if topping_key is not None and catalog_ref.get("topping_key") != topping_key:
        reasons.append(f"{path.as_posix()}: catalog_ref.topping_key must be {topping_key}")


def _dict_get(value: Any, key: str) -> Any:
    return value.get(key) if isinstance(value, dict) else None


def _validate_canonical_parts(
    value: Any,
    expected: tuple[str, ...],
    modules: dict[str, Any],
    reasons: list[str],
    warnings: list[str],
) -> None:
    if value is None:
        warnings.append("canonical_parts missing; modules object is used as source of truth")
        return
    if not _string_list(value):
        reasons.append("canonical_parts must be a string list when present")
        return
    missing = [module for module in expected if module not in value]
    if missing:
        reasons.append(f"canonical_parts missing expected module(s): {missing}")
    undeclared_modules = [module for module in modules if module not in value]
    if undeclared_modules:
        warnings.append(f"modules not listed in canonical_parts: {undeclared_modules}")


def _collect_variant_keys(modules: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for module, module_payload in modules.items():
        if not isinstance(module_payload, dict):
            continue
        variants = _variant_records(module, module_payload.get("variants"), errors=[])
        for variant in variants:
            variant_key = variant.get("variant_key")
            if isinstance(variant_key, str):
                keys.add(variant_key)
    return keys


def _validate_module(
    module: str,
    module_payload: Any,
    *,
    all_modules: dict[str, Any],
    all_variant_keys: set[str],
    strict_mirror_of: bool,
    strict_recommended_slots: bool,
) -> dict[str, Any]:
    reasons: list[str] = []
    warnings: list[str] = []
    slot_names: set[str] = set()
    material_zones: set[str] = set()

    if not isinstance(module_payload, dict):
        return _module_result(module, [], [], [], [f"{module}: module entry must be an object"], [])

    part_family = module_payload.get("part_family")
    if not _non_empty_string(part_family):
        reasons.append(f"{module}: part_family missing")

    motif_link = _validate_motif_link(module, module_payload.get("base_motif_link"), reasons, "module")
    if motif_link:
        material_zones.add(motif_link["surface_zone"])

    _validate_module_mirror_of(
        module,
        module_payload.get("mirror_of"),
        all_modules=all_modules,
        reasons=reasons,
        warnings=warnings,
        strict=strict_mirror_of,
    )

    variants = _variant_records(module, module_payload.get("variants"), errors=reasons)
    minimum_variant_count = 2 if module in P0_REQUIRED_TOPPING_SLOTS else 1
    if len(variants) < minimum_variant_count:
        reasons.append(f"{module}: expected at least {minimum_variant_count} variant(s)")

    seen_variant_keys: set[str] = set()
    for variant in variants:
        _validate_variant(
            module,
            variant,
            seen_variant_keys=seen_variant_keys,
            module_motif_link=motif_link,
            all_variant_keys=all_variant_keys,
            reasons=reasons,
            warnings=warnings,
        )
        variant_motif = variant.get("base_motif_link")
        if isinstance(variant_motif, dict) and _non_empty_string(variant_motif.get("surface_zone")):
            material_zones.add(str(variant_motif["surface_zone"]).strip())

    slots = _topping_slot_records(module, module_payload.get("topping_slots"), errors=reasons)
    seen_slot_names: set[str] = set()
    for slot in slots:
        slot_name = _validate_topping_slot(module, slot, seen_slot_names=seen_slot_names, reasons=reasons)
        if slot_name:
            slot_names.add(slot_name)
        material_zone = slot.get("material_zone") if isinstance(slot, dict) else None
        if _non_empty_string(material_zone):
            material_zones.add(str(material_zone).strip())

    _validate_required_slots(module, slot_names, reasons)
    _validate_slot_conflicts(module, slots, slot_names, reasons)
    _validate_recommended_slots(
        module,
        variants,
        slot_names,
        reasons=reasons,
        warnings=warnings,
        strict=strict_recommended_slots,
    )

    if not material_zones:
        reasons.append(f"{module}: no material zones declared through base_motif_link or topping_slots")
    elif not any(_has_canonical_material_token(zone) for zone in material_zones):
        warnings.append(
            f"{module}: material zones {sorted(material_zones)} do not include canonical base/accent/emissive/trim tokens"
        )

    return _module_result(
        module,
        variants,
        slots,
        sorted(material_zones),
        reasons,
        warnings,
        slot_names=sorted(slot_names),
    )


def _validate_module_mirror_of(
    module: str,
    value: Any,
    *,
    all_modules: dict[str, Any],
    reasons: list[str],
    warnings: list[str],
    strict: bool,
) -> None:
    expected_partner = MIRROR_OF_BY_MODULE.get(module)
    if value is None:
        if expected_partner:
            message = f"{module}: mirror_of should point at {expected_partner}"
            if strict:
                reasons.append(message)
            else:
                warnings.append(message)
        return
    if not _non_empty_string(value):
        reasons.append(f"{module}: mirror_of must be a module id string when present")
        return
    partner = str(value).strip()
    if partner not in all_modules:
        reasons.append(f"{module}: mirror_of references unknown module {partner!r}")
    if expected_partner and partner != expected_partner:
        reasons.append(f"{module}: mirror_of must be {expected_partner}")


def _validate_variant(
    module: str,
    variant: dict[str, Any],
    *,
    seen_variant_keys: set[str],
    module_motif_link: dict[str, str] | None,
    all_variant_keys: set[str],
    reasons: list[str],
    warnings: list[str],
) -> None:
    variant_key = variant.get("variant_key")
    label = f"{module}: variant"
    if not _non_empty_string(variant_key):
        reasons.append(f"{label} missing variant_key")
        variant_label = label
    else:
        variant_key = str(variant_key).strip()
        variant_label = variant_key
        if not variant_key.startswith(f"{module}:"):
            reasons.append(f"{variant_label}: variant_key must start with {module}:")
        if variant_key in seen_variant_keys:
            reasons.append(f"{variant_label}: duplicate variant_key")
        seen_variant_keys.add(variant_key)

    display_name = variant.get("display_name", variant.get("label"))
    if not _non_empty_string(display_name):
        reasons.append(f"{variant_label}: display_name missing")

    if "base_motif_link" in variant:
        _validate_motif_link(variant_label, variant.get("base_motif_link"), reasons, "variant")
    elif module_motif_link is None:
        reasons.append(f"{variant_label}: base_motif_link missing and module has no fallback")

    detail_features = variant.get("detail_features")
    if not isinstance(detail_features, list):
        reasons.append(f"{variant_label}: detail_features must be a list")
    elif len([item for item in detail_features if _non_empty_string(item)]) < 2:
        reasons.append(f"{variant_label}: detail_features must include at least 2 non-empty strings")

    recommended = variant.get("recommended_topping_slots")
    if recommended is not None and not _string_list(recommended):
        reasons.append(f"{variant_label}: recommended_topping_slots must be a string list")

    conflicts = variant.get("conflicts_with")
    if conflicts is not None and not _string_list(conflicts):
        reasons.append(f"{variant_label}: conflicts_with must be a string list")

    mirror_of = variant.get("mirror_of")
    if mirror_of is not None:
        if not _non_empty_string(mirror_of):
            reasons.append(f"{variant_label}: mirror_of must be a variant_key string when present")
        elif str(mirror_of).strip() not in all_variant_keys:
            reasons.append(f"{variant_label}: mirror_of references unknown variant {str(mirror_of).strip()!r}")
        elif str(mirror_of).split(":", 1)[0] == module:
            warnings.append(f"{variant_label}: mirror_of points inside the same module")


def _validate_motif_link(
    label: str,
    value: Any,
    reasons: list[str],
    owner: str,
) -> dict[str, str] | None:
    if not isinstance(value, dict):
        reasons.append(f"{label}: {owner} base_motif_link must be an object")
        return None
    name = value.get("name")
    surface_zone = value.get("surface_zone")
    if not _non_empty_string(name):
        reasons.append(f"{label}: {owner} base_motif_link.name missing")
    if not _non_empty_string(surface_zone):
        reasons.append(f"{label}: {owner} base_motif_link.surface_zone missing")
    if _non_empty_string(name) and _non_empty_string(surface_zone):
        return {"name": str(name).strip(), "surface_zone": str(surface_zone).strip()}
    return None


def _validate_topping_slot(
    module: str,
    slot: dict[str, Any],
    *,
    seen_slot_names: set[str],
    reasons: list[str],
) -> str | None:
    slot_name = slot.get("topping_slot")
    label = f"{module}: topping_slot"
    if not _non_empty_string(slot_name):
        reasons.append(f"{label} missing topping_slot")
        return None
    slot_name = str(slot_name).strip()
    label = f"{module}: topping_slot {slot_name}"
    if slot_name in seen_slot_names:
        reasons.append(f"{label}: duplicate topping_slot")
    seen_slot_names.add(slot_name)

    slot_kind = slot.get("slot_kind")
    if slot_kind not in SLOT_KINDS:
        reasons.append(f"{label}: slot_kind must be one of {sorted(SLOT_KINDS)}")

    parent_module = slot.get("parent_module")
    if parent_module != module:
        reasons.append(f"{label}: parent_module must be {module}")

    allowed_count = slot.get("allowed_count")
    if not isinstance(allowed_count, dict):
        reasons.append(f"{label}: allowed_count must be an object")
    else:
        minimum = allowed_count.get("min")
        maximum = allowed_count.get("max")
        if not _non_bool_int(minimum) or not _non_bool_int(maximum):
            reasons.append(f"{label}: allowed_count.min/max must be integers")
        elif minimum < 0 or maximum < minimum:
            reasons.append(f"{label}: allowed_count must satisfy 0 <= min <= max")

    if not _has_anchor_contract(slot):
        reasons.append(f"{label}: anchor_hint or slot_transform must declare placement")

    max_bbox = slot.get("max_bbox_m")
    if not isinstance(max_bbox, dict):
        reasons.append(f"{label}: max_bbox_m must be an object")
    else:
        dims = [max_bbox.get(axis) for axis in AXES]
        if not _number_list(dims, expected_len=3) or not all(float(dim) > 0 for dim in dims):
            reasons.append(f"{label}: max_bbox_m must provide positive x/y/z")

    if not _non_empty_string(slot.get("material_zone")):
        reasons.append(f"{label}: material_zone missing")

    examples = slot.get("variant_examples")
    if examples is not None and not _string_list(examples):
        reasons.append(f"{label}: variant_examples must be a string list")

    conflicts = slot.get("conflicts_with")
    if conflicts is None:
        reasons.append(f"{label}: conflicts_with must be declared, use [] when none")
    elif not _string_list(conflicts):
        reasons.append(f"{label}: conflicts_with must be a string list")

    return slot_name


def _validate_required_slots(module: str, slot_names: set[str], reasons: list[str]) -> None:
    required = P0_REQUIRED_TOPPING_SLOTS.get(module, ())
    missing = [slot for slot in required if slot not in slot_names]
    if missing:
        reasons.append(f"{module}: missing required topping slots {missing}")


def _validate_slot_conflicts(
    module: str,
    slots: list[dict[str, Any]],
    slot_names: set[str],
    reasons: list[str],
) -> None:
    for slot in slots:
        slot_name = slot.get("topping_slot")
        if not _non_empty_string(slot_name):
            continue
        for conflict in slot.get("conflicts_with") or []:
            if not isinstance(conflict, str):
                continue
            if conflict == slot_name:
                reasons.append(f"{module}: topping_slot {slot_name} conflicts_with itself")
            elif conflict not in slot_names:
                reasons.append(
                    f"{module}: topping_slot {slot_name} conflicts_with unknown slot {conflict!r}"
                )


def _validate_recommended_slots(
    module: str,
    variants: list[dict[str, Any]],
    slot_names: set[str],
    *,
    reasons: list[str],
    warnings: list[str],
    strict: bool,
) -> None:
    for variant in variants:
        variant_key = variant.get("variant_key", f"{module}:<unknown>")
        recommended = variant.get("recommended_topping_slots")
        if not _string_list(recommended):
            continue
        missing = [slot for slot in recommended if slot not in slot_names]
        if missing:
            message = f"{variant_key}: recommended_topping_slots missing catalog slot(s): {missing}"
            if strict:
                reasons.append(message)
            else:
                warnings.append(message)


def _variant_records(module: str, raw_variants: Any, *, errors: list[str]) -> list[dict[str, Any]]:
    if not isinstance(raw_variants, (list, dict)):
        errors.append(f"{module}: variants must be a list or object")
        return []
    if isinstance(raw_variants, dict):
        records = []
        for key, value in raw_variants.items():
            if not isinstance(value, dict):
                errors.append(f"{module}: variant {key} must be an object")
                continue
            records.append({"variant_key": value.get("variant_key", key), **value})
        return records
    records = []
    for index, value in enumerate(raw_variants):
        if not isinstance(value, dict):
            errors.append(f"{module}: variants[{index}] must be an object")
            continue
        records.append(value)
    return records


def _topping_slot_records(module: str, raw_slots: Any, *, errors: list[str]) -> list[dict[str, Any]]:
    if raw_slots is None:
        if module in P0_REQUIRED_TOPPING_SLOTS:
            errors.append(f"{module}: topping_slots missing")
        return []
    if not isinstance(raw_slots, list):
        errors.append(f"{module}: topping_slots must be a list")
        return []
    records = []
    for index, value in enumerate(raw_slots):
        if not isinstance(value, dict):
            errors.append(f"{module}: topping_slots[{index}] must be an object")
            continue
        records.append(value)
    return records


def _has_anchor_contract(slot: dict[str, Any]) -> bool:
    transform = slot.get("slot_transform")
    if isinstance(transform, dict):
        anchor = transform.get("anchor")
        rotation = transform.get("rotation_deg")
        if _number_list(anchor, expected_len=3) and _number_list(rotation, expected_len=3):
            return True

    anchor_hint = slot.get("anchor_hint")
    if isinstance(anchor_hint, dict):
        required = ("body_anchor", "parent_surface", "placement")
        return all(_non_empty_string(anchor_hint.get(key)) for key in required)
    return False


def _module_result(
    module: str,
    variants: list[dict[str, Any]],
    slots: list[dict[str, Any]],
    material_zones: list[str],
    reasons: list[str],
    warnings: list[str],
    *,
    slot_names: list[str] | None = None,
) -> dict[str, Any]:
    status = "fail" if reasons else "warn" if warnings else "pass"
    return {
        "ok": not reasons,
        "status": status,
        "module": module,
        "variant_count": len(variants),
        "topping_slot_count": len(slots),
        "topping_slots": slot_names or [],
        "material_zones": material_zones,
        "reasons": reasons,
        "warnings": warnings,
    }


def _result(
    *,
    catalog_path: str | Path | None,
    modules: dict[str, Any],
    reasons: list[str],
    warnings: list[str],
) -> dict[str, Any]:
    status = "fail" if reasons else "warn" if warnings else "pass"
    return {
        "ok": not reasons,
        "status": status,
        "catalog_path": str(catalog_path) if catalog_path is not None else None,
        "module_count": len(modules),
        "reasons": reasons,
        "warnings": warnings,
        "modules": modules,
    }


def _has_canonical_material_token(zone: str) -> bool:
    normalized = zone.strip().lower()
    return normalized in CANONICAL_SURFACE_ZONES or any(
        token in normalized for token in CANONICAL_SURFACE_ZONES
    )


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(_non_empty_string(item) for item in value)


def _non_bool_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _number_list(value: Any, *, expected_len: int) -> bool:
    return (
        isinstance(value, list)
        and len(value) == expected_len
        and all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in value)
    )


def _print_text_report(result: dict[str, Any]) -> None:
    print(f"[{result['status'].upper()}] {result.get('catalog_path') or '<payload>'}")
    print(f"validated {result['module_count']} module(s)")
    for reason in result["reasons"]:
        print(f"  fail  {reason}")
    for warning in result["warnings"]:
        print(f"  warn  {warning}")
    for module, report in result["modules"].items():
        print(
            f"  {report['status']:>4}  {module}: "
            f"{report['variant_count']} variant(s), {report['topping_slot_count']} slot(s)"
        )


def _merge_asset_inventory_result(result: dict[str, Any], asset_result: dict[str, Any]) -> dict[str, Any]:
    merged = dict(result)
    merged["delivered_assets"] = asset_result
    merged["reasons"] = result["reasons"] + [
        f"delivered_assets: {reason}" for reason in asset_result["reasons"]
    ]
    merged["warnings"] = result["warnings"] + [
        f"delivered_assets: {warning}" for warning in asset_result["warnings"]
    ]
    merged["ok"] = result["ok"] and asset_result["ok"]
    merged["status"] = "fail" if merged["reasons"] else "warn" if merged["warnings"] else "pass"
    return merged


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--catalog",
        type=Path,
        default=DEFAULT_CATALOG_PATH,
        help="Path to variant_catalog.json",
    )
    parser.add_argument("--report-json", action="store_true", help="Emit a structured JSON report")
    parser.add_argument(
        "--strict-mirror-of",
        action="store_true",
        help="Fail right-side modules that have not declared mirror_of yet",
    )
    parser.add_argument(
        "--strict-recommended-slots",
        action="store_true",
        help="Fail variants whose recommended_topping_slots are not declared as slots",
    )
    parser.add_argument(
        "--include-delivered-assets",
        action="store_true",
        help="Also validate delivered Wave 2 variant/topping GLBs and companion files",
    )
    args = parser.parse_args(argv)

    result = validate_variant_catalog(
        args.catalog,
        strict_mirror_of=args.strict_mirror_of,
        strict_recommended_slots=args.strict_recommended_slots,
    )
    if args.include_delivered_assets:
        asset_result = validate_delivered_asset_inventory(
            args.catalog.parent,
            catalog_path=args.catalog,
        )
        result = _merge_asset_inventory_result(result, asset_result)
    if args.report_json:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        _print_text_report(result)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
