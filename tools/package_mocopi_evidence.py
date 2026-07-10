"""Package mocopi exhibition evidence into a share-safe JSON manifest.

The package manifest is intended for GitHub or external-PC handoff. It keeps
raw Quest telemetry, ADB logs, screenshots, and other potentially identifying
or large files local by default, while sharing the minimal gate summary needed
to understand the current BODY/mocopi/fallback decision.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


CONTRACT_VERSION = "mocopi-evidence-share-package.v1"
DEFAULT_OUT = Path("qa/mocopi-evidence-package-latest.json")
PACK_ROLES = ("body_baseline", "mocopi_candidate", "fallback_recovery")
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}
RAW_LOCAL_FILES = {
    "operator-summary.txt": "may include local URL, user agent, code, and operator environment details",
    "quest-debug-latest.json": "raw Quest telemetry may include local paths, runtime state, and participant/venue context",
    "adb-devices.txt": "ADB output may include headset serial/device identifiers",
    "adb-reverse.txt": "ADB reverse output may expose local transport details",
}
RAW_LOG_SUFFIXES = {".log", ".trace", ".har"}
DEFAULT_MAX_SHARE_BYTES = 64 * 1024


def package_mocopi_evidence(
    *,
    evaluation_report: dict[str, Any],
    rehearsal_plan: dict[str, Any],
    evaluation_path: str | Path | None = None,
    rehearsal_plan_path: str | Path | None = None,
    evidence_dirs: list[str | Path] | None = None,
    output_path: str | Path = DEFAULT_OUT,
) -> dict[str, Any]:
    label = _first_non_empty(
        rehearsal_plan.get("current_gate_label"),
        evaluation_report.get("label"),
        "mocopi-NO-GO",
    )
    evidence_dir_summaries, local_files = _evidence_dir_summaries(evidence_dirs or [])
    files_to_keep_local = []
    files_to_keep_local.extend(_input_files_to_keep_local(evaluation_path, rehearsal_plan_path))
    files_to_keep_local.extend(local_files)

    out_path = Path(output_path)
    return {
        "contract_version": CONTRACT_VERSION,
        "current_gate_label": label,
        "operator_ready_status": _operator_ready_status(label),
        "fallback_required": True,
        "included_evidence": {
            "evaluation_report": _evaluation_summary(evaluation_report, evaluation_path),
            "rehearsal_plan": _plan_summary(rehearsal_plan, rehearsal_plan_path),
            "evidence_dirs": evidence_dir_summaries,
        },
        "redaction_policy": _redaction_policy(),
        "privacy_notes": _privacy_notes(),
        "files_to_share": [
            {
                "path": out_path.as_posix(),
                "kind": "sanitized_manifest",
                "share_by_default": True,
                "reason": "contains only gate summaries, sanitized evidence refs, and sharing policy",
            }
        ],
        "files_to_keep_local": files_to_keep_local,
    }


def load_json(path: str | Path) -> dict[str, Any]:
    loaded = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return loaded


def _evaluation_summary(evaluation: dict[str, Any], path: str | Path | None) -> dict[str, Any]:
    packs = evaluation.get("packs") if isinstance(evaluation.get("packs"), dict) else {}
    return {
        "source_path": _path_ref(path),
        "contract_version": evaluation.get("contract_version", ""),
        "status": evaluation.get("status", ""),
        "label": evaluation.get("label", ""),
        "expected_code": evaluation.get("expected_code", ""),
        "automatic_pack_gate_pass": bool(evaluation.get("automatic_pack_gate_pass")),
        "mocopi_candidate_usable": bool(evaluation.get("mocopi_candidate_usable")),
        "pack_summaries": {
            role: _pack_summary(packs.get(role) if isinstance(packs.get(role), dict) else {})
            for role in PACK_ROLES
        },
        "reason_count": len(evaluation.get("reasons") if isinstance(evaluation.get("reasons"), list) else []),
        "warning_count": len(evaluation.get("warnings") if isinstance(evaluation.get("warnings"), list) else []),
        "go_blocker_count": len(evaluation.get("go_blockers") if isinstance(evaluation.get("go_blockers"), list) else []),
    }


def _pack_summary(pack: dict[str, Any]) -> dict[str, Any]:
    motion = pack.get("motion") if isinstance(pack.get("motion"), dict) else {}
    centerline = pack.get("centerline") if isinstance(pack.get("centerline"), dict) else {}
    adb = pack.get("adb") if isinstance(pack.get("adb"), dict) else {}
    return {
        "path_ref": _path_ref(pack.get("path", "")),
        "status": pack.get("status", ""),
        "motion": {
            "token": motion.get("token", ""),
            "category": motion.get("category", ""),
            "frame_count": motion.get("frame_count"),
            "usable_mocopi": bool(motion.get("usable_mocopi")),
            "usable_body_or_static": bool(motion.get("usable_body_or_static")),
        },
        "centerline": {
            "present": bool(centerline.get("present")),
            "verdict": centerline.get("verdict", ""),
            "classification": centerline.get("classification", ""),
        },
        "adb": {
            "device_authorized": bool(adb.get("device_authorized")),
            "reverse_5173": bool(adb.get("reverse_5173")),
            "reverse_8010": bool(adb.get("reverse_8010")),
        },
    }


def _plan_summary(plan: dict[str, Any], path: str | Path | None) -> dict[str, Any]:
    return {
        "source_path": _path_ref(path),
        "contract_version": plan.get("contract_version", ""),
        "status": plan.get("status", ""),
        "current_gate_label": plan.get("current_gate_label", ""),
        "rehearsal_step_count": _list_count(plan.get("rehearsal_steps")),
        "operator_script_count": _list_count(plan.get("operator_script")),
        "risk_count": _list_count(plan.get("risk_register")),
        "fallback_trigger_count": _list_count(plan.get("fallback_trigger_points")),
        "evidence_to_collect_count": _list_count(plan.get("evidence_to_collect")),
    }


def _evidence_dir_summaries(evidence_dirs: list[str | Path]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    summaries: list[dict[str, Any]] = []
    keep_local: list[dict[str, Any]] = []
    for evidence_dir in evidence_dirs:
        root = Path(evidence_dir)
        files = [path for path in root.rglob("*") if path.is_file()] if root.exists() else []
        classified = [_classify_evidence_file(path, root) for path in files]
        keep_local.extend(
            {
                "path": item["path"],
                "kind": item["kind"],
                "reason": item["reason"],
                "size_bytes": item["size_bytes"],
                "share_by_default": False,
            }
            for item in classified
        )
        summaries.append(
            {
                "path_ref": _path_ref(root),
                "exists": root.exists(),
                "file_count": len(files),
                "total_bytes": sum(item["size_bytes"] for item in classified),
                "local_only_file_count": len(classified),
                "image_or_screenshot_count": sum(1 for item in classified if item["kind"] == "image_or_screenshot"),
                "raw_debug_file_count": sum(1 for item in classified if item["kind"] == "raw_debug"),
                "large_file_count": sum(1 for item in classified if item["kind"] == "large_file"),
            }
        )
    return summaries, keep_local


def _classify_evidence_file(path: Path, root: Path) -> dict[str, Any]:
    rel = _relative_path(path, root)
    suffix = path.suffix.lower()
    name = path.name
    size = path.stat().st_size
    if suffix in IMAGE_SUFFIXES or "screencap" in name.lower() or "screenshot" in name.lower():
        kind = "image_or_screenshot"
        reason = "screenshots/images can expose participants, venue, browser state, or generated visuals"
    elif name in RAW_LOCAL_FILES:
        kind = "raw_debug"
        reason = RAW_LOCAL_FILES[name]
    elif size > DEFAULT_MAX_SHARE_BYTES:
        kind = "large_file"
        reason = f"file is larger than the default share budget of {DEFAULT_MAX_SHARE_BYTES} bytes"
    elif suffix in RAW_LOG_SUFFIXES:
        kind = "raw_log"
        reason = "raw logs may expose local environment, identifiers, or excessive detail"
    else:
        kind = "evidence_raw_file"
        reason = "raw evidence files stay local by default; share the sanitized package manifest instead"
    return {
        "path": rel,
        "kind": kind,
        "reason": reason,
        "size_bytes": size,
    }


def _input_files_to_keep_local(
    evaluation_path: str | Path | None,
    rehearsal_plan_path: str | Path | None,
) -> list[dict[str, Any]]:
    files: list[dict[str, Any]] = []
    if evaluation_path:
        files.append(
            {
                "path": Path(evaluation_path).as_posix(),
                "kind": "source_evaluation_json",
                "reason": "may contain raw href, user agent, local evidence paths, and detailed warnings",
                "share_by_default": False,
            }
        )
    if rehearsal_plan_path:
        files.append(
            {
                "path": Path(rehearsal_plan_path).as_posix(),
                "kind": "source_rehearsal_plan_json",
                "reason": "may contain local evidence refs; the package manifest carries the sanitized summary",
                "share_by_default": False,
            }
        )
    return files


def _redaction_policy() -> dict[str, Any]:
    return {
        "default": "share sanitized manifest only",
        "excluded_by_default": [
            "screencap.png and other screenshots/images",
            "quest-debug-latest.json raw Quest telemetry",
            "operator-summary.txt raw operator snapshot",
            "adb-devices.txt and adb-reverse.txt raw ADB logs",
            "raw mocopi sensor streams, phone exports, and participant motion captures",
            "large logs or files over the default share budget",
        ],
        "fields_removed_or_summarized": [
            "full href and query strings",
            "user agent strings",
            "device serials",
            "local absolute paths and usernames",
            "raw centerline mesh records and part positions",
            "screenshots or generated visual evidence",
        ],
        "allowed_summary_fields": [
            "current gate label",
            "pack status",
            "motion token/category/frame count",
            "centerline verdict/classification",
            "ADB boolean readiness",
            "file counts and local-only classification",
        ],
    }


def _privacy_notes() -> list[str]:
    return [
        "Raw mocopi motion can be identifying biometric-style motion data; keep raw captures local unless consent and retention are explicit.",
        "Quest screenshots can reveal participants, venue layout, browser tabs, generated visuals, or operator state; do not share them by default.",
        "ADB device logs may contain headset serials or transport details; share only boolean readiness in the manifest.",
        "The 4-character recall code is not a durable identity or secret, but package recipients should not treat it as proof that raw data is safe to publish.",
        "For GitHub sharing, commit the sanitized package manifest, not qa/logs raw snapshot folders.",
    ]


def _operator_ready_status(label: str) -> str:
    if label == "mocopi-GO":
        return "shareable_go_summary_body_fallback_still_required"
    if label == "mocopi-DEMO-ONLY":
        return "shareable_demo_only_summary_body_fallback_required"
    if label == "mocopi-NO-GO":
        return "shareable_no_go_summary_body_fallback_only"
    return "review_required_unknown_gate_label"


def _path_ref(path: Any) -> str:
    if not path:
        return ""
    normalized = str(path).replace("\\", "/").rstrip("/")
    return normalized.split("/")[-1]


def _relative_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def _first_non_empty(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _list_count(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _print_text_report(manifest: dict[str, Any]) -> None:
    print(f"{manifest['current_gate_label']} ({manifest['operator_ready_status']})")
    print(f"fallback_required: {manifest['fallback_required']}")
    print("files_to_share:")
    for item in manifest["files_to_share"]:
        print(f"- {item['path']} ({item['kind']})")
    print("files_to_keep_local:")
    for item in manifest["files_to_keep_local"]:
        print(f"- {item['path']} ({item['kind']})")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluation-json", required=True, type=Path, help="Path to evaluator report JSON")
    parser.add_argument("--rehearsal-plan", required=True, type=Path, help="Path to rehearsal plan JSON")
    parser.add_argument(
        "--evidence-dir",
        action="append",
        default=[],
        type=Path,
        help="Optional qa/logs evidence directory. May be provided multiple times.",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"Write package manifest, default: {DEFAULT_OUT}")
    parser.add_argument("--report-json", action="store_true", help="Emit package manifest JSON to stdout")
    args = parser.parse_args(argv)

    evaluation = load_json(args.evaluation_json)
    rehearsal_plan = load_json(args.rehearsal_plan)
    manifest = package_mocopi_evidence(
        evaluation_report=evaluation,
        rehearsal_plan=rehearsal_plan,
        evaluation_path=args.evaluation_json,
        rehearsal_plan_path=args.rehearsal_plan,
        evidence_dirs=args.evidence_dir,
        output_path=args.out,
    )
    _write_json(args.out, manifest)
    if args.report_json:
        json.dump(manifest, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        _print_text_report(manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
