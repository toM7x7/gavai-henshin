"""Validate exhibition PC release-package completeness.

This is a read-only gate for the package copied to an external exhibition PC.
It checks that critical runtime code, armor assets, replay schema/examples, and
operator docs are present. When run inside a git checkout, it also reports
critical files that exist but are not tracked, because those files would be
missing from a normal git/archive-based release package.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


CONTRACT_VERSION = "exhibition-release-package-completeness.v1"
DEFAULT_ARMOR_ROOT = Path("viewer/assets/armor-parts")
DEFAULT_VARIANT_GLB_COUNT = 54
DEFAULT_TOPPING_GLB_COUNT = 32
MODEL_BBOX_PASS_TOLERANCE_RATIO = 0.10
MODEL_BBOX_FAIL_TOLERANCE_RATIO = 0.15
AXES = ("x", "y", "z")
JAPANESE_TEXT_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")
BODY_WRAP_LOOP_METADATA_ONLY_STATUSES = {
    "contract_metadata_only_glb_not_regenerated",
    "metadata_only",
    "spec_metadata_only",
    "primitive_available_not_applied_until_blender_rebuild",
}
BODY_WRAP_LOOP_EXPORTED_STATUSES = {
    "glb_loop_exported",
    "body_wrap_loop_glb_exported",
    "exported_glb_loop",
    "applied_to_glb",
}
BODY_WRAP_LOOP_CONTRACT_KEYS = (
    "waist_fit",
    "body_wrap_loop_contract",
    "body_wrap_coverage_contract",
)
BODY_WRAP_LOOP_STATUS_KEYS = (
    "body_wrap_loop_export_status",
    "asset_status",
    "adoption_status",
)

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

REQUIRED_FILES: tuple[tuple[str, str], ...] = (
    ("runtime", "package.json"),
    ("runtime", ".env.demo.example"),
    ("runtime", "pyproject.toml"),
    ("runtime", "vite.quest.config.js"),
    ("runtime", "tools/run_henshin.py"),
    ("runtime", "tools/exhibition_smoke_check.py"),
    ("runtime", "tools/smoke_web_glb_load.py"),
    ("runtime", "tools/validate_variant_catalog.py"),
    ("runtime", "tools/validate_modeler_variant_order_manifest.py"),
    ("runtime", "tools/validate_exhibition_release_package.py"),
    ("runtime", "src/henshin/forge.py"),
    ("runtime", "src/henshin/runtime_package.py"),
    ("runtime", "src/henshin/new_route_api.py"),
    ("runtime", "src/henshin/dashboard_server.py"),
    ("runtime", "src/henshin/validators.py"),
    ("runtime", "src/henshin/variant_selection.py"),
    ("runtime", "src/henshin/armor_fit_contract.py"),
    ("runtime", "src/henshin/modeler_blueprints.py"),
    ("viewer", "viewer/armor-forge/index.html"),
    ("viewer", "viewer/armor-forge/forge.js"),
    ("viewer", "viewer/armor-forge/styles.css"),
    ("viewer", "viewer/quest-iw-demo/index.html"),
    ("viewer", "viewer/quest-iw-demo/quest-demo.js"),
    ("armor", "viewer/assets/armor-parts/variant_catalog.json"),
    ("replay", "schemas/replay-record.v0.2.schema.json"),
    ("replay", "examples/replay-record.sample.json"),
    ("examples", "examples/suitspec.sample.json"),
    ("examples", "examples/modeler_delivery_manifest.sample.json"),
    ("operator_docs", "docs/exhibition-pc-runbook-2026-05-04.md"),
    ("operator_docs", "docs/exhibition-day-one-page-checklist-2026-05-04.md"),
    ("operator_docs", "docs/exhibition-pc-release-package-manifest-2026-05-04.md"),
    ("operator_docs", "docs/exhibition-service-mocopi-roadmap-2026-05-04.md"),
    ("operator_docs", "docs/web-service-phase0-task-breakdown-2026-05-02.md"),
    ("operator_docs", "docs/quest-mocopi-exhibition-spike-2026-05-04.md"),
    ("operator_docs", "docs/modeler-exhibition-readiness-risks-2026-05-04.md"),
    ("operator_docs", "docs/modeler-triview-30variant-audit-table-2026-05-03.md"),
    ("operator_docs", "docs/quest-deposition-visual-direction-2026-05-04.md"),
    ("operator_docs", "docs/exhibition-ui-redesign-backlog-2026-05-04.md"),
    ("operator_docs", "docs/p1-limb-variant-order-acceptance-2026-05-03.md"),
    ("operator_docs", "docs/modeler-deliveries/p1-limb-three-line-variants-2026-05-03.order-manifest.json"),
    ("operator_docs", "docs/current-web-quest-check-guide.md"),
    ("operator_docs", "docs/replay-record-contract.md"),
)


@dataclass(frozen=True)
class GlobRequirement:
    category: str
    pattern: str
    minimum_count: int
    description: str


def validate_release_package(
    repo_root: str | Path = ".",
    *,
    check_git_tracking: bool | None = None,
    allow_untracked_for_local_snapshot: bool = False,
    expected_variant_glbs: int = DEFAULT_VARIANT_GLB_COUNT,
    expected_topping_glbs: int = DEFAULT_TOPPING_GLB_COUNT,
) -> dict[str, Any]:
    """Validate a repo checkout or copied release package root."""

    root = Path(repo_root).resolve()
    missing: list[dict[str, Any]] = []
    pattern_gaps: list[dict[str, Any]] = []
    untracked: list[dict[str, Any]] = []
    warnings: list[str] = []
    tracked_candidates: dict[str, set[str]] = {}

    for category, rel_path in REQUIRED_FILES:
        _require_file(root, category, rel_path, missing, tracked_candidates)

    for module in EXPECTED_MODULES:
        _require_file(root, "armor", f"viewer/assets/armor-parts/{module}/{module}.glb", missing, tracked_candidates)
        _require_file(
            root,
            "armor",
            f"viewer/assets/armor-parts/{module}/{module}.modeler.json",
            missing,
            tracked_candidates,
        )
        _require_file(
            root,
            "armor",
            f"viewer/assets/armor-parts/{module}/preview/{module}.mesh.json",
            missing,
            tracked_candidates,
        )

    glob_requirements = _glob_requirements(expected_variant_glbs, expected_topping_glbs)
    for requirement in glob_requirements:
        matches = _match_files(root, requirement.pattern)
        for path in matches:
            _track_candidate(tracked_candidates, requirement.category, _rel(root, path))
        if len(matches) < requirement.minimum_count:
            pattern_gaps.append(
                {
                    "category": requirement.category,
                    "pattern": requirement.pattern,
                    "description": requirement.description,
                    "minimum_count": requirement.minimum_count,
                    "actual_count": len(matches),
                    "missing_count": requirement.minimum_count - len(matches),
                }
            )

    catalog_result = _validate_catalog_refs(root, tracked_candidates)
    missing.extend(catalog_result["missing"])
    warnings.extend(catalog_result["warnings"])
    model_quality = _model_quality_adjustments(root)
    warnings.extend(model_quality["warnings"])
    experience_gates = _experience_gates(root, model_quality)
    warnings.extend(experience_gates["warnings"])
    p1_acceptance = _p1_limb_acceptance_summary(root)
    warnings.extend(p1_acceptance["warnings"])

    git_checked = False
    git_available = _is_git_worktree(root)
    if check_git_tracking is None:
        check_git_tracking = git_available
    if check_git_tracking:
        if git_available:
            git_checked = True
            tracked_paths = _git_tracked_paths(root)
            for rel_path, categories in sorted(tracked_candidates.items()):
                if rel_path not in tracked_paths:
                    untracked.append(
                        {
                            "path": rel_path,
                            "categories": sorted(categories),
                            "reason": "critical release-package file exists but is not tracked by git",
                        }
                    )
        else:
            warnings.append("git tracking check skipped: repo root is not a git worktree")

    reasons = []
    reasons.extend(f"missing {entry['path']}" for entry in missing)
    reasons.extend(
        f"pattern {entry['pattern']} has {entry['actual_count']} file(s), expected at least {entry['minimum_count']}"
        for entry in pattern_gaps
    )
    reasons.extend(
        f"model quality fail {entry['module']}: max bbox delta {entry['max_abs_delta_pct']}%"
        for entry in model_quality["parts"]
        if entry["status"] == "fail"
    )
    reasons.extend(p1_acceptance["reasons"])
    untracked_blocking = bool(untracked) and not allow_untracked_for_local_snapshot
    if untracked_blocking:
        reasons.extend(f"untracked {entry['path']}" for entry in untracked)
    elif untracked:
        warnings.append(
            "git tracking gate: "
            f"{len(untracked)} critical untracked file(s) allowed for explicit local snapshot; "
            "copy/export must include these paths and preserve this report."
        )
    has_warnings = bool(warnings) or model_quality["warning_count"] > 0 or experience_gates["warning_count"] > 0

    return {
        "contract_version": CONTRACT_VERSION,
        "ok": not reasons,
        "status": "fail" if reasons else "warn" if has_warnings else "pass",
        "repo_root": root.as_posix(),
        "git_tracking": {
            "requested": bool(check_git_tracking),
            "checked": git_checked,
            "worktree": git_available,
            "allow_untracked_for_local_snapshot": allow_untracked_for_local_snapshot,
            "untracked_blocking": untracked_blocking,
            "untracked_policy": "local_snapshot_allowed"
            if allow_untracked_for_local_snapshot
            else "tracked_release_required",
        },
        "missing_count": len(missing),
        "pattern_gap_count": len(pattern_gaps),
        "untracked_count": len(untracked),
        "reasons": reasons,
        "warnings": warnings,
        "missing": missing,
        "pattern_gaps": pattern_gaps,
        "untracked": untracked,
        "model_quality": model_quality,
        "model_quality_warning_count": model_quality["warning_count"],
        "model_quality_fail_count": model_quality["fail_count"],
        "experience_gates": experience_gates,
        "experience_warning_count": experience_gates["warning_count"],
        "p1_acceptance": p1_acceptance,
        "p1_acceptance_warning_count": len(p1_acceptance["warnings"]),
        "tracked_candidate_count": len(tracked_candidates),
        "expected_variant_glbs": expected_variant_glbs,
        "expected_topping_glbs": expected_topping_glbs,
    }


def _glob_requirements(expected_variant_glbs: int, expected_topping_glbs: int) -> tuple[GlobRequirement, ...]:
    return (
        GlobRequirement("runtime", "src/henshin/*.py", 1, "runtime Python source modules"),
        GlobRequirement("viewer", "viewer/armor-forge/*", 3, "Web Forge static files"),
        GlobRequirement("viewer", "viewer/quest-iw-demo/*", 2, "Quest runtime static files"),
        GlobRequirement("armor", "viewer/assets/armor-parts/*/*.glb", len(EXPECTED_MODULES), "canonical armor GLBs"),
        GlobRequirement(
            "armor",
            "viewer/assets/armor-parts/*/*.modeler.json",
            len(EXPECTED_MODULES),
            "canonical armor sidecars",
        ),
        GlobRequirement(
            "armor",
            "viewer/assets/armor-parts/*/preview/*.mesh.json",
            len(EXPECTED_MODULES),
            "canonical armor preview meshes",
        ),
        GlobRequirement(
            "armor_variants",
            "viewer/assets/armor-parts/*/variants/*/*.glb",
            expected_variant_glbs,
            "delivered variant GLBs",
        ),
        GlobRequirement(
            "armor_variants",
            "viewer/assets/armor-parts/*/variants/*/*.modeler.json",
            expected_variant_glbs,
            "delivered variant sidecars",
        ),
        GlobRequirement(
            "armor_variants",
            "viewer/assets/armor-parts/*/variants/*/preview/*.mesh.json",
            expected_variant_glbs,
            "delivered variant preview meshes",
        ),
        GlobRequirement(
            "armor_toppings",
            "viewer/assets/armor-parts/*/toppings/*/*/*.glb",
            expected_topping_glbs,
            "delivered topping GLBs",
        ),
        GlobRequirement(
            "armor_toppings",
            "viewer/assets/armor-parts/*/toppings/*/*/*.modeler.json",
            expected_topping_glbs,
            "delivered topping sidecars",
        ),
        GlobRequirement(
            "armor_toppings",
            "viewer/assets/armor-parts/*/toppings/*/*/preview/*.mesh.json",
            expected_topping_glbs,
            "delivered topping preview meshes",
        ),
        GlobRequirement("replay", "schemas/*.schema.json", 1, "portable replay schemas"),
    )


def _validate_catalog_refs(root: Path, tracked_candidates: dict[str, set[str]]) -> dict[str, Any]:
    missing: list[dict[str, Any]] = []
    warnings: list[str] = []
    catalog_path = root / "viewer/assets/armor-parts/variant_catalog.json"
    if not catalog_path.is_file():
        return {"missing": missing, "warnings": warnings}
    try:
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"variant catalog refs skipped: unreadable JSON: {exc}")
        return {"missing": missing, "warnings": warnings}

    for asset_ref in sorted(_iter_asset_refs(payload)):
        if _unsafe_package_path(asset_ref):
            missing.append(
                {
                    "category": "armor_catalog_ref",
                    "path": asset_ref,
                    "reason": "variant catalog asset_ref must be a repo-relative path inside the package",
                }
            )
            continue
        _require_file(root, "armor_catalog_ref", asset_ref, missing, tracked_candidates)
        glb = Path(asset_ref)
        stem = glb.stem
        parent = glb.parent.as_posix()
        _require_file(root, "armor_catalog_ref", f"{parent}/{stem}.modeler.json", missing, tracked_candidates)
        _require_file(root, "armor_catalog_ref", f"{parent}/preview/{stem}.mesh.json", missing, tracked_candidates)

    return {"missing": missing, "warnings": warnings}


def _model_quality_adjustments(root: Path) -> dict[str, Any]:
    parts: list[dict[str, Any]] = []
    warnings: list[str] = []
    micro_dimension_warnings: list[dict[str, Any]] = []
    fidelity_acceptance_blockers: list[dict[str, Any]] = []
    for module in EXPECTED_MODULES:
        sidecar_path = root / "viewer" / "assets" / "armor-parts" / module / f"{module}.modeler.json"
        if not sidecar_path.is_file():
            continue
        try:
            payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"{module}: model quality skipped because sidecar JSON is unreadable: {exc}")
            continue
        bbox = _bbox_dict(payload.get("bbox_m"))
        target = _bbox_dict(payload.get("target_envelope_m") or payload.get("target_bbox_m"))
        if bbox is None or target is None:
            warnings.append(f"{module}: model quality skipped because bbox_m or target_envelope_m is missing")
            continue
        axis_reports = _axis_adjustments(bbox, target)
        max_abs_delta = max(abs(report["delta_pct"]) for report in axis_reports.values())
        if max_abs_delta > MODEL_BBOX_FAIL_TOLERANCE_RATIO * 100:
            status = "fail"
        elif max_abs_delta > MODEL_BBOX_PASS_TOLERANCE_RATIO * 100:
            status = "warn"
        else:
            status = "pass"
        adjustments = [report for report in axis_reports.values() if report["action"] != "hold"]
        micro_dimension_warning = _micro_dimension_warning(module, status, max_abs_delta, adjustments)
        if micro_dimension_warning is not None:
            micro_dimension_warnings.append(micro_dimension_warning)
        fidelity_blocker = _fidelity_acceptance_blocker(module, payload, adjustments)
        if fidelity_blocker is not None:
            fidelity_acceptance_blockers.append(fidelity_blocker)
        parts.append(
            {
                "module": module,
                "status": status,
                "runtime_release_allowed": status != "fail",
                "model_delivery_acceptance_status": "blocked"
                if micro_dimension_warning is not None or fidelity_blocker is not None
                else "pass",
                "model_quality_warning_type": "micro_dimension"
                if micro_dimension_warning is not None
                else "fidelity_acceptance_blocker"
                if fidelity_blocker is not None
                else None,
                "bbox_m": {axis: round(float(bbox[axis]), 6) for axis in AXES},
                "target_bbox_m": {axis: round(float(target[axis]), 6) for axis in AXES},
                "max_abs_delta_pct": round(max_abs_delta, 1),
                "axis_reports": axis_reports,
                "size_adjustments": adjustments,
                "position_adjustment": _position_adjustment(module, adjustments, payload),
                "tri_view_focus": _tri_view_focus(module, adjustments),
                "design_directive": _design_directive(module),
                "fidelity_acceptance": fidelity_blocker
                if fidelity_blocker is not None
                else {
                    "status": "not_blocked",
                    "runtime_release_allowed": status != "fail",
                    "model_delivery_acceptance_status": "pass"
                    if micro_dimension_warning is None
                    else "blocked_until_micro_adjusted_or_waived",
                },
            }
        )

    fail_count = sum(1 for part in parts if part["status"] == "fail")
    warning_count = sum(1 for part in parts if part["status"] == "warn")
    model_delivery_blocked = bool(micro_dimension_warnings or fidelity_acceptance_blockers or fail_count)
    return {
        "contract_version": "modeler-exhibition-quality-adjustments.v1",
        "status": "fail" if fail_count else "warn" if warning_count or warnings else "pass",
        "runtime_release_allowed": fail_count == 0,
        "runtime_release_policy": (
            "Web/Quest runtime release may proceed with model-quality warnings; "
            "model delivery/fidelity acceptance remains blocked until listed blockers "
            "and micro-dimension warnings are resolved or explicitly waived."
        ),
        "model_delivery_acceptance_status": "blocked" if model_delivery_blocked else "pass",
        "fidelity_acceptance_blocker_count": len(fidelity_acceptance_blockers),
        "fidelity_acceptance_blockers": fidelity_acceptance_blockers,
        "micro_dimension_warning_count": len(micro_dimension_warnings),
        "micro_dimension_warnings": micro_dimension_warnings,
        "part_count": len(parts),
        "warning_count": warning_count,
        "fail_count": fail_count,
        "pass_tolerance_pct": MODEL_BBOX_PASS_TOLERANCE_RATIO * 100,
        "fail_tolerance_pct": MODEL_BBOX_FAIL_TOLERANCE_RATIO * 100,
        "warnings": warnings,
        "parts": parts,
    }


def _micro_dimension_warning(
    module: str,
    status: str,
    max_abs_delta: float,
    adjustments: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if status != "warn" or not adjustments:
        return None
    return {
        "module": module,
        "warning_type": "micro_dimension",
        "acceptance_bucket": "model_delivery_micro_adjustment",
        "runtime_release_allowed": True,
        "model_delivery_acceptance_status": "blocked_until_micro_adjusted_or_waived",
        "package_gate_status": "warn_runtime_allowed_block_model_delivery",
        "axes": [str(adjustment["axis"]) for adjustment in adjustments],
        "max_abs_delta_pct": round(max_abs_delta, 1),
        "size_adjustments": adjustments,
        "required_action": (
            "Resolve the listed bbox micro-dimension deltas, or attach tri-view waiver evidence, "
            "before model delivery/fidelity acceptance."
        ),
    }


def _fidelity_acceptance_blocker(
    module: str,
    payload: dict[str, Any],
    adjustments: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if module != "waist" or not _waist_requires_body_wrap_loop(payload):
        return None
    export = _body_wrap_loop_export_status(payload)
    if not export["acceptance_blocked"]:
        return None
    return {
        "module": module,
        "blocker_id": "waist_body_wrap_loop_not_exported",
        "warning_type": "fidelity_acceptance_blocker",
        "acceptance_bucket": "p1_fidelity_hold",
        "phase": "P1",
        "runtime_release_allowed": True,
        "model_delivery_acceptance_status": "blocked_until_glb_loop_exported",
        "package_gate_status": "warn_now_block_p1",
        "body_wrap_loop_export_status": export["status"],
        "body_wrap_loop_export_detail": export,
        "related_micro_dimension_axes": [str(adjustment["axis"]) for adjustment in adjustments],
        "distinction": "This is a closed wearable-loop proof blocker, not a simple bbox micro-dimension warning.",
        "required_action": (
            "Export/regenerate the waist GLB with a real body_wrap_loop, declare belt aperture/clearance, "
            "and recheck front/side/back/3Q before model delivery acceptance."
        ),
    }


def _waist_requires_body_wrap_loop(payload: dict[str, Any]) -> bool:
    if str(payload.get("category") or "").strip() == "waist":
        return True
    for key in BODY_WRAP_LOOP_CONTRACT_KEYS:
        if isinstance(payload.get(key), dict):
            return True
    for key in ("body_follow_profile", "suit_silhouette_profile", "visual_density_profile"):
        value = payload.get(key)
        if isinstance(value, dict) and "loop" in json.dumps(value, ensure_ascii=False).lower():
            return True
    for key in ("fit_alignment_notes", "silhouette_review_notes"):
        value = payload.get(key)
        if isinstance(value, list) and "loop" in json.dumps(value, ensure_ascii=False).lower():
            return True
    return False


def _body_wrap_loop_export_status(sidecar: dict[str, Any]) -> dict[str, Any]:
    status = "export_status_not_declared"
    source_fields: dict[str, str] = {}
    metadata_only = False
    exported = False
    containers: list[tuple[str, dict[str, Any]]] = [("sidecar", sidecar)]
    for key in BODY_WRAP_LOOP_CONTRACT_KEYS:
        value = sidecar.get(key)
        if isinstance(value, dict):
            containers.append((key, value))

    for prefix, container in containers:
        for key in BODY_WRAP_LOOP_STATUS_KEYS:
            raw_value = container.get(key)
            raw_status: str | None = None
            if isinstance(raw_value, str):
                raw_status = raw_value
            elif isinstance(raw_value, dict) and isinstance(raw_value.get("status"), str):
                raw_status = raw_value["status"]
            if raw_status is None:
                continue
            normalized = raw_status.strip()
            source_fields[f"{prefix}.{key}"] = normalized
            if normalized in BODY_WRAP_LOOP_EXPORTED_STATUSES:
                exported = True
            if normalized in BODY_WRAP_LOOP_METADATA_ONLY_STATUSES:
                metadata_only = True

    if metadata_only:
        status = "metadata_only_blocked_until_glb_loop_exported"
    elif exported:
        status = "glb_loop_exported"

    return {
        "status": status,
        "phase": "P1",
        "acceptance_blocked": not exported,
        "metadata_only": metadata_only,
        "glb_loop_export_required": True,
        "source_fields": source_fields,
        "required_action": (
            "Export/regenerate the waist GLB from body_wrap_loop and mark the sidecar "
            "as glb_loop_exported before model delivery/fidelity acceptance."
        ),
    }


def _experience_gates(root: Path, model_quality: dict[str, Any]) -> dict[str, Any]:
    gates = [
        _japanese_ui_gate(root),
        _quest_deposition_visual_gate(root),
        _model_fit_artifact_gate(model_quality),
        _tri_view_fidelity_doc_gate(root),
        _p1_limb_baseline_gate(root),
        _local_optional_lane_separation_gate(root),
    ]
    warnings = [
        warning
        for gate in gates
        for warning in gate.get("warnings", [])
    ]
    return {
        "contract_version": "exhibition-experience-readiness-gates.v1",
        "status": "warn" if warnings else "pass",
        "warning_count": len(warnings),
        "warnings": warnings,
        "gates": gates,
    }


def _japanese_ui_gate(root: Path) -> dict[str, Any]:
    files = (
        "viewer/armor-forge/index.html",
        "viewer/armor-forge/forge.js",
        "viewer/quest-iw-demo/index.html",
        "viewer/quest-iw-demo/quest-demo.js",
    )
    present = []
    with_japanese = []
    for rel_path in files:
        path = root / rel_path
        if not path.is_file():
            continue
        present.append(rel_path)
        if JAPANESE_TEXT_RE.search(path.read_text(encoding="utf-8", errors="ignore")):
            with_japanese.append(rel_path)
    warnings = []
    if not with_japanese:
        warnings.append(
            "Japanese UI gate: no Japanese copy detected in viewer public UI files; "
            "package needs Japanese UI proof or a waiver."
        )
    return {
        "gate": "japanese_ui",
        "status": "pass" if with_japanese else "warn",
        "checked_files": present,
        "files_with_japanese_copy": with_japanese,
        "warnings": warnings,
    }


def _quest_deposition_visual_gate(root: Path) -> dict[str, Any]:
    files = (
        "viewer/quest-iw-demo/quest-demo.js",
        "docs/quest-deposition-visual-direction-2026-05-04.md",
    )
    combined = _read_combined_text(root, files)
    required_terms = {
        "蒸着粒子": "deposition particles",
        "蒸着光跡": "deposition light trails",
        "THREE.Points": "point particle renderer",
        "THREE.LineSegments": "line-trail renderer",
        "THREE.AdditiveBlending": "additive glow blending",
        "updateDepositionEffects": "runtime deposition updater",
    }
    missing_terms = [
        label
        for term, label in required_terms.items()
        if term not in combined
    ]
    warnings = []
    if missing_terms:
        warnings.append(
            "Quest deposition visual gate: missing particles/shine evidence for "
            + ", ".join(missing_terms)
            + "."
        )
    return {
        "gate": "quest_deposition_visuals",
        "status": "pass" if not missing_terms else "warn",
        "checked_files": list(files),
        "missing_evidence_terms": missing_terms,
        "warnings": warnings,
    }


def _model_fit_artifact_gate(model_quality: dict[str, Any]) -> dict[str, Any]:
    part_count = int(model_quality.get("part_count") or 0)
    parts = model_quality.get("parts") if isinstance(model_quality.get("parts"), list) else []
    complete_parts = [
        part
        for part in parts
        if isinstance(part.get("position_adjustment"), dict)
        and isinstance(part.get("tri_view_focus"), list)
        and isinstance(part.get("design_directive"), str)
        and isinstance(part.get("axis_reports"), dict)
    ]
    warnings = []
    if part_count != len(EXPECTED_MODULES) or len(complete_parts) != len(EXPECTED_MODULES):
        warnings.append(
            "Model fit artifact gate: per-part micro-adjustment report is incomplete; "
            "save validator --report-json output and resolve missing sidecar target data."
        )
    return {
        "gate": "model_fit_micro_adjustment_artifacts",
        "status": "pass" if not warnings else "warn",
        "expected_part_count": len(EXPECTED_MODULES),
        "reported_part_count": part_count,
        "complete_part_count": len(complete_parts),
        "artifact_hint": "Save tools/validate_exhibition_release_package.py --report-json as qa/model_fit_micro_adjustments.json.",
        "warnings": warnings,
    }


def _tri_view_fidelity_doc_gate(root: Path) -> dict[str, Any]:
    docs = (
        "docs/modeler-exhibition-readiness-risks-2026-05-04.md",
        "docs/modeler-triview-30variant-audit-table-2026-05-03.md",
    )
    combined = _read_combined_text(root, docs)
    required_tokens = {
        "fidelity_hold": "fidelity_hold status separation",
        "front": "front view QA",
        "side": "side view QA",
        "back": "back view QA",
        "3Q": "3Q or three-quarter view QA",
    }
    missing_tokens = [
        label
        for token, label in required_tokens.items()
        if token not in combined
    ]
    warnings = []
    if missing_tokens:
        warnings.append(
            "Tri-view/fidelity_hold doc gate: missing evidence language for "
            + ", ".join(missing_tokens)
            + "."
        )
    return {
        "gate": "tri_view_fidelity_hold_documentation",
        "status": "pass" if not missing_tokens else "warn",
        "checked_docs": list(docs),
        "missing_evidence_terms": missing_tokens,
        "warnings": warnings,
    }


def _p1_limb_baseline_gate(root: Path) -> dict[str, Any]:
    docs = (
        "docs/p1-limb-variant-order-acceptance-2026-05-03.md",
        "docs/modeler-deliveries/p1-limb-three-line-variants-2026-05-03.order-manifest.json",
    )
    combined = _read_combined_text(root, docs)
    required_terms = {
        "24": "24 ordered P1 limb variants",
        "upperarm": "upperarm scope",
        "forearm": "forearm scope",
        "hand": "hand scope",
        "thigh": "thigh scope",
        "line_rescue_knight": "rescue line",
        "line_royal_insect": "royal insect line",
        "line_final_oath": "final oath line",
        "runtime_activation_allowed": "runtime activation remains separate",
    }
    missing_terms = [
        label
        for term, label in required_terms.items()
        if term not in combined
    ]
    warnings = []
    if missing_terms:
        warnings.append(
            "P1 limb baseline gate: missing acceptance/order language for "
            + ", ".join(missing_terms)
            + "."
        )
    return {
        "gate": "p1_limb_order_acceptance_baseline",
        "status": "pass" if not missing_terms else "warn",
        "checked_docs": list(docs),
        "missing_baseline_terms": missing_terms,
        "warnings": warnings,
    }


def _p1_limb_acceptance_summary(root: Path) -> dict[str, Any]:
    validator_path = root / "tools" / "validate_modeler_variant_order_manifest.py"
    manifest_path = root / "docs" / "modeler-deliveries" / "p1-limb-three-line-variants-2026-05-03.order-manifest.json"
    catalog_path = root / "viewer" / "assets" / "armor-parts" / "variant_catalog.json"
    summary: dict[str, Any] = {
        "contract_version": "exhibition-p1-limb-acceptance-summary.v1",
        "manifest": _posix(manifest_path.relative_to(root)) if manifest_path.exists() else _posix(manifest_path),
        "validator": _posix(validator_path.relative_to(root)) if validator_path.exists() else _posix(validator_path),
        "package_gate_status": "warn_now_block_p1",
        "acceptance_complete": False,
        "runtime_activation_allowed": False,
        "runtime_activation_label": "runtime_activation_blocked_by_order_manifest",
        "validator_ok": False,
        "validator_status": "not_run",
        "asset_count": 0,
        "accepted_asset_count": 0,
        "blocked_asset_count": 0,
        "catalog_gap_count": 0,
        "delivery_gap_count": 0,
        "line_system_reports": {},
        "reasons": [],
        "warnings": [],
    }
    if not validator_path.is_file():
        summary["reasons"].append(
            "P1 limb acceptance validator missing: tools/validate_modeler_variant_order_manifest.py"
        )
        return summary
    if not manifest_path.is_file():
        summary["reasons"].append(
            "P1 limb order manifest missing: docs/modeler-deliveries/p1-limb-three-line-variants-2026-05-03.order-manifest.json"
        )
        return summary
    try:
        spec = importlib.util.spec_from_file_location("validate_modeler_variant_order_manifest", validator_path)
        if spec is None or spec.loader is None:
            raise RuntimeError("could not create import spec")
        module = importlib.util.module_from_spec(spec)
        sys.modules["validate_modeler_variant_order_manifest"] = module
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001
        summary["reasons"].append(f"P1 limb acceptance validator unreadable: {exc}")
        return summary

    if not hasattr(module, "validate_order_manifest"):
        summary["reasons"].append("P1 limb acceptance validator missing validate_order_manifest()")
        return summary

    try:
        module.REPO_ROOT = root
        result = module.validate_order_manifest(
            manifest_path,
            catalog_path=catalog_path,
            require_delivered=False,
        )
    except Exception as exc:  # noqa: BLE001
        summary["reasons"].append(f"P1 limb acceptance validator crashed: {exc}")
        return summary

    p1 = result.get("p1_acceptance") if isinstance(result.get("p1_acceptance"), dict) else {}
    package_gate_status = p1.get("package_gate_status")
    if package_gate_status not in {"pass_p1", "warn_now_block_p1"}:
        summary["reasons"].append("P1 limb acceptance validator did not expose a valid package_gate_status")
        package_gate_status = "warn_now_block_p1"
    runtime_allowed = bool(p1.get("runtime_activation_allowed"))
    summary.update(
        {
            "package_gate_status": package_gate_status,
            "acceptance_complete": bool(p1.get("acceptance_complete")),
            "runtime_activation_allowed": runtime_allowed,
            "runtime_activation_label": str(
                p1.get("runtime_activation_label") or "runtime_activation_blocked_by_order_manifest"
            ),
            "validator_ok": bool(result.get("ok")),
            "validator_status": str(result.get("status") or "unknown"),
            "asset_count": int(result.get("asset_count") or 0),
            "accepted_asset_count": int(p1.get("accepted_asset_count") or 0),
            "blocked_asset_count": int(p1.get("blocked_asset_count") or 0),
            "catalog_gap_count": int(result.get("catalog_gap_count") or 0),
            "delivery_gap_count": int(result.get("delivery_gap_count") or 0),
            "line_system_reports": result.get("line_system_reports")
            if isinstance(result.get("line_system_reports"), dict)
            else {},
        }
    )
    validator_reasons = [str(reason) for reason in result.get("reasons", [])]
    validator_warnings = [str(warning) for warning in result.get("warnings", [])]
    if validator_reasons:
        summary["reasons"].extend(f"P1 limb manifest validator: {reason}" for reason in validator_reasons)
    if runtime_allowed:
        summary["reasons"].append(
            "P1 limb acceptance must keep runtime_activation_allowed=false in the release package"
        )
    if package_gate_status == "warn_now_block_p1" and not validator_reasons:
        summary["warnings"].append(
            "P1 limb acceptance incomplete: package_gate_status=warn_now_block_p1; "
            "release remains runnable but P1 limb variants are not accepted for activation."
        )
    summary["warnings"].extend(f"P1 limb manifest validator: {warning}" for warning in validator_warnings)
    return summary


def _local_optional_lane_separation_gate(root: Path) -> dict[str, Any]:
    docs = (
        "docs/exhibition-service-mocopi-roadmap-2026-05-04.md",
        "docs/exhibition-pc-release-package-manifest-2026-05-04.md",
        "docs/exhibition-pc-runbook-2026-05-04.md",
        "docs/exhibition-day-one-page-checklist-2026-05-04.md",
        "docs/web-service-phase0-task-breakdown-2026-05-02.md",
        "docs/quest-mocopi-exhibition-spike-2026-05-04.md",
    )
    combined = _read_combined_text(root, docs)
    package_json = _read_combined_text(root, ("package.json",))
    required_terms = {
        "Required local preflight": "required local preflight section",
        "Optional enhancement preflight": "optional enhancement preflight section",
        "local-pass is prerequisite for visitor operation": "local-pass prerequisite rule",
        "External PC local baseline": "external-PC local baseline schedule",
        "Core demo must run without live GCP, internet, provider secrets, or mocopi.": "offline/local baseline rule",
        "Cloud-only exhibition path before local fallback passes.": "cloud-only path blocked before local pass",
        "PlayCanvas as variant, placement, code, or Replay authority.": "PlayCanvas authority ban",
        "mocopi-GO/DEMO-ONLY/NO-GO/not-included": "mocopi show-floor status labels",
        "service-pass/fail/not-included": "service lane status labels",
        "playcanvas-pass/fail/not-included": "PlayCanvas lane status labels",
        "local-pass/fail": "local lane status labels",
        "local-pass cannot be overridden": "optional lanes cannot override local failure",
        "service endpoint must pass the same forge, recall, replay, and no-local-path checks": "service parity smoke",
        "PlayCanvas must consume an exported runtime package snapshot": "PlayCanvas snapshot-only preflight",
        "mocopi cannot promote the visitor path unless the packaged-PC local baseline remains pass": "mocopi cannot override local pass",
        "fallback confirmed": "mocopi fallback confirmation",
        "`8010`": "fixed Web/API port 8010",
        "`5173`": "fixed Quest port 5173",
        "USB ADB reverse": "USB ADB reverse operator path",
        "Replay portability": "replay portability gate",
    }
    missing_terms = [
        label
        for term, label in required_terms.items()
        if term not in combined
    ]
    script_terms = {
        "serve-dashboard --port 8010": "npm dev starts local Web/API on 8010",
        "dev:quest:adb": "ADB reverse helper script is exposed",
    }
    missing_scripts = [
        label
        for term, label in script_terms.items()
        if term not in package_json
    ]
    warnings = []
    if missing_terms:
        warnings.append(
            "Local/optional lane separation gate: missing docs evidence for "
            + ", ".join(missing_terms)
            + "."
        )
    if missing_scripts:
        warnings.append(
            "Local/optional lane separation gate: missing package script evidence for "
            + ", ".join(missing_scripts)
            + "."
        )
    return {
        "gate": "local_required_optional_enhancement_separation",
        "status": "pass" if not warnings else "warn",
        "required_lane": "external_pc_local",
        "required_operator_labels": ["local-pass", "local-fail"],
        "optional_operator_labels": {
            "gcp_service": ["service-pass", "service-fail", "not-included"],
            "playcanvas": ["playcanvas-pass", "playcanvas-fail", "not-included"],
            "mocopi": ["mocopi-GO", "DEMO-ONLY", "NO-GO", "not-included"],
        },
        "checked_docs": list(docs),
        "missing_evidence_terms": missing_terms,
        "missing_script_terms": missing_scripts,
        "warnings": warnings,
    }


def _read_combined_text(root: Path, rel_paths: Iterable[str]) -> str:
    chunks = []
    for rel_path in rel_paths:
        path = root / rel_path
        if path.is_file():
            chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(chunks)


def _axis_adjustments(bbox: dict[str, float], target: dict[str, float]) -> dict[str, Any]:
    reports: dict[str, Any] = {}
    for axis in AXES:
        actual = float(bbox[axis])
        target_value = float(target[axis])
        delta_pct = ((actual - target_value) / target_value) * 100 if target_value else 0.0
        pass_min = target_value * (1.0 - MODEL_BBOX_PASS_TOLERANCE_RATIO)
        pass_max = target_value * (1.0 + MODEL_BBOX_PASS_TOLERANCE_RATIO)
        if actual < pass_min:
            action = "increase"
            minimum_change = pass_min - actual
        elif actual > pass_max:
            action = "decrease"
            minimum_change = pass_max - actual
        else:
            action = "hold"
            minimum_change = 0.0
        reports[axis] = {
            "axis": axis,
            "action": action,
            "actual_m": round(actual, 6),
            "target_m": round(target_value, 6),
            "delta_pct": round(delta_pct, 1),
            "pass_min_m": round(pass_min, 6),
            "pass_max_m": round(pass_max, 6),
            "minimum_change_to_pass_m": round(minimum_change, 6),
            "symmetric_each_side_m": round(minimum_change / 2.0, 6),
            "view_impact": _axis_view_impact(axis),
        }
    return reports


def _bbox_dict(value: Any) -> dict[str, float] | None:
    if not isinstance(value, dict):
        return None
    if all(isinstance(value.get(axis), (int, float)) for axis in AXES):
        return {axis: float(value[axis]) for axis in AXES}
    size = value.get("size") or value.get("dimensions")
    if isinstance(size, list) and len(size) == 3 and all(isinstance(item, (int, float)) for item in size):
        return {axis: float(size[index]) for index, axis in enumerate(AXES)}
    return None


def _position_adjustment(module: str, adjustments: list[dict[str, Any]], payload: dict[str, Any]) -> dict[str, Any]:
    attachment = payload.get("vrm_attachment") if isinstance(payload.get("vrm_attachment"), dict) else {}
    offset = attachment.get("offset_m")
    offset_target = payload.get("attachment_offset_target_m")
    offset_report: dict[str, Any] = {"action": "hold", "reason": "offset target not declared"}
    if (
        isinstance(offset, list)
        and len(offset) == 3
        and all(isinstance(value, (int, float)) for value in offset)
        and isinstance(offset_target, (int, float))
    ):
        magnitude = sum(float(value) ** 2 for value in offset) ** 0.5
        offset_report = {
            "action": "hold" if magnitude <= float(offset_target) else "reduce_offset",
            "offset_m": [round(float(value), 6) for value in offset],
            "magnitude_m": round(magnitude, 6),
            "target_m": round(float(offset_target), 6),
        }
    if not adjustments:
        return {
            "summary": "No position shift required; preserve current anchor and tri-view silhouette.",
            "attachment_offset": offset_report,
        }
    actions = []
    for adjustment in adjustments:
        axis = adjustment["axis"]
        amount = adjustment["symmetric_each_side_m"]
        if axis == "x":
            actions.append(f"expand local x symmetrically by {amount:+.6f}m per side; keep bone anchor centered")
        elif axis == "y":
            actions.append(f"adjust local y coverage by {amount:+.6f}m at top/bottom; preserve joint escape")
        elif axis == "z":
            actions.append(f"add local z depth by {amount:+.6f}m front/back; verify side and 3Q volume")
    return {
        "summary": f"{module}: " + "; ".join(actions),
        "attachment_offset": offset_report,
    }


def _tri_view_focus(module: str, adjustments: list[dict[str, Any]]) -> list[str]:
    if not adjustments:
        return [
            f"{module}: front/side/back accepted for package gate; keep current silhouette and material-zone read."
        ]
    focus = []
    for adjustment in adjustments:
        focus.append(f"{module}.{adjustment['axis']}: {adjustment['view_impact']}")
    return focus


def _axis_view_impact(axis: str) -> str:
    if axis == "x":
        return "front/back width read; compare left/right silhouette and mirror-pair balance"
    if axis == "y":
        return "front/side vertical coverage; protect neck, elbow, hip, knee, or ankle escape"
    return "side/3Q depth read; avoid flat plate/proxy impression under exhibition lighting"


def _design_directive(module: str) -> str:
    if module == "helmet":
        return "Keep a cool hero face: visor, brow, cheek, and crest must read in front and side, not only texture."
    if module == "chest":
        return "Make the suit read powerful from tri-view: V core, rib returns, and side seams should add depth, not a flat tile."
    if module == "back":
        return "Back view needs a spine keel/rear core that is compact but unmistakably designed."
    if module == "waist":
        return "Treat the belt as a transformation driver loop: buckle, hip plates, and rear clasp should connect chest to legs."
    if "shoulder" in module:
        return "Deltoid cap should look sharp and heroic from front/back while leaving arm lift clearance."
    if "upperarm" in module:
        return "Upperarm should carry stream panels from shoulder to forearm, not read as a thin tube band."
    if "forearm" in module:
        return "Forearm vambrace needs wrist cuff readability and controller-safe side clearance."
    if "hand" in module:
        return "Hand plate should use broad knuckle/palm shapes; avoid tiny details that vanish in Quest."
    if "thigh" in module:
        return "Thigh plate should continue waist-to-shin flow and remain visible in side view without blocking gait."
    if "shin" in module:
        return "Shin should have a strong knee-to-boot stream and ankle cuff so the leg reads grounded."
    if "boot" in module:
        return "Boot needs grounded toe, sole, heel, and ankle mass visible from side/back."
    return "Preserve the cool hero-suit read across front, side, and back."


def _iter_asset_refs(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            if key == "asset_ref" and isinstance(child, str) and child.strip():
                yield child.strip()
            else:
                yield from _iter_asset_refs(child)
    elif isinstance(value, list):
        for child in value:
            yield from _iter_asset_refs(child)


def _require_file(
    root: Path,
    category: str,
    rel_path: str,
    missing: list[dict[str, Any]],
    tracked_candidates: dict[str, set[str]],
) -> None:
    if _unsafe_package_path(rel_path):
        missing.append({"category": category, "path": rel_path, "reason": "path must be repo-relative"})
        return
    path = root / rel_path
    if not path.is_file():
        missing.append({"category": category, "path": _posix(rel_path), "reason": "required file missing"})
        return
    _track_candidate(tracked_candidates, category, _posix(rel_path))


def _match_files(root: Path, pattern: str) -> list[Path]:
    return sorted(path for path in root.glob(pattern) if path.is_file())


def _track_candidate(tracked_candidates: dict[str, set[str]], category: str, rel_path: str) -> None:
    tracked_candidates.setdefault(_posix(rel_path), set()).add(category)


def _is_git_worktree(root: Path) -> bool:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return False
    return proc.returncode == 0 and proc.stdout.strip() == "true"


def _git_tracked_paths(root: Path) -> set[str]:
    proc = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        check=True,
        capture_output=True,
    )
    return {item.decode("utf-8") for item in proc.stdout.split(b"\0") if item}


def _unsafe_package_path(path: str) -> bool:
    raw = Path(path)
    if raw.is_absolute():
        return True
    normalized = raw.as_posix()
    return normalized.startswith("../") or "/../" in normalized or normalized == ".."


def _rel(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root).as_posix()


def _posix(path: str | Path) -> str:
    return Path(str(path)).as_posix()


def _print_text_report(result: dict[str, Any]) -> None:
    print(f"[{result['status'].upper()}] exhibition release package: {result['repo_root']}")
    print(
        "missing="
        f"{result['missing_count']} pattern_gaps={result['pattern_gap_count']} "
        f"untracked={result['untracked_count']} "
        f"model_quality_warn={result['model_quality_warning_count']} "
        f"model_quality_fail={result['model_quality_fail_count']} "
        f"experience_warn={result['experience_warning_count']}"
    )
    for entry in result["missing"]:
        print(f"  missing   {entry['path']} ({entry['category']}): {entry['reason']}")
    for entry in result["pattern_gaps"]:
        print(
            f"  pattern   {entry['pattern']} ({entry['category']}): "
            f"{entry['actual_count']}/{entry['minimum_count']} - {entry['description']}"
        )
    for entry in result["untracked"]:
        print(f"  untracked {entry['path']} ({', '.join(entry['categories'])})")
    if result["git_tracking"].get("allow_untracked_for_local_snapshot") and result["untracked"]:
        print("  snapshot  untracked critical files are allowed by explicit local snapshot mode")
    model_quality = result["model_quality"]
    print(
        "  modelgate "
        f"runtime_release_allowed={str(model_quality.get('runtime_release_allowed')).lower()} "
        f"model_delivery={model_quality.get('model_delivery_acceptance_status')} "
        f"fidelity_blockers={model_quality.get('fidelity_acceptance_blocker_count', 0)} "
        f"micro_warnings={model_quality.get('micro_dimension_warning_count', 0)}"
    )
    for blocker in model_quality.get("fidelity_acceptance_blockers", []):
        print(
            f"  fidelity  block {blocker['module']} {blocker['blocker_id']} "
            f"status={blocker['body_wrap_loop_export_status']} "
            f"runtime_allowed={str(blocker['runtime_release_allowed']).lower()}"
        )
    for part in result["model_quality"]["parts"]:
        if part["status"] == "pass":
            continue
        axes = ",".join(adjustment["axis"] for adjustment in part["size_adjustments"])
        print(
            f"  model     {part['status']} {part['module']} axes={axes} "
            f"max_delta={part['max_abs_delta_pct']}%"
        )
        print(f"            {part['position_adjustment']['summary']}")
    for warning in result["warnings"]:
        print(f"  warn      {warning}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."), help="Release package or repo root to validate")
    parser.add_argument("--report-json", action="store_true", help="Emit structured JSON")
    parser.add_argument(
        "--skip-git-tracking",
        action="store_true",
        help="Only check package existence/counts. Use for release zips without .git.",
    )
    parser.add_argument(
        "--allow-untracked-for-local-snapshot",
        action="store_true",
        help=(
            "Keep the git tracking check and report untracked critical files, but do not fail on them. "
            "Use only for an explicit working-tree snapshot copied/exported to an exhibition PC."
        ),
    )
    parser.add_argument("--expected-variant-glbs", type=int, default=DEFAULT_VARIANT_GLB_COUNT)
    parser.add_argument("--expected-topping-glbs", type=int, default=DEFAULT_TOPPING_GLB_COUNT)
    args = parser.parse_args(argv)
    if args.skip_git_tracking and args.allow_untracked_for_local_snapshot:
        parser.error("--allow-untracked-for-local-snapshot requires git tracking; do not combine with --skip-git-tracking")

    result = validate_release_package(
        args.repo_root,
        check_git_tracking=False if args.skip_git_tracking else None,
        allow_untracked_for_local_snapshot=args.allow_untracked_for_local_snapshot,
        expected_variant_glbs=args.expected_variant_glbs,
        expected_topping_glbs=args.expected_topping_glbs,
    )
    if args.report_json:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        _print_text_report(result)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
