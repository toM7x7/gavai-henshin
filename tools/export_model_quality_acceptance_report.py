"""Export one machine-readable model-quality acceptance report.

This report keeps Web/Quest runtime release, model delivery acceptance, and P1
variant acceptance visible in one JSON file. It is intentionally read-only: it
reuses existing validators and does not run Blender or regenerate GLBs.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


CONTRACT_VERSION = "model-quality-acceptance-report.v1"
DEFAULT_OUT = Path("qa/model-quality-acceptance-latest.json")


def export_acceptance_report(
    repo_root: str | Path = ".",
    *,
    check_git_tracking: bool | None = None,
    allow_untracked_for_local_snapshot: bool = False,
    expected_variant_glbs: int | None = None,
    expected_topping_glbs: int | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    release_result = _collect_release_package(
        root,
        check_git_tracking=check_git_tracking,
        allow_untracked_for_local_snapshot=allow_untracked_for_local_snapshot,
        expected_variant_glbs=expected_variant_glbs,
        expected_topping_glbs=expected_topping_glbs,
    )
    p1_result = _collect_p1_manifest(root)
    return build_model_quality_acceptance_report(release_result, p1_result=p1_result, repo_root=root)


def build_model_quality_acceptance_report(
    release_result: dict[str, Any],
    *,
    p1_result: dict[str, Any] | None = None,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    model_quality = _dict(release_result.get("model_quality"))
    p1_acceptance = _dict(release_result.get("p1_acceptance"))
    fidelity_blockers = _list(model_quality.get("fidelity_acceptance_blockers"))
    micro_warnings = _list(model_quality.get("micro_dimension_warnings"))
    fail_count = _int(model_quality.get("fail_count"))
    runtime_release_allowed = bool(model_quality.get("runtime_release_allowed", fail_count == 0))
    model_delivery_acceptance_status = str(
        model_quality.get("model_delivery_acceptance_status")
        or ("blocked" if fail_count or fidelity_blockers or micro_warnings else "pass")
    )
    p1_summary = _p1_missing_matrix_summary(p1_acceptance, p1_result)
    report = {
        "contract_version": CONTRACT_VERSION,
        "repo_root": Path(repo_root).resolve().as_posix() if repo_root is not None else release_result.get("repo_root"),
        "source_validators": {
            "release_package": "tools/validate_exhibition_release_package.py",
            "p1_variant_order_manifest": "tools/validate_modeler_variant_order_manifest.py",
            "armor_part": "tools/validate_armor_part.py",
        },
        "release_package_status": release_result.get("status"),
        "release_package_ok": bool(release_result.get("ok")),
        "runtime_release_allowed": runtime_release_allowed,
        "runtime_release_policy": model_quality.get(
            "runtime_release_policy",
            "Runtime release is separate from model delivery/fidelity acceptance.",
        ),
        "model_delivery_acceptance_status": model_delivery_acceptance_status,
        "model_quality_status": model_quality.get("status"),
        "model_quality_warning_count": _int(model_quality.get("warning_count")),
        "model_quality_fail_count": fail_count,
        "fidelity_acceptance_blockers": fidelity_blockers,
        "micro_dimension_warnings": micro_warnings,
        "p1_missing_matrix_summary": p1_summary,
        "recommended_next_actions": [],
        "release_reasons": _list(release_result.get("reasons")),
        "release_warnings": _list(release_result.get("warnings")),
    }
    report["recommended_next_actions"] = _recommended_next_actions(report)
    return report


def _collect_release_package(
    root: Path,
    *,
    check_git_tracking: bool | None,
    allow_untracked_for_local_snapshot: bool,
    expected_variant_glbs: int | None,
    expected_topping_glbs: int | None,
) -> dict[str, Any]:
    module = _load_tool_module(root, "validate_exhibition_release_package")
    kwargs: dict[str, Any] = {
        "check_git_tracking": check_git_tracking,
        "allow_untracked_for_local_snapshot": allow_untracked_for_local_snapshot,
    }
    if expected_variant_glbs is not None:
        kwargs["expected_variant_glbs"] = expected_variant_glbs
    if expected_topping_glbs is not None:
        kwargs["expected_topping_glbs"] = expected_topping_glbs
    return module.validate_release_package(root, **kwargs)


def _collect_p1_manifest(root: Path) -> dict[str, Any]:
    module = _load_tool_module(root, "validate_modeler_variant_order_manifest")
    module.REPO_ROOT = root
    return module.validate_order_manifest(
        module.DEFAULT_MANIFEST,
        catalog_path=module.DEFAULT_CATALOG,
        require_delivered=False,
    )


def _load_tool_module(root: Path, name: str) -> Any:
    path = root / "tools" / f"{name}.py"
    if not path.is_file():
        raise FileNotFoundError(f"required validator missing: {path.as_posix()}")
    module_name = f"_model_quality_acceptance_{name}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load validator module: {path.as_posix()}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _p1_missing_matrix_summary(
    release_p1: dict[str, Any],
    p1_result: dict[str, Any] | None,
) -> dict[str, Any]:
    if p1_result is None:
        return {
            "contract_version": "p1-missing-matrix-summary.v1",
            "source": "release_package_summary",
            "status": release_p1.get("package_gate_status", "unknown"),
            "asset_count": _int(release_p1.get("asset_count")),
            "accepted_asset_count": _int(release_p1.get("accepted_asset_count")),
            "blocked_asset_count": _int(release_p1.get("blocked_asset_count")),
            "catalog_gap_count": _int(release_p1.get("catalog_gap_count")),
            "delivery_gap_count": _int(release_p1.get("delivery_gap_count")),
            "runtime_activation_allowed": bool(release_p1.get("runtime_activation_allowed")),
            "runtime_activation_label": release_p1.get("runtime_activation_label"),
            "stage_counts": {},
            "by_line": {},
        }

    p1_acceptance = _dict(p1_result.get("p1_acceptance"))
    missing_matrix = _dict(p1_result.get("missing_matrix"))
    stage_counts = _dict(missing_matrix.get("stage_counts"))
    return {
        "contract_version": "p1-missing-matrix-summary.v1",
        "source": "validate_modeler_variant_order_manifest",
        "status": p1_acceptance.get("package_gate_status", p1_result.get("status", "unknown")),
        "manifest": p1_result.get("manifest"),
        "asset_count": _int(p1_result.get("asset_count")),
        "accepted_asset_count": _int(p1_acceptance.get("accepted_asset_count")),
        "blocked_asset_count": _int(p1_acceptance.get("blocked_asset_count")),
        "catalog_gap_count": _int(p1_result.get("catalog_gap_count")),
        "delivery_gap_count": _int(p1_result.get("delivery_gap_count")),
        "runtime_activation_allowed": bool(p1_acceptance.get("runtime_activation_allowed")),
        "runtime_activation_label": p1_acceptance.get("runtime_activation_label"),
        "entry_count": _int(missing_matrix.get("entry_count")),
        "p1_blocked_asset_count": _int(missing_matrix.get("p1_blocked_asset_count")),
        "runtime_activation_blocked_count": _int(missing_matrix.get("runtime_activation_blocked_count")),
        "stage_counts": stage_counts,
        "current_stop_counts": _dict(stage_counts.get("current_stop")),
        "by_line": _compact_by_line(_dict(missing_matrix.get("by_line"))),
        "warnings": _list(p1_result.get("warnings")),
        "reasons": _list(p1_result.get("reasons")),
    }


def _compact_by_line(by_line: dict[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for line_id, value in by_line.items():
        line = _dict(value)
        compact[str(line_id)] = {
            "line_label": line.get("line_label"),
            "asset_count": _int(line.get("asset_count")),
            "p1_blocked_asset_count": _int(line.get("p1_blocked_asset_count")),
            "runtime_activation_blocked_count": _int(line.get("runtime_activation_blocked_count")),
        }
    return compact


def _recommended_next_actions(report: dict[str, Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    if not report["runtime_release_allowed"]:
        actions.append(
            {
                "priority": "P0",
                "scope": "runtime_release",
                "action": "Resolve model-quality fail entries before Web/Quest runtime release.",
                "source": "model_quality.fail_count",
            }
        )
    if report["fidelity_acceptance_blockers"]:
        modules = sorted({str(item.get("module")) for item in report["fidelity_acceptance_blockers"]})
        actions.append(
            {
                "priority": "P1",
                "scope": "model_fidelity",
                "modules": modules,
                "action": (
                    "Export/regenerate blocked GLB fidelity assets, starting with waist body_wrap_loop; "
                    "declare aperture/clearance and recheck front/side/back/3Q."
                ),
                "source": "fidelity_acceptance_blockers",
            }
        )
    if report["micro_dimension_warnings"]:
        modules = sorted({str(item.get("module")) for item in report["micro_dimension_warnings"]})
        actions.append(
            {
                "priority": "P0",
                "scope": "model_delivery_micro_adjustments",
                "modules": modules,
                "action": (
                    "Apply bbox micro-dimension fixes or attach tri-view waiver evidence; keep left/right "
                    "pair edits mirrored."
                ),
                "source": "micro_dimension_warnings",
            }
        )
    p1_summary = _dict(report.get("p1_missing_matrix_summary"))
    if _int(p1_summary.get("blocked_asset_count")) or _int(p1_summary.get("p1_blocked_asset_count")):
        actions.append(
            {
                "priority": "P1",
                "scope": "p1_limb_variants",
                "action": (
                    "Close the P1 missing matrix: deliver/register missing upperarm/forearm/hand/thigh "
                    "variants while keeping runtime activation blocked until accepted."
                ),
                "source": "p1_missing_matrix_summary",
            }
        )
    if report["runtime_release_allowed"] and report["model_delivery_acceptance_status"] != "pass":
        actions.append(
            {
                "priority": "P0",
                "scope": "release_handoff",
                "action": (
                    "Runtime may proceed with warnings, but do not mark model delivery accepted; ship this "
                    "JSON beside the release package."
                ),
                "source": "runtime_release_allowed",
            }
        )
    return actions


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return 0


def _print_text_report(report: dict[str, Any]) -> None:
    print("[MODEL-QUALITY-ACCEPTANCE]")
    print(f"runtime_release_allowed={str(report['runtime_release_allowed']).lower()}")
    print(f"model_delivery_acceptance_status={report['model_delivery_acceptance_status']}")
    print(f"fidelity_acceptance_blockers={len(report['fidelity_acceptance_blockers'])}")
    print(f"micro_dimension_warnings={len(report['micro_dimension_warnings'])}")
    p1_summary = _dict(report.get("p1_missing_matrix_summary"))
    print(
        "p1_missing_matrix="
        f"blocked={p1_summary.get('blocked_asset_count', 0)} "
        f"catalog_gaps={p1_summary.get('catalog_gap_count', 0)} "
        f"delivery_gaps={p1_summary.get('delivery_gap_count', 0)}"
    )
    for action in report["recommended_next_actions"]:
        print(f"  next {action['priority']} {action['scope']}: {action['action']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."), help="Repo or package root")
    parser.add_argument("--out", type=Path, default=None, help=f"Write JSON report, e.g. {DEFAULT_OUT}")
    parser.add_argument("--report-json", action="store_true", help="Emit structured JSON to stdout")
    parser.add_argument("--no-color", action="store_true", help="Accepted for CI parity; output is never colorized")
    parser.add_argument("--skip-git-tracking", action="store_true", help="Skip git tracking checks in package validator")
    parser.add_argument(
        "--allow-untracked-for-local-snapshot",
        action="store_true",
        help="Pass through local snapshot allowance to package validator",
    )
    parser.add_argument("--expected-variant-glbs", type=int, default=None)
    parser.add_argument("--expected-topping-glbs", type=int, default=None)
    args = parser.parse_args(argv)
    if args.skip_git_tracking and args.allow_untracked_for_local_snapshot:
        parser.error("--allow-untracked-for-local-snapshot requires git tracking; do not combine with --skip-git-tracking")

    report = export_acceptance_report(
        args.repo_root,
        check_git_tracking=False if args.skip_git_tracking else None,
        allow_untracked_for_local_snapshot=args.allow_untracked_for_local_snapshot,
        expected_variant_glbs=args.expected_variant_glbs,
        expected_topping_glbs=args.expected_topping_glbs,
    )
    if args.out is not None:
        out_path = args.out if args.out.is_absolute() else args.repo_root / args.out
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.report_json:
        json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    elif args.out is None:
        _print_text_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
