from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "export_model_quality_acceptance_report.py"


def _load_exporter():
    spec = importlib.util.spec_from_file_location("export_model_quality_acceptance_report", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["export_model_quality_acceptance_report"] = module
    spec.loader.exec_module(module)
    return module


exporter = _load_exporter()


def _fake_release_result() -> dict:
    micro_warnings = [
        {"module": "chest", "axes": ["z"], "runtime_release_allowed": True},
        {"module": "waist", "axes": ["x"], "runtime_release_allowed": True},
        {"module": "left_upperarm", "axes": ["x"], "runtime_release_allowed": True},
        {"module": "right_upperarm", "axes": ["x"], "runtime_release_allowed": True},
        {"module": "left_shin", "axes": ["x"], "runtime_release_allowed": True},
        {"module": "right_shin", "axes": ["x"], "runtime_release_allowed": True},
    ]
    fidelity_blockers = [
        {
            "module": "waist",
            "blocker_id": "waist_body_wrap_loop_not_exported",
            "phase": "P1",
            "runtime_release_allowed": True,
            "model_delivery_acceptance_status": "blocked_until_glb_loop_exported",
            "body_wrap_loop_export_status": "export_status_not_declared",
        }
    ]
    return {
        "ok": True,
        "status": "warn",
        "repo_root": "C:/repo",
        "reasons": [],
        "warnings": ["P1 limb acceptance incomplete"],
        "model_quality": {
            "status": "warn",
            "runtime_release_allowed": True,
            "runtime_release_policy": "runtime ok; model delivery blocked",
            "model_delivery_acceptance_status": "blocked",
            "warning_count": 6,
            "fail_count": 0,
            "fidelity_acceptance_blockers": fidelity_blockers,
            "micro_dimension_warnings": micro_warnings,
        },
        "p1_acceptance": {
            "package_gate_status": "warn_now_block_p1",
            "asset_count": 24,
            "accepted_asset_count": 0,
            "blocked_asset_count": 24,
            "catalog_gap_count": 24,
            "delivery_gap_count": 24,
            "runtime_activation_allowed": False,
            "runtime_activation_label": "runtime_activation_blocked_by_order_manifest",
        },
    }


def _fake_p1_result() -> dict:
    return {
        "status": "warn",
        "manifest": "docs/modeler-deliveries/p1-limb-three-line-variants-2026-05-03.order-manifest.json",
        "asset_count": 24,
        "catalog_gap_count": 24,
        "delivery_gap_count": 24,
        "p1_acceptance": {
            "package_gate_status": "warn_now_block_p1",
            "accepted_asset_count": 0,
            "blocked_asset_count": 24,
            "runtime_activation_allowed": False,
            "runtime_activation_label": "runtime_activation_blocked_by_order_manifest",
        },
        "missing_matrix": {
            "entry_count": 24,
            "p1_blocked_asset_count": 24,
            "runtime_activation_blocked_count": 24,
            "stage_counts": {
                "current_stop": {"delivery": 24},
                "delivery": {"missing_count": 24},
                "catalog_registration": {"missing_count": 24},
            },
            "by_line": {
                "line_rescue_knight": {
                    "line_label": "rescue",
                    "asset_count": 8,
                    "p1_blocked_asset_count": 8,
                    "runtime_activation_blocked_count": 8,
                }
            },
        },
        "warnings": ["catalog: 24 ordered variant(s) not yet declared"],
        "reasons": [],
    }


def test_build_report_keeps_runtime_allowed_and_delivery_blocked_separate() -> None:
    report = exporter.build_model_quality_acceptance_report(
        _fake_release_result(),
        p1_result=_fake_p1_result(),
        repo_root="C:/repo",
    )

    assert report["contract_version"] == "model-quality-acceptance-report.v1"
    assert report["runtime_release_allowed"] is True
    assert report["model_delivery_acceptance_status"] == "blocked"
    assert len(report["micro_dimension_warnings"]) == 6
    assert report["fidelity_acceptance_blockers"][0]["blocker_id"] == "waist_body_wrap_loop_not_exported"
    p1_summary = report["p1_missing_matrix_summary"]
    assert p1_summary["blocked_asset_count"] == 24
    assert p1_summary["catalog_gap_count"] == 24
    assert p1_summary["delivery_gap_count"] == 24
    assert p1_summary["current_stop_counts"] == {"delivery": 24}
    action_scopes = {action["scope"] for action in report["recommended_next_actions"]}
    assert "model_fidelity" in action_scopes
    assert "model_delivery_micro_adjustments" in action_scopes
    assert "p1_limb_variants" in action_scopes
    assert "release_handoff" in action_scopes


def test_cli_writes_out_and_report_json(monkeypatch, tmp_path: Path, capsys) -> None:
    expected_report = exporter.build_model_quality_acceptance_report(
        _fake_release_result(),
        p1_result=_fake_p1_result(),
        repo_root=tmp_path,
    )
    monkeypatch.setattr(
        exporter,
        "export_acceptance_report",
        lambda *args, **kwargs: expected_report,
    )

    rc = exporter.main(
        [
            "--repo-root",
            str(tmp_path),
            "--out",
            "qa/model-quality-acceptance-latest.json",
            "--report-json",
            "--no-color",
        ]
    )
    captured = capsys.readouterr()
    out_path = tmp_path / "qa" / "model-quality-acceptance-latest.json"

    assert rc == 0
    assert out_path.is_file()
    assert json.loads(out_path.read_text(encoding="utf-8")) == expected_report
    assert json.loads(captured.out) == expected_report
