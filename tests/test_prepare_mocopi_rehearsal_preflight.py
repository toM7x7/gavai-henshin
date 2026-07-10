from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "prepare_mocopi_rehearsal_preflight.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("prepare_mocopi_rehearsal_preflight", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["prepare_mocopi_rehearsal_preflight"] = module
    spec.loader.exec_module(module)
    return module


tool = _load_tool()


def test_static_preflight_is_demo_only_when_runtime_is_skipped() -> None:
    report = tool.prepare_mocopi_rehearsal_preflight(repo_root=REPO_ROOT, skip_runtime=True)

    assert report["contract_version"] == "mocopi-rehearsal-preflight.v1"
    assert report["current_gate_label"] == "mocopi-DEMO-ONLY"
    assert report["static_checks"]["ok"] is True
    assert report["ready_to_start_physical_rehearsal"] is True
    assert report["ready_for_public_mocopi"] is False
    assert any("Capture BODY baseline" in action for action in report["operator_next_actions"])
    assert "mocopi-GO" in report["go_demo_no_go_rules"]


def test_missing_repo_reception_points_are_no_go(tmp_path: Path) -> None:
    report = tool.prepare_mocopi_rehearsal_preflight(repo_root=tmp_path, skip_runtime=True)

    assert report["current_gate_label"] == "mocopi-NO-GO"
    assert report["ready_to_start_physical_rehearsal"] is False
    assert report["missing_reception_points"]
    assert any("missing required file" in item for item in report["blocking_items"])


def test_go_requires_go_evaluation_when_static_and_runtime_are_ready(tmp_path: Path) -> None:
    evaluation_path = tmp_path / "evaluation.json"
    evaluation_path.write_text(
        json.dumps(
            {
                "label": "mocopi-GO",
                "status": "pass",
                "automatic_pack_gate_pass": True,
                "mocopi_candidate_usable": True,
                "go_blockers": [],
                "reasons": [],
                "warnings": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    report = tool.prepare_mocopi_rehearsal_preflight(
        repo_root=REPO_ROOT,
        evaluation_json=evaluation_path,
        skip_runtime=True,
    )

    assert report["current_gate_label"] == "mocopi-GO"
    assert report["ready_for_public_mocopi"] is True
    assert report["source_evaluation"]["present"] is True
    assert report["source_evaluation"]["label"] == "mocopi-GO"


def test_quest_motion_diagnostic_accepts_route_and_top_level_shapes() -> None:
    assert tool._quest_motion_diagnostic({"replayMotion": {"token": "MOCOPI 7f"}})["token"] == "MOCOPI 7f"
    assert (
        tool._quest_motion_diagnostic({"route": {"replayMotionDiagnostic": {"token": "BODY 12f"}}})["token"]
        == "BODY 12f"
    )
    assert (
        tool._quest_motion_diagnostic(
            {
                "replayMotion": {"token": "MOCOPI 7f"},
                "route": {"replayMotionDiagnostic": {"token": "BODY 12f"}},
            }
        )["token"]
        == "MOCOPI 7f"
    )
    assert tool._quest_motion_diagnostic({"route": {}}) == {}


def test_quest_debug_api_summary_reads_motion_token_from_latest_shapes() -> None:
    top_level = tool._quest_debug_api_summary(
        {
            "query": {"code": "3601", "userAgent": "Mozilla/5.0 Quest Browser"},
            "uxState": "browser_archive_replay_mirror_active",
            "xr": {"session": True},
            "replayMotion": {"token": "MOCOPI 7f"},
        }
    )
    route_only = tool._quest_debug_api_summary(
        {
            "record": {
                "payload": {
                    "query": {"code": "3601", "userAgent": "Mozilla/5.0 Quest Browser"},
                    "route": {"replayMotionDiagnostic": {"token": "BODY 12f"}},
                }
            }
        }
    )
    both = tool._quest_debug_api_summary(
        {
            "record": {
                "payload": {
                    "query": {"code": "3601", "userAgent": "Mozilla/5.0 Quest Browser"},
                    "replayMotion": {"token": "MOCOPI 7f"},
                    "route": {"replayMotionDiagnostic": {"token": "BODY 12f"}},
                }
            }
        }
    )

    assert top_level["motion_token"] == "MOCOPI 7f"
    assert route_only["motion_token"] == "BODY 12f"
    assert both["motion_token"] == "MOCOPI 7f"


def test_cli_writes_report_json_with_runtime_skipped(tmp_path: Path) -> None:
    out_path = tmp_path / "preflight.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--repo-root",
            str(REPO_ROOT),
            "--skip-runtime",
            "--out",
            str(out_path),
            "--report-json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    stdout_report = json.loads(completed.stdout)
    file_report = json.loads(out_path.read_text(encoding="utf-8"))

    assert stdout_report["current_gate_label"] == "mocopi-DEMO-ONLY"
    assert file_report["codex_next_commands"]
    assert out_path.exists()
