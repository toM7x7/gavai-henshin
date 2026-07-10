"""Validate modeler delivery manifests before Web/Quest runtime activation.

The manifest is intentionally a staging contract. It proves that delivered
assets match the existing armor-parts paths and keys, but it does not activate
or rewrite the runtime catalog.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_VERSION = "modeler-delivery-manifest.v1"
ARMOR_ROOT = "viewer/assets/armor-parts"
VALID_ASSET_KINDS = {"canonical", "variant", "topping", "base_suit_texture", "reference"}
CANONICAL_MODULES = (
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


def _load_intake_validator():
    path = REPO_ROOT / "tools" / "validate_armor_parts_intake.py"
    spec = importlib.util.spec_from_file_location("validate_armor_parts_intake", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load intake validator: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("validate_armor_parts_intake", module)
    spec.loader.exec_module(module)
    return module


def _repo_relative_path(value: Any, reasons: list[str], label: str) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        reasons.append(f"{label}: path must be a non-empty string")
        return None
    raw = Path(value)
    if raw.is_absolute():
        reasons.append(f"{label}: path must be repo-relative, not absolute: {value}")
        return None
    resolved = (REPO_ROOT / raw).resolve()
    try:
        resolved.relative_to(REPO_ROOT)
    except ValueError:
        reasons.append(f"{label}: path escapes repository: {value}")
        return None
    return resolved


def _posix(path: str | Path) -> str:
    return Path(path).as_posix()


def _read_json(path: Path, reasons: list[str], label: str) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - validator should report all parse failures.
        reasons.append(f"{label}: invalid JSON: {exc}")
        return None
    if not isinstance(data, dict):
        reasons.append(f"{label}: JSON root must be an object")
        return None
    return data


def _expected_variant_paths(module: str, asset_key: str) -> tuple[str, str, str]:
    stem = f"{module}__{asset_key}"
    base = f"{ARMOR_ROOT}/{module}/variants/{asset_key}"
    return (
        f"{base}/{stem}.glb",
        f"{base}/{stem}.modeler.json",
        f"{base}/source/{stem}.blend",
    )


def _expected_topping_paths(module: str, slot: str, choice_key: str) -> tuple[str, str, str]:
    stem = f"{module}__{slot}__{choice_key}"
    base = f"{ARMOR_ROOT}/{module}/toppings/{slot}/{choice_key}"
    return (
        f"{base}/{stem}.glb",
        f"{base}/{stem}.modeler.json",
        f"{base}/source/{stem}.blend",
    )


def _check_expected_path(
    asset: dict[str, Any],
    field: str,
    expected: str,
    reasons: list[str],
) -> Path | None:
    value = asset.get(field)
    path = _repo_relative_path(value, reasons, field)
    if path is not None and _posix(value) != expected:
        reasons.append(f"{field}: expected {expected}, got {_posix(value)}")
    return path


def _check_existing_file(path: Path | None, reasons: list[str], label: str) -> None:
    if path is None:
        return
    if not path.exists():
        reasons.append(f"{label}: file missing: {_posix(path.relative_to(REPO_ROOT))}")
    elif not path.is_file():
        reasons.append(f"{label}: must be a file: {_posix(path.relative_to(REPO_ROOT))}")


def _validate_sidecar(
    sidecar_path: Path | None,
    asset: dict[str, Any],
    reasons: list[str],
    warnings: list[str],
) -> None:
    if sidecar_path is None or not sidecar_path.exists():
        return
    sidecar = _read_json(sidecar_path, reasons, "sidecar_path")
    if sidecar is None:
        return

    module = asset.get("module") or asset.get("parent_module")
    if isinstance(module, str) and sidecar.get("module") not in (None, module):
        reasons.append(f"sidecar_path: module mismatch ({sidecar.get('module')} != {module})")

    kind = asset.get("asset_kind")
    if kind == "variant":
        expected_variant = asset.get("variant_key")
        if sidecar.get("variant_key") not in (None, expected_variant):
            reasons.append(
                f"sidecar_path: variant_key mismatch ({sidecar.get('variant_key')} != {expected_variant})"
            )
        if sidecar.get("contract_version") not in (None, "modeler-part-variant-sidecar.v1"):
            warnings.append(f"sidecar_path: unexpected variant sidecar contract {sidecar.get('contract_version')}")
    elif kind == "canonical":
        if sidecar.get("contract_version") not in (None, "modeler-part-sidecar.v1"):
            warnings.append(f"sidecar_path: unexpected canonical sidecar contract {sidecar.get('contract_version')}")


def _validate_glb(glb_path: Path | None, reasons: list[str], warnings: list[str]) -> None:
    if glb_path is None:
        return
    if not glb_path.exists():
        return
    intake = _load_intake_validator()
    result = intake.validate_glb_header(glb_path)
    reasons.extend(f"glb_path: {reason}" for reason in result.get("reasons", []))
    warnings.extend(f"glb_path: {warning}" for warning in result.get("warnings", []))


def _validate_review_images(asset: dict[str, Any], warnings: list[str], reasons: list[str]) -> None:
    images = asset.get("human_review_images")
    if images is None:
        warnings.append("human_review_images: recommended for modeler handoff review")
        return
    if not isinstance(images, list):
        reasons.append("human_review_images: must be a list of repo-relative image paths")
        return
    for index, image in enumerate(images):
        path = _repo_relative_path(image, reasons, f"human_review_images[{index}]")
        _check_existing_file(path, reasons, f"human_review_images[{index}]")


def _validate_concept_links(asset: dict[str, Any], warnings: list[str], reasons: list[str]) -> None:
    concepts = asset.get("source_concept_ids")
    if concepts is None:
        warnings.append("source_concept_ids: recommended so design intent remains traceable")
        return
    if not isinstance(concepts, list) or not all(isinstance(item, str) for item in concepts):
        reasons.append("source_concept_ids: must be a list of concept id strings")


def _validate_asset(index: int, asset: Any) -> dict[str, Any]:
    reasons: list[str] = []
    warnings: list[str] = []
    if not isinstance(asset, dict):
        return {
            "index": index,
            "status": "fail",
            "asset_kind": None,
            "module": None,
            "reasons": [f"assets[{index}]: must be an object"],
            "warnings": [],
        }

    kind = asset.get("asset_kind")
    if kind not in VALID_ASSET_KINDS:
        reasons.append(f"asset_kind: must be one of {sorted(VALID_ASSET_KINDS)}")

    if asset.get("activate_runtime") is True:
        reasons.append("activate_runtime: validation manifests must not activate runtime assets directly")

    glb_path: Path | None = None
    sidecar_path: Path | None = None
    source_blend_path: Path | None = None
    module = asset.get("module")

    if kind == "canonical":
        if module not in CANONICAL_MODULES:
            reasons.append(f"module: unknown canonical module {module!r}")
        elif isinstance(module, str):
            glb_path = _check_expected_path(asset, "glb_path", f"{ARMOR_ROOT}/{module}/{module}.glb", reasons)
            sidecar_path = _check_expected_path(
                asset, "sidecar_path", f"{ARMOR_ROOT}/{module}/{module}.modeler.json", reasons
            )
            source_blend_path = _check_expected_path(
                asset, "source_blend_path", f"{ARMOR_ROOT}/{module}/source/{module}.blend", reasons
            )
    elif kind == "variant":
        asset_key = asset.get("asset_key")
        variant_key = asset.get("variant_key")
        if module not in CANONICAL_MODULES:
            reasons.append(f"module: unknown canonical module {module!r}")
        if not isinstance(asset_key, str) or not asset_key or ":" in asset_key or "/" in asset_key or "\\" in asset_key:
            reasons.append("asset_key: must be a path-safe slug without ':' or slashes")
        if isinstance(module, str) and isinstance(asset_key, str):
            expected_variant = f"{module}:{asset_key}"
            if variant_key != expected_variant:
                reasons.append(f"variant_key: expected {expected_variant}, got {variant_key!r}")
            glb_expected, sidecar_expected, blend_expected = _expected_variant_paths(module, asset_key)
            glb_path = _check_expected_path(asset, "glb_path", glb_expected, reasons)
            sidecar_path = _check_expected_path(asset, "sidecar_path", sidecar_expected, reasons)
            source_blend_path = _check_expected_path(asset, "source_blend_path", blend_expected, reasons)
    elif kind == "topping":
        module = asset.get("module") or asset.get("parent_module")
        slot = asset.get("topping_slot")
        choice_key = asset.get("choice_key") or asset.get("topping_key")
        if module not in CANONICAL_MODULES:
            reasons.append(f"module: unknown canonical module {module!r}")
        for field_name, value in (("topping_slot", slot), ("choice_key", choice_key)):
            if not isinstance(value, str) or not value or ":" in value or "/" in value or "\\" in value:
                reasons.append(f"{field_name}: must be a path-safe slug")
        if isinstance(module, str) and isinstance(slot, str) and isinstance(choice_key, str):
            glb_expected, sidecar_expected, blend_expected = _expected_topping_paths(module, slot, choice_key)
            glb_path = _check_expected_path(asset, "glb_path", glb_expected, reasons)
            sidecar_path = _check_expected_path(asset, "sidecar_path", sidecar_expected, reasons)
            source_blend_path = _check_expected_path(asset, "source_blend_path", blend_expected, reasons)
    elif kind == "base_suit_texture":
        texture_path = _repo_relative_path(asset.get("texture_path"), reasons, "texture_path")
        _check_existing_file(texture_path, reasons, "texture_path")
        module = "base_suit_texture"
    elif kind == "reference":
        reference_path = _repo_relative_path(asset.get("reference_path"), reasons, "reference_path")
        _check_existing_file(reference_path, reasons, "reference_path")
        module = "reference"

    if kind in {"canonical", "variant", "topping"}:
        _check_existing_file(glb_path, reasons, "glb_path")
        _check_existing_file(sidecar_path, reasons, "sidecar_path")
        if source_blend_path is None:
            warnings.append("source_blend_path: recommended for reproducible Blender edits")
        else:
            _check_existing_file(source_blend_path, reasons, "source_blend_path")
        _validate_glb(glb_path, reasons, warnings)
        _validate_sidecar(sidecar_path, asset, reasons, warnings)

    _validate_review_images(asset, warnings, reasons)
    _validate_concept_links(asset, warnings, reasons)

    return {
        "index": index,
        "status": "fail" if reasons else "warn" if warnings else "pass",
        "asset_kind": kind,
        "module": module,
        "reasons": reasons,
        "warnings": warnings,
    }


def validate_delivery_manifest(manifest_path: str | Path) -> dict[str, Any]:
    path = Path(manifest_path)
    if not path.is_absolute():
        path = (REPO_ROOT / path).resolve()

    reasons: list[str] = []
    warnings: list[str] = []
    data = _read_json(path, reasons, "manifest")
    if data is None:
        return {
            "ok": False,
            "status": "fail",
            "manifest": str(path),
            "asset_count": 0,
            "reasons": reasons,
            "warnings": warnings,
            "assets": [],
        }

    if data.get("contract_version") != CONTRACT_VERSION:
        reasons.append(f"contract_version: expected {CONTRACT_VERSION}, got {data.get('contract_version')!r}")
    if not isinstance(data.get("delivery_id"), str) or not data.get("delivery_id"):
        reasons.append("delivery_id: required non-empty string")

    catalog_path = data.get("source_concept_catalog")
    if catalog_path is not None:
        resolved_catalog = _repo_relative_path(catalog_path, reasons, "source_concept_catalog")
        _check_existing_file(resolved_catalog, reasons, "source_concept_catalog")
    else:
        warnings.append("source_concept_catalog: recommended for tracing the tri-view source")

    assets = data.get("assets")
    if not isinstance(assets, list) or not assets:
        reasons.append("assets: required non-empty list")
        assets = []

    asset_results = [_validate_asset(index, asset) for index, asset in enumerate(assets)]
    for result in asset_results:
        reasons.extend(f"assets[{result['index']}]: {reason}" for reason in result["reasons"])
        warnings.extend(f"assets[{result['index']}]: {warning}" for warning in result["warnings"])

    status = "fail" if reasons else "warn" if warnings else "pass"
    return {
        "ok": status != "fail",
        "status": status,
        "manifest": str(path),
        "asset_count": len(asset_results),
        "reasons": reasons,
        "warnings": warnings,
        "assets": asset_results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, help="Repo-relative delivery manifest JSON path")
    args = parser.parse_args(argv)
    result = validate_delivery_manifest(args.manifest)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
