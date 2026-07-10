from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "package_mocopi_evidence.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("package_mocopi_evidence", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["package_mocopi_evidence"] = module
    spec.loader.exec_module(module)
    return module


tool = _load_tool()


def _evaluation(label: str = "mocopi-DEMO-ONLY") -> dict:
    return {
        "contract_version": "mocopi-evidence-pack-evaluator.v1",
        "status": "warn" if label == "mocopi-DEMO-ONLY" else "fail" if label == "mocopi-NO-GO" else "pass",
        "label": label,
        "expected_code": "3601",
        "automatic_pack_gate_pass": label != "mocopi-NO-GO",
        "mocopi_candidate_usable": label != "mocopi-NO-GO",
        "packs": {
            "body_baseline": _pack("qa/logs/quest-3601-body", "BODY 12f", "body", usable_body=True),
            "mocopi_candidate": _pack(
                "qa/logs/quest-3601-mocopi",
                "MOCOPI 12f" if label != "mocopi-NO-GO" else "BODY 12f",
                "mocopi" if label != "mocopi-NO-GO" else "body",
                usable_mocopi=label != "mocopi-NO-GO",
            ),
            "fallback_recovery": _pack("qa/logs/quest-3601-fallback", "STATIC", "static", usable_body=True),
        },
        "reasons": [] if label != "mocopi-NO-GO" else ["mocopi_candidate failed"],
        "warnings": ["GO blocker: latency evidence missing"],
        "go_blockers": ["latency evidence missing"],
    }


def _pack(path: str, token: str, category: str, *, usable_mocopi: bool = False, usable_body: bool = False) -> dict:
    return {
        "path": path,
        "status": "pass",
        "motion": {
            "token": token,
            "category": category,
            "frame_count": 12 if token != "STATIC" else None,
            "usable_mocopi": usable_mocopi,
            "usable_body_or_static": usable_body,
        },
        "centerline": {"present": True, "verdict": "pass", "classification": "pass"},
        "adb": {"device_authorized": True, "reverse_5173": True, "reverse_8010": True},
    }


def _plan(label: str = "mocopi-DEMO-ONLY") -> dict:
    return {
        "contract_version": "mocopi-rehearsal-plan.v1",
        "current_gate_label": label,
        "status": "operator_rehearsal_only",
        "rehearsal_steps": [{"id": "baseline-01"}],
        "operator_script": [{"moment": "fallback", "line": "BODY fallback"}],
        "risk_register": [{"id": "risk-local-baseline"}],
        "fallback_trigger_points": [{"trigger": "MOCOPI 0f"}],
        "evidence_to_collect": [{"id": "evidence-body-baseline"}],
    }


def _write_evidence_dir(root: Path) -> Path:
    evidence = root / "quest-3601-demo"
    evidence.mkdir()
    evidence.joinpath("operator-summary.txt").write_text("href: http://localhost:5173/?code=3601\n", encoding="utf-8")
    evidence.joinpath("quest-debug-latest.json").write_text('{"record":{"payload":{"query":{"code":"3601"}}}}', encoding="utf-8")
    evidence.joinpath("adb-devices.txt").write_text("1WMHH000000000\tdevice\n", encoding="utf-8")
    evidence.joinpath("adb-reverse.txt").write_text("tcp:5173 tcp:5173\n", encoding="utf-8")
    evidence.joinpath("screencap.png").write_bytes(b"\x89PNG\r\n")
    evidence.joinpath("large.log").write_text("x" * 70000, encoding="utf-8")
    return evidence


def test_manifest_contains_required_keys_and_sanitized_summary(tmp_path: Path) -> None:
    evidence_dir = _write_evidence_dir(tmp_path)

    manifest = tool.package_mocopi_evidence(
        evaluation_report=_evaluation(),
        rehearsal_plan=_plan(),
        evaluation_path=tmp_path / "evaluation.json",
        rehearsal_plan_path=tmp_path / "plan.json",
        evidence_dirs=[evidence_dir],
        output_path=tmp_path / "package.json",
    )

    for key in (
        "included_evidence",
        "redaction_policy",
        "privacy_notes",
        "operator_ready_status",
        "fallback_required",
        "files_to_share",
        "files_to_keep_local",
    ):
        assert key in manifest
    assert manifest["current_gate_label"] == "mocopi-DEMO-ONLY"
    assert manifest["fallback_required"] is True
    assert manifest["operator_ready_status"] == "shareable_demo_only_summary_body_fallback_required"
    assert manifest["included_evidence"]["evaluation_report"]["pack_summaries"]["mocopi_candidate"]["motion"]["token"] == "MOCOPI 12f"
    assert manifest["included_evidence"]["evaluation_report"]["pack_summaries"]["mocopi_candidate"]["path_ref"] == "quest-3601-mocopi"


def test_raw_logs_screenshots_and_source_json_stay_local_by_default(tmp_path: Path) -> None:
    evidence_dir = _write_evidence_dir(tmp_path)
    manifest = tool.package_mocopi_evidence(
        evaluation_report=_evaluation(),
        rehearsal_plan=_plan(),
        evaluation_path=tmp_path / "evaluation.json",
        rehearsal_plan_path=tmp_path / "plan.json",
        evidence_dirs=[evidence_dir],
        output_path=tmp_path / "package.json",
    )

    share_paths = {item["path"] for item in manifest["files_to_share"]}
    local_paths = {item["path"] for item in manifest["files_to_keep_local"]}

    assert (tmp_path / "package.json").as_posix() in share_paths
    assert "screencap.png" in local_paths
    assert "quest-debug-latest.json" in local_paths
    assert "adb-devices.txt" in local_paths
    assert "large.log" in local_paths
    assert all("screencap" not in path for path in share_paths)
    assert all(item["share_by_default"] is False for item in manifest["files_to_keep_local"])


def test_no_go_manifest_is_body_fallback_only() -> None:
    manifest = tool.package_mocopi_evidence(
        evaluation_report=_evaluation("mocopi-NO-GO"),
        rehearsal_plan=_plan("mocopi-NO-GO"),
        output_path="qa/mocopi-evidence-package-latest.json",
    )

    assert manifest["current_gate_label"] == "mocopi-NO-GO"
    assert manifest["operator_ready_status"] == "shareable_no_go_summary_body_fallback_only"
    assert manifest["fallback_required"] is True
    assert manifest["included_evidence"]["evaluation_report"]["mocopi_candidate_usable"] is False


def test_cli_writes_manifest_and_reports_json(tmp_path: Path) -> None:
    evaluation_path = tmp_path / "evaluation.json"
    plan_path = tmp_path / "plan.json"
    out_path = tmp_path / "mocopi-evidence-package.json"
    evidence_dir = _write_evidence_dir(tmp_path)
    evaluation_path.write_text(json.dumps(_evaluation(), ensure_ascii=False), encoding="utf-8")
    plan_path.write_text(json.dumps(_plan(), ensure_ascii=False), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--evaluation-json",
            str(evaluation_path),
            "--rehearsal-plan",
            str(plan_path),
            "--evidence-dir",
            str(evidence_dir),
            "--out",
            str(out_path),
            "--report-json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    stdout_manifest = json.loads(completed.stdout)
    file_manifest = json.loads(out_path.read_text(encoding="utf-8"))

    assert stdout_manifest["contract_version"] == "mocopi-evidence-share-package.v1"
    assert file_manifest["files_to_share"][0]["path"] == out_path.as_posix()
    assert file_manifest["included_evidence"]["evidence_dirs"][0]["image_or_screenshot_count"] == 1
    assert file_manifest["included_evidence"]["evidence_dirs"][0]["large_file_count"] == 1
