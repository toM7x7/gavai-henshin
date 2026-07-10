"""Validate P1 modeler variant order manifests.

The order manifest is a pre-delivery contract. In normal mode it verifies
that the requested variants are well formed and reports catalog/file gaps as
open work. With --require-delivered, the same manifest becomes an acceptance
gate for delivered GLB/source/sidecar/preview companions.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = Path(
    "docs/modeler-deliveries/p1-limb-three-line-variants-2026-05-03.order-manifest.json"
)
DEFAULT_CATALOG = Path("viewer/assets/armor-parts/variant_catalog.json")
CONTRACT_VERSION = "modeler-variant-order-manifest.v1"
ASSET_KIND = "variant_order"
ARMOR_ROOT = "viewer/assets/armor-parts"
P1_TARGET_MODULES = (
    "left_upperarm",
    "right_upperarm",
    "left_forearm",
    "right_forearm",
    "left_hand",
    "right_hand",
    "left_thigh",
    "right_thigh",
)
CANONICAL_MODULES = {
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
}
REQUIRED_SIDECAR_FIELDS = (
    "source_concept_ids",
    "line_id",
    "design_intent",
    "fidelity_notes",
)
P1_ACCEPTANCE_PHASE = "P1"
P1_ACCEPTANCE_PASS = "pass_p1"
P1_ACCEPTANCE_BLOCK = "warn_now_block_p1"
RUNTIME_ACTIVATION_BLOCKED = "runtime_activation_blocked_by_order_manifest"
MISSING_MATRIX_CONTRACT = "p1-limb-missing-matrix.v1"
STAGE_ORDER = ("order", "delivery", "catalog_registration", "runtime_activation")
PATH_FIELDS = (
    "expected_glb_path",
    "expected_sidecar_path",
    "expected_source_blend_path",
    "expected_preview_mesh_path",
)


def validate_order_manifest(
    manifest_path: str | Path = DEFAULT_MANIFEST,
    *,
    catalog_path: str | Path = DEFAULT_CATALOG,
    require_delivered: bool = False,
) -> dict[str, Any]:
    """Read and validate an order manifest."""

    path = _repo_path(manifest_path)
    reasons: list[str] = []
    warnings: list[str] = []
    payload = _read_json_object(path, reasons, "manifest")
    if payload is None:
        return _result(
            manifest=path,
            catalog_path=catalog_path,
            require_delivered=require_delivered,
            asset_reports=[],
            module_reports={},
            line_system_reports={},
            missing_matrix=_missing_matrix([], lines={}, target_modules=[]),
            catalog_gaps=[],
            delivery_gaps=[],
            reasons=reasons,
            warnings=warnings,
        )

    if payload.get("contract_version") != CONTRACT_VERSION:
        reasons.append(f"contract_version: expected {CONTRACT_VERSION}, got {payload.get('contract_version')!r}")
    if not _non_empty_string(payload.get("order_id")):
        reasons.append("order_id: required non-empty string")
    if not _non_empty_string(payload.get("assets_root")):
        reasons.append("assets_root: required non-empty string")
    elif _posix(payload["assets_root"]) != ARMOR_ROOT:
        reasons.append(f"assets_root: expected {ARMOR_ROOT}, got {_posix(payload['assets_root'])}")
    if payload.get("source_concept_catalog") is not None:
        concept_path = _repo_relative_path(payload.get("source_concept_catalog"), reasons, "source_concept_catalog")
        _check_existing_file(concept_path, reasons, "source_concept_catalog")

    target_modules = payload.get("target_modules")
    if not isinstance(target_modules, list) or not target_modules:
        reasons.append("target_modules: required non-empty list")
        target_modules = []
    elif not all(_non_empty_string(module) for module in target_modules):
        reasons.append("target_modules: must contain module id strings")
    else:
        duplicates = sorted({module for module in target_modules if target_modules.count(module) > 1})
        if duplicates:
            reasons.append(f"target_modules: duplicate module(s) {duplicates}")
        unknown = [module for module in target_modules if module not in CANONICAL_MODULES]
        if unknown:
            reasons.append(f"target_modules: unknown module(s) {unknown}")
        unexpected = [module for module in target_modules if module not in P1_TARGET_MODULES]
        if unexpected:
            reasons.append(f"target_modules: not in P1 limb scope {unexpected}")

    lines = _line_map(payload.get("required_lines"), reasons)
    policy = payload.get("acceptance_policy")
    if not isinstance(policy, dict):
        reasons.append("acceptance_policy: required object")
        policy = {}
    required_per_module = policy.get("required_variants_per_module")
    if not isinstance(required_per_module, int) or isinstance(required_per_module, bool) or required_per_module < 1:
        reasons.append("acceptance_policy.required_variants_per_module: must be a positive integer")
        required_per_module = len(lines)
    if policy.get("runtime_activation_allowed") is not False:
        reasons.append("acceptance_policy.runtime_activation_allowed: must be false for order manifests")

    catalog_keys, catalog_warnings = _catalog_variant_keys(catalog_path)
    warnings.extend(catalog_warnings)

    raw_variants = payload.get("variants")
    if not isinstance(raw_variants, list) or not raw_variants:
        reasons.append("variants: required non-empty list")
        raw_variants = []

    reports: list[dict[str, Any]] = []
    seen_variant_keys: set[str] = set()
    for index, variant in enumerate(raw_variants):
        report = _validate_variant_order(
            index,
            variant,
            target_modules=target_modules,
            lines=lines,
            catalog_keys=catalog_keys,
            require_delivered=require_delivered,
        )
        reports.append(report)
        reasons.extend(f"variants[{index}]: {reason}" for reason in report["reasons"])
        warnings.extend(f"variants[{index}]: {warning}" for warning in report["warnings"])
        variant_key = report.get("variant_key")
        if isinstance(variant_key, str):
            if variant_key in seen_variant_keys:
                reasons.append(f"variants[{index}]: duplicate variant_key {variant_key}")
            seen_variant_keys.add(variant_key)

    _validate_expected_matrix(
        reports,
        target_modules=target_modules,
        lines=lines,
        required_per_module=required_per_module,
        reasons=reasons,
    )

    catalog_gaps = [report for report in reports if report.get("catalog_status") == "missing"]
    delivery_gaps = [report for report in reports if report.get("delivery_status") == "missing"]
    if catalog_gaps and not require_delivered:
        warnings.append(f"catalog: {len(catalog_gaps)} ordered variant(s) not yet declared")
    if delivery_gaps and not require_delivered:
        warnings.append(f"delivery: {len(delivery_gaps)} ordered variant(s) not yet delivered")

    module_reports = _module_reports(reports, target_modules=target_modules, lines=lines)
    line_system_reports = _line_system_reports(reports, lines=lines)
    missing_matrix = _missing_matrix(reports, lines=lines, target_modules=target_modules)
    return _result(
        manifest=path,
        catalog_path=catalog_path,
        require_delivered=require_delivered,
        asset_reports=reports,
        module_reports=module_reports,
        line_system_reports=line_system_reports,
        missing_matrix=missing_matrix,
        catalog_gaps=catalog_gaps,
        delivery_gaps=delivery_gaps,
        reasons=reasons,
        warnings=warnings,
    )


def _validate_variant_order(
    index: int,
    value: Any,
    *,
    target_modules: list[str],
    lines: dict[str, dict[str, Any]],
    catalog_keys: set[str],
    require_delivered: bool,
) -> dict[str, Any]:
    order_reasons: list[str] = []
    catalog_reasons: list[str] = []
    delivery_reasons: list[str] = []
    warnings: list[str] = []
    if not isinstance(value, dict):
        return _asset_report(
            index=index,
            module=None,
            line_id=None,
            asset_key=None,
            variant_key=None,
            catalog_status="unknown",
            delivery_status="unknown",
            order_reasons=["must be an object"],
            catalog_reasons=[],
            delivery_reasons=[],
            warnings=[],
        )

    if value.get("asset_kind") != ASSET_KIND:
        order_reasons.append(f"asset_kind: expected {ASSET_KIND}")
    if value.get("activate_runtime") is True:
        order_reasons.append("activate_runtime: order manifests must not activate runtime assets")

    module = value.get("module")
    asset_key = value.get("asset_key")
    variant_key = value.get("variant_key")
    line_id = value.get("line_id")

    if module not in target_modules:
        order_reasons.append(f"module: expected one of {target_modules}, got {module!r}")
    if not _safe_slug(asset_key):
        order_reasons.append("asset_key: must be a path-safe slug")
    if not _non_empty_string(line_id) or line_id not in lines:
        order_reasons.append(f"line_id: must reference required_lines, got {line_id!r}")
    if isinstance(module, str) and isinstance(asset_key, str):
        expected_variant_key = f"{module}:{asset_key}"
        if variant_key != expected_variant_key:
            order_reasons.append(f"variant_key: expected {expected_variant_key}, got {variant_key!r}")
        _validate_expected_paths(value, module, asset_key, order_reasons)
    if not _non_empty_string(value.get("design_intent")):
        order_reasons.append("design_intent: required non-empty string")

    _validate_mirror(value, order_reasons)

    catalog_status = "present" if isinstance(variant_key, str) and variant_key in catalog_keys else "missing"
    if catalog_status == "missing" and require_delivered:
        catalog_reasons.append(f"catalog: {variant_key!r} not declared in variant_catalog.json")

    delivery_status = _delivery_status(value, delivery_reasons, require_delivered=require_delivered)
    if delivery_status == "missing" and require_delivered:
        delivery_reasons.append("delivery: required GLB/source/sidecar/preview files are missing")

    return _asset_report(
        index=index,
        module=module,
        line_id=line_id,
        asset_key=asset_key,
        variant_key=variant_key,
        catalog_status=catalog_status,
        delivery_status=delivery_status,
        order_reasons=order_reasons,
        catalog_reasons=catalog_reasons,
        delivery_reasons=delivery_reasons,
        warnings=warnings,
    )


def _validate_expected_paths(value: dict[str, Any], module: str, asset_key: str, reasons: list[str]) -> None:
    stem = f"{module}__{asset_key}"
    base = f"{ARMOR_ROOT}/{module}/variants/{asset_key}"
    expected = {
        "expected_glb_path": f"{base}/{stem}.glb",
        "expected_sidecar_path": f"{base}/{stem}.modeler.json",
        "expected_source_blend_path": f"{base}/source/{stem}.blend",
        "expected_preview_mesh_path": f"{base}/preview/{stem}.mesh.json",
    }
    for field, expected_path in expected.items():
        path = _repo_relative_path(value.get(field), reasons, field)
        if path is not None and _posix(value.get(field)) != expected_path:
            reasons.append(f"{field}: expected {expected_path}, got {_posix(value.get(field))}")


def _validate_mirror(value: dict[str, Any], reasons: list[str]) -> None:
    module = value.get("module")
    asset_key = value.get("asset_key")
    mirror_of = value.get("mirror_of")
    if not isinstance(module, str) or not isinstance(asset_key, str):
        return
    if module.startswith("right_"):
        expected = f"left_{module.removeprefix('right_')}:{asset_key}"
        if mirror_of != expected:
            reasons.append(f"mirror_of: expected {expected}, got {mirror_of!r}")
    elif mirror_of is not None:
        reasons.append("mirror_of: left-side or center orders must not declare mirror_of")


def _delivery_status(value: dict[str, Any], reasons: list[str], *, require_delivered: bool) -> str:
    paths: dict[str, Path | None] = {
        field: _repo_relative_path(value.get(field), reasons, field)
        for field in PATH_FIELDS
    }
    missing = [field for field, path in paths.items() if path is None or not path.is_file()]
    sidecar_path = paths.get("expected_sidecar_path")
    if sidecar_path is not None and sidecar_path.is_file():
        sidecar = _read_json_object(sidecar_path, reasons, "expected_sidecar_path")
        if sidecar is not None and require_delivered:
            _validate_sidecar_acceptance(sidecar, value, reasons)
    return "missing" if missing else "present"


def _validate_sidecar_acceptance(sidecar: dict[str, Any], order: dict[str, Any], reasons: list[str]) -> None:
    module = order.get("module")
    variant_key = order.get("variant_key")
    if sidecar.get("module") not in (None, module):
        reasons.append(f"sidecar.module: expected {module}, got {sidecar.get('module')!r}")
    if sidecar.get("variant_key") != variant_key:
        reasons.append(f"sidecar.variant_key: expected {variant_key}, got {sidecar.get('variant_key')!r}")
    if sidecar.get("line_id") != order.get("line_id"):
        reasons.append(f"sidecar.line_id: expected {order.get('line_id')}, got {sidecar.get('line_id')!r}")
    if sidecar.get("runtime_activation_allowed") is True:
        reasons.append(
            "sidecar.runtime_activation_allowed: must not be true; P1 acceptance is not runtime activation"
        )
    if sidecar.get("activate_runtime") is True:
        reasons.append("sidecar.activate_runtime: must not be true; use a separate runtime activation change")
    for field in REQUIRED_SIDECAR_FIELDS:
        value = sidecar.get(field)
        if field == "source_concept_ids":
            if not isinstance(value, list) or not all(_non_empty_string(item) for item in value):
                reasons.append("sidecar.source_concept_ids: required non-empty string list")
        elif not _non_empty_string(value):
            reasons.append(f"sidecar.{field}: required non-empty string")


def _validate_expected_matrix(
    reports: list[dict[str, Any]],
    *,
    target_modules: list[str],
    lines: dict[str, dict[str, Any]],
    required_per_module: int,
    reasons: list[str],
) -> None:
    by_module: dict[str, list[dict[str, Any]]] = {module: [] for module in target_modules}
    for report in reports:
        module = report.get("module")
        if isinstance(module, str) and module in by_module:
            by_module[module].append(report)
    for module, module_reports in by_module.items():
        if len(module_reports) != required_per_module:
            reasons.append(f"{module}: expected {required_per_module} ordered variant(s), got {len(module_reports)}")
        present_lines = {report.get("line_id") for report in module_reports}
        missing_lines = [line_id for line_id in lines if line_id not in present_lines]
        if missing_lines:
            reasons.append(f"{module}: missing required line order(s) {missing_lines}")


def _module_reports(
    reports: list[dict[str, Any]],
    *,
    target_modules: list[str],
    lines: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for module in target_modules:
        module_assets = [report for report in reports if report.get("module") == module]
        ordered_lines = sorted({str(report.get("line_id")) for report in module_assets if report.get("line_id")})
        result[module] = {
            "ordered_count": len(module_assets),
            "required_line_count": len(lines),
            "ordered_lines": ordered_lines,
            "missing_lines": [line_id for line_id in lines if line_id not in ordered_lines],
            "catalog_missing_count": sum(1 for report in module_assets if report.get("catalog_status") == "missing"),
            "delivery_missing_count": sum(1 for report in module_assets if report.get("delivery_status") == "missing"),
        }
    return result


def _line_system_reports(
    reports: list[dict[str, Any]],
    *,
    lines: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for line_id in lines:
        line_assets = [report for report in reports if report.get("line_id") == line_id]
        accepted = [
            report
            for report in line_assets
            if report.get("p1_acceptance", {}).get("package_gate_status") == P1_ACCEPTANCE_PASS
        ]
        blocked = [report for report in line_assets if report not in accepted]
        result[line_id] = {
            "ordered_count": len(line_assets),
            "accepted_count": len(accepted),
            "blocked_count": len(blocked),
            "package_gate_status": P1_ACCEPTANCE_PASS if line_assets and not blocked else P1_ACCEPTANCE_BLOCK,
            "runtime_activation_label": RUNTIME_ACTIVATION_BLOCKED,
            "limb_families": sorted({_limb_family(str(report.get("module") or "")) for report in line_assets}),
        }
    return result


def _line_map(value: Any, reasons: list[str]) -> dict[str, dict[str, Any]]:
    if not isinstance(value, list) or not value:
        reasons.append("required_lines: required non-empty list")
        return {}
    result: dict[str, dict[str, Any]] = {}
    for index, line in enumerate(value):
        if not isinstance(line, dict):
            reasons.append(f"required_lines[{index}]: must be an object")
            continue
        line_id = line.get("line_id")
        if not _non_empty_string(line_id):
            reasons.append(f"required_lines[{index}].line_id: required non-empty string")
            continue
        if line_id in result:
            reasons.append(f"required_lines[{index}].line_id: duplicate {line_id}")
        concepts = line.get("source_concept_ids")
        if not isinstance(concepts, list) or not all(_non_empty_string(item) for item in concepts):
            reasons.append(f"required_lines[{index}].source_concept_ids: required non-empty string list")
        result[str(line_id)] = line
    return result


def _catalog_variant_keys(catalog_path: str | Path) -> tuple[set[str], list[str]]:
    path = _repo_path(catalog_path)
    warnings: list[str] = []
    payload = _read_json_object(path, warnings, "catalog")
    if payload is None:
        return set(), warnings
    modules = payload.get("modules", payload.get("parts"))
    if not isinstance(modules, dict):
        warnings.append("catalog: modules object missing")
        return set(), warnings
    keys: set[str] = set()
    for module_payload in modules.values():
        if not isinstance(module_payload, dict):
            continue
        variants = module_payload.get("variants")
        if isinstance(variants, dict):
            variants = list(variants.values())
        if not isinstance(variants, list):
            continue
        for variant in variants:
            if isinstance(variant, dict) and _non_empty_string(variant.get("variant_key")):
                keys.add(str(variant["variant_key"]).strip())
    return keys, warnings


def _asset_report(
    *,
    index: int,
    module: Any,
    line_id: Any,
    asset_key: Any,
    variant_key: Any,
    catalog_status: str,
    delivery_status: str,
    order_reasons: list[str],
    catalog_reasons: list[str],
    delivery_reasons: list[str],
    warnings: list[str],
) -> dict[str, Any]:
    reasons = order_reasons + catalog_reasons + delivery_reasons
    p1_acceptance = _asset_p1_acceptance(
        catalog_status=catalog_status,
        delivery_status=delivery_status,
        reasons=reasons,
    )
    return {
        "index": index,
        "module": module,
        "line_id": line_id,
        "side": _limb_side(str(module or "")),
        "limb_family": _limb_family(str(module or "")),
        "asset_key": asset_key,
        "variant_key": variant_key,
        "catalog_status": catalog_status,
        "delivery_status": delivery_status,
        "status": "fail" if reasons else "open" if catalog_status == "missing" or delivery_status == "missing" else "pass",
        "p1_acceptance": p1_acceptance,
        "stage_reasons": {
            "order": order_reasons,
            "delivery": delivery_reasons,
            "catalog_registration": catalog_reasons,
            "runtime_activation": [],
        },
        "reasons": reasons,
        "warnings": warnings,
    }


def _asset_p1_acceptance(
    *,
    catalog_status: str,
    delivery_status: str,
    reasons: list[str],
) -> dict[str, Any]:
    complete = not reasons and catalog_status == "present" and delivery_status == "present"
    if complete:
        status = "accepted"
    elif catalog_status == "missing" and delivery_status == "missing":
        status = "blocked_catalog_and_delivery_missing"
    elif catalog_status == "missing":
        status = "blocked_catalog_missing"
    elif delivery_status == "missing":
        status = "blocked_delivery_missing"
    else:
        status = "blocked_manifest_or_sidecar_error"
    return {
        "phase": P1_ACCEPTANCE_PHASE,
        "status": status,
        "package_gate_status": P1_ACCEPTANCE_PASS if complete else P1_ACCEPTANCE_BLOCK,
        "acceptance_complete": complete,
        "runtime_activation_allowed": False,
        "runtime_activation_label": RUNTIME_ACTIVATION_BLOCKED,
        "meaning": (
            "P1 variant acceptance proves delivered files, catalog declaration, sidecar metadata, "
            "and review readiness; it does not activate Web/Quest runtime selection"
        ),
    }


def _limb_family(module: str) -> str:
    for family in ("upperarm", "forearm", "hand", "thigh"):
        if module.endswith(f"_{family}"):
            return family
    return "unknown"


def _limb_side(module: str) -> str:
    if module.startswith("left_"):
        return "left"
    if module.startswith("right_"):
        return "right"
    return "unknown"


def _missing_matrix(
    reports: list[dict[str, Any]],
    *,
    lines: dict[str, dict[str, Any]],
    target_modules: list[str],
) -> dict[str, Any]:
    entries = _missing_matrix_entries(reports, lines=lines, target_modules=target_modules)
    current_stop_counts = {
        stage: sum(1 for entry in entries if entry["current_stop_stage"] == stage)
        for stage in STAGE_ORDER
    }
    stage_counts = {
        "order": {
            "ordered_count": sum(1 for entry in entries if entry["order_status"] == "ordered"),
            "blocked_count": sum(1 for entry in entries if entry["order_status"] != "ordered"),
        },
        "delivery": _status_counts(entries, "delivery_status"),
        "catalog_registration": _status_counts(entries, "catalog_registration_status"),
        "runtime_activation": {
            "allowed_count": sum(1 for entry in entries if entry["runtime_activation_allowed"]),
            "blocked_count": sum(1 for entry in entries if not entry["runtime_activation_allowed"]),
        },
        "current_stop": current_stop_counts,
    }
    return {
        "contract_version": MISSING_MATRIX_CONTRACT,
        "axis": ["line_id", "limb_family", "side"],
        "stage_order": list(STAGE_ORDER),
        "entry_count": len(entries),
        "p1_blocked_asset_count": sum(1 for entry in entries if not entry["p1_acceptance_complete"]),
        "runtime_activation_blocked_count": sum(
            1 for entry in entries if not entry["runtime_activation_allowed"]
        ),
        "stage_counts": stage_counts,
        "by_line": _missing_matrix_by_line(entries, lines=lines),
        "entries": entries,
    }


def _missing_matrix_entries(
    reports: list[dict[str, Any]],
    *,
    lines: dict[str, dict[str, Any]],
    target_modules: list[str],
) -> list[dict[str, Any]]:
    if not lines or not target_modules:
        return [_missing_matrix_entry(report, lines=lines) for report in reports]

    report_by_cell: dict[tuple[str, str], dict[str, Any]] = {}
    used_indexes: set[int] = set()
    for report in reports:
        module = report.get("module")
        line_id = report.get("line_id")
        if isinstance(module, str) and isinstance(line_id, str):
            report_by_cell.setdefault((module, line_id), report)

    entries: list[dict[str, Any]] = []
    for line_id in lines:
        for module in target_modules:
            report = report_by_cell.get((module, line_id))
            if report is None:
                entries.append(_missing_order_matrix_entry(module=module, line_id=line_id, lines=lines))
                continue
            used_indexes.add(int(report.get("index", -1)))
            entries.append(_missing_matrix_entry(report, lines=lines))

    extra_reports = [
        report
        for report in reports
        if isinstance(report.get("index"), int) and report["index"] not in used_indexes
    ]
    entries.extend(_missing_matrix_entry(report, lines=lines) for report in extra_reports)
    return entries


def _missing_order_matrix_entry(
    *,
    module: str,
    line_id: str,
    lines: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    line = lines.get(line_id, {})
    return {
        "line_id": line_id,
        "line_label": line.get("line_label"),
        "source_concept_ids": line.get("source_concept_ids", []),
        "limb_family": _limb_family(module),
        "side": _limb_side(module),
        "module": module,
        "asset_key": None,
        "variant_key": None,
        "order_status": "missing_order",
        "delivery_status": "not_ordered",
        "catalog_registration_status": "not_ordered",
        "runtime_activation_status": RUNTIME_ACTIVATION_BLOCKED,
        "runtime_activation_allowed": False,
        "p1_acceptance_complete": False,
        "package_gate_status": P1_ACCEPTANCE_BLOCK,
        "blocked_stages": list(STAGE_ORDER),
        "current_stop_stage": "order",
        "stage_reasons": {
            "order": [f"missing order row for {module} / {line_id}"],
            "delivery": [],
            "catalog_registration": [],
            "runtime_activation": [],
        },
    }


def _missing_matrix_entry(report: dict[str, Any], *, lines: dict[str, dict[str, Any]]) -> dict[str, Any]:
    stage_reasons = report.get("stage_reasons")
    if not isinstance(stage_reasons, dict):
        stage_reasons = {}
    p1_acceptance = report.get("p1_acceptance")
    if not isinstance(p1_acceptance, dict):
        p1_acceptance = {}
    line_id = report.get("line_id")
    line = lines.get(str(line_id), {}) if isinstance(line_id, str) else {}
    order_blocked = bool(stage_reasons.get("order"))
    p1_complete = bool(p1_acceptance.get("acceptance_complete"))
    blocked_stages: list[str] = []
    if order_blocked:
        blocked_stages.append("order")
    if report.get("delivery_status") != "present" or stage_reasons.get("delivery"):
        blocked_stages.append("delivery")
    if report.get("catalog_status") != "present" or stage_reasons.get("catalog_registration"):
        blocked_stages.append("catalog_registration")
    if not p1_acceptance.get("runtime_activation_allowed", False):
        blocked_stages.append("runtime_activation")

    return {
        "line_id": line_id,
        "line_label": line.get("line_label"),
        "source_concept_ids": line.get("source_concept_ids", []),
        "limb_family": report.get("limb_family"),
        "side": report.get("side"),
        "module": report.get("module"),
        "asset_key": report.get("asset_key"),
        "variant_key": report.get("variant_key"),
        "order_status": "blocked_order_invalid" if order_blocked else "ordered",
        "delivery_status": report.get("delivery_status"),
        "catalog_registration_status": report.get("catalog_status"),
        "runtime_activation_status": (
            "allowed" if p1_acceptance.get("runtime_activation_allowed") else RUNTIME_ACTIVATION_BLOCKED
        ),
        "runtime_activation_allowed": bool(p1_acceptance.get("runtime_activation_allowed", False)),
        "p1_acceptance_complete": p1_complete,
        "package_gate_status": p1_acceptance.get("package_gate_status", P1_ACCEPTANCE_BLOCK),
        "blocked_stages": blocked_stages,
        "current_stop_stage": _current_stop_stage(blocked_stages),
        "stage_reasons": {
            "order": list(stage_reasons.get("order") or []),
            "delivery": list(stage_reasons.get("delivery") or []),
            "catalog_registration": list(stage_reasons.get("catalog_registration") or []),
            "runtime_activation": list(stage_reasons.get("runtime_activation") or []),
        },
    }


def _current_stop_stage(blocked_stages: list[str]) -> str | None:
    for stage in STAGE_ORDER:
        if stage in blocked_stages:
            return stage
    return None


def _status_counts(entries: list[dict[str, Any]], field: str) -> dict[str, int]:
    values = sorted({str(entry.get(field)) for entry in entries if entry.get(field) is not None})
    return {f"{value}_count": sum(1 for entry in entries if entry.get(field) == value) for value in values}


def _missing_matrix_by_line(
    entries: list[dict[str, Any]],
    *,
    lines: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    line_ids = list(lines) + sorted(
        {
            str(entry["line_id"])
            for entry in entries
            if _non_empty_string(entry.get("line_id")) and str(entry["line_id"]) not in lines
        }
    )
    for line_id in line_ids:
        line_entries = [entry for entry in entries if entry.get("line_id") == line_id]
        line_payload = lines.get(line_id, {})
        result[line_id] = {
            "line_label": line_payload.get("line_label"),
            "source_concept_ids": line_payload.get("source_concept_ids", []),
            "asset_count": len(line_entries),
            "p1_blocked_asset_count": sum(1 for entry in line_entries if not entry["p1_acceptance_complete"]),
            "runtime_activation_blocked_count": sum(
                1 for entry in line_entries if not entry["runtime_activation_allowed"]
            ),
            "families": _missing_matrix_families(line_entries),
        }
    return result


def _missing_matrix_families(entries: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for family in ("upperarm", "forearm", "hand", "thigh"):
        family_entries = [entry for entry in entries if entry.get("limb_family") == family]
        result[family] = {
            side: _compact_missing_matrix_entry(next((entry for entry in family_entries if entry.get("side") == side), None))
            for side in ("left", "right")
        }
    return result


def _compact_missing_matrix_entry(entry: dict[str, Any] | None) -> dict[str, Any]:
    if entry is None:
        return {
            "variant_key": None,
            "current_stop_stage": "order",
            "blocked_stages": ["order"],
            "package_gate_status": P1_ACCEPTANCE_BLOCK,
        }
    return {
        "variant_key": entry.get("variant_key"),
        "order_status": entry.get("order_status"),
        "delivery_status": entry.get("delivery_status"),
        "catalog_registration_status": entry.get("catalog_registration_status"),
        "runtime_activation_status": entry.get("runtime_activation_status"),
        "current_stop_stage": entry.get("current_stop_stage"),
        "blocked_stages": entry.get("blocked_stages", []),
        "package_gate_status": entry.get("package_gate_status"),
    }


def _result(
    *,
    manifest: Path,
    catalog_path: str | Path,
    require_delivered: bool,
    asset_reports: list[dict[str, Any]],
    module_reports: dict[str, Any],
    line_system_reports: dict[str, Any],
    missing_matrix: dict[str, Any],
    catalog_gaps: list[dict[str, Any]],
    delivery_gaps: list[dict[str, Any]],
    reasons: list[str],
    warnings: list[str],
) -> dict[str, Any]:
    status = "fail" if reasons else "warn" if warnings else "pass"
    accepted_count = sum(
        1
        for report in asset_reports
        if report.get("p1_acceptance", {}).get("package_gate_status") == P1_ACCEPTANCE_PASS
    )
    acceptance_complete = bool(asset_reports) and accepted_count == len(asset_reports) and not reasons
    return {
        "ok": not reasons,
        "status": status,
        "manifest": _rel(manifest),
        "catalog_path": _rel(_repo_path(catalog_path)),
        "require_delivered": require_delivered,
        "asset_count": len(asset_reports),
        "catalog_gap_count": len(catalog_gaps),
        "delivery_gap_count": len(delivery_gaps),
        "p1_acceptance": {
            "phase": P1_ACCEPTANCE_PHASE,
            "package_gate_status": P1_ACCEPTANCE_PASS if acceptance_complete else P1_ACCEPTANCE_BLOCK,
            "acceptance_complete": acceptance_complete,
            "accepted_asset_count": accepted_count,
            "blocked_asset_count": len(asset_reports) - accepted_count,
            "runtime_activation_allowed": False,
            "runtime_activation_label": RUNTIME_ACTIVATION_BLOCKED,
        },
        "module_reports": module_reports,
        "line_system_reports": line_system_reports,
        "missing_matrix": missing_matrix,
        "reasons": reasons,
        "warnings": warnings,
        "assets": asset_reports,
    }


def _repo_path(path: str | Path) -> Path:
    path = Path(path)
    if path.is_absolute():
        return path
    return (REPO_ROOT / path).resolve()


def _repo_relative_path(value: Any, reasons: list[str], label: str) -> Path | None:
    if not _non_empty_string(value):
        reasons.append(f"{label}: path must be a non-empty string")
        return None
    raw = Path(str(value))
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


def _read_json_object(path: Path, messages: list[str], label: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        messages.append(f"{label}: invalid JSON: {exc}")
        return None
    if not isinstance(payload, dict):
        messages.append(f"{label}: JSON root must be an object")
        return None
    return payload


def _check_existing_file(path: Path | None, reasons: list[str], label: str) -> None:
    if path is None:
        return
    if not path.is_file():
        reasons.append(f"{label}: file missing: {_rel(path)}")


def _rel(path: str | Path) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def _posix(path: Any) -> str:
    return Path(str(path)).as_posix()


def _safe_slug(value: Any) -> bool:
    return _non_empty_string(value) and not any(token in str(value) for token in (":", "/", "\\"))


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST, type=Path, help="Order manifest path")
    parser.add_argument("--catalog", default=DEFAULT_CATALOG, type=Path, help="variant_catalog.json path")
    parser.add_argument(
        "--require-delivered",
        action="store_true",
        help="Promote missing catalog/file/sidecar acceptance gaps to failures",
    )
    parser.add_argument("--report-json", action="store_true", help="Emit structured JSON")
    args = parser.parse_args(argv)

    result = validate_order_manifest(
        args.manifest,
        catalog_path=args.catalog,
        require_delivered=args.require_delivered,
    )
    if args.report_json:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        print(f"[{result['status'].upper()}] {result['manifest']}")
        print(f"ordered variants: {result['asset_count']}")
        print(f"catalog gaps: {result['catalog_gap_count']}")
        print(f"delivery gaps: {result['delivery_gap_count']}")
        for reason in result["reasons"]:
            print(f"  fail  {reason}")
        for warning in result["warnings"]:
            print(f"  warn  {warning}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
