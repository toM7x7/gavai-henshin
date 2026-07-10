from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "export_mocopi_rehearsal_plan.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("export_mocopi_rehearsal_plan", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["export_mocopi_rehearsal_plan"] = module
    spec.loader.exec_module(module)
    return module


tool = _load_tool()


def _evaluation(label: str = "mocopi-DEMO-ONLY", *, candidate_token: str = "MOCOPI 12f") -> dict:
    candidate_usable = candidate_token.startswith("MOCOPI") and "0f" not in candidate_token
    status = "fail" if label == "mocopi-NO-GO" else "warn" if label == "mocopi-DEMO-ONLY" else "pass"
    return {
        "contract_version": "mocopi-evidence-pack-evaluator.v1",
        "ok": label != "mocopi-NO-GO",
        "status": status,
        "label": label,
        "expected_code": "3601",
        "automatic_pack_gate_pass": label != "mocopi-NO-GO",
        "mocopi_candidate_usable": candidate_usable,
        "packs": {
            "body_baseline": _pack("body", "BODY 12f", "body"),
            "mocopi_candidate": _pack("mocopi", candidate_token, "mocopi" if candidate_usable else "body"),
            "fallback_recovery": _pack("fallback", "STATIC", "static"),
        },
        "go_blockers": [
            "physical mocopi pairing/calibration evidence is not represented in the snapshot pack yet",
            "median/p95 latency and freeze/drop thresholds are not represented in the snapshot pack yet",
        ],
        "reasons": [] if label != "mocopi-NO-GO" else ["mocopi_candidate: MOCOPI candidate does not show usable MOCOPI motion token: BODY 12f"],
        "warnings": ["GO blocker: median/p95 latency and freeze/drop thresholds are not represented in the snapshot pack yet"],
    }


def _pack(name: str, token: str, category: str) -> dict:
    return {
        "role": name,
        "path": f"qa/logs/quest-3601-{name}",
        "status": "pass",
        "motion": {
            "token": token,
            "category": category,
            "usable_mocopi": category == "mocopi",
            "usable_body_or_static": category in {"body", "static"},
        },
        "centerline": {"present": True, "verdict": "pass", "classification": "pass"},
        "adb": {
            "device_authorized": True,
            "reverse_5173": True,
            "reverse_8010": True,
        },
        "reasons": [],
        "warnings": [],
    }


def _write_pack(root: Path, name: str, *, token: str, motion_source: str) -> Path:
    pack = root / name
    pack.mkdir()
    pack.joinpath("operator-summary.txt").write_text(
        "\n".join(
            [
                f"snapshotDir: {pack.as_posix()}",
                "code: 3601",
                "qaCenterlineExpected: True",
                "apiUrl: http://127.0.0.1:8010/api/quest-debug/latest",
                "href: http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=3601&qa=centerline",
                "userAgent: Mozilla/5.0 Quest Browser",
                "telemetryCode: 3601",
                "xrSession: True",
                "uxState: playing",
                "centerlineVerdict: pass",
                "centerlineClassification: pass",
                "centerlineDisplayLine: QA pass",
                "apiError: ",
            ]
        ),
        encoding="utf-8",
    )
    pack.joinpath("quest-debug-latest.json").write_text(
        json.dumps(
            {
                "ok": True,
                "record": {
                    "payload": {
                        "query": {
                            "href": "http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=3601&qa=centerline",
                            "code": "3601",
                            "userAgent": "Mozilla/5.0 Quest Browser",
                            "qa": "centerline",
                        },
                        "uxState": "playing",
                        "xr": {"session": True},
                        "replayMotionDiagnostic": {
                            "token": token,
                            "motion_source": motion_source,
                            "source": motion_source,
                            "body_sim_frames": 12 if "MOCOPI" in token or "BODY" in token else 0,
                            "live_pose_frames": 0,
                        },
                        "centerlineQa": {
                            "verdict": "pass",
                            "classification": "pass",
                            "displayLine": "QA pass",
                        },
                    }
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    pack.joinpath("adb-devices.txt").write_text("List of devices attached\n1WMHH000000000\tdevice\n", encoding="utf-8")
    pack.joinpath("adb-reverse.txt").write_text(
        "1WMHH000000000 tcp:5173 tcp:5173\n1WMHH000000000 tcp:8010 tcp:8010\n",
        encoding="utf-8",
    )
    return pack


def test_plan_contains_required_show_floor_sections() -> None:
    plan = tool.export_mocopi_rehearsal_plan(_evaluation())

    assert plan["contract_version"] == "mocopi-rehearsal-plan.v1"
    assert plan["current_gate_label"] == "mocopi-DEMO-ONLY"
    for key in (
        "target_environment",
        "lane_policy",
        "external_pc_stage_table",
        "quest_mocopi_connection_stage_table",
        "web_service_anshin_lane",
        "mocopi_go_promotion_conditions",
        "rehearsal_steps",
        "operator_script",
        "risk_register",
        "fallback_trigger_points",
        "evidence_to_collect",
        "current_gate_label",
    ):
        assert key in plan
    assert any(step["phase"] == "BODY baseline" for step in plan["rehearsal_steps"])
    assert any("BODY fallback" in line["line"] for line in plan["operator_script"])
    assert plan["target_environment"]["pc"]["os"] == "Windows"
    assert "unknown" in plan["target_environment"]["pc"]["gpu"]
    assert plan["target_environment"]["quest"]["preferred_transport"] == "USB ADB reverse"
    assert plan["lane_policy"]["required_baseline"]["label"] == "local-pass/fail"
    assert plan["web_service_anshin_lane"]["label"] == "service-pass/fail/not-included"
    assert any(stage["stage"] == "5" and "fresh" in " ".join(stage["actions"]) and "code" in " ".join(stage["actions"]) for stage in plan["external_pc_stage_table"])
    assert any(stage["stage"] == "Q2" and "six sensors" in " ".join(stage["actions"]) for stage in plan["quest_mocopi_connection_stage_table"])
    assert any("latency" in risk["trigger"] for risk in plan["risk_register"])
    assert any(item["id"] == "evidence-manual-go-blockers" for item in plan["evidence_to_collect"])
    assert "Only mocopi-GO" in plan["mocopi_go_promotion_conditions"]["public_route_rule"]


def test_no_go_plan_starts_with_public_mocopi_stop_condition() -> None:
    plan = tool.export_mocopi_rehearsal_plan(_evaluation("mocopi-NO-GO", candidate_token="BODY 12f"))

    assert plan["status"] == "fallback_only"
    assert plan["rehearsal_steps"][0]["id"] == "no-go-00"
    assert any(trigger["max_recovery_sec"] == 0 for trigger in plan["fallback_trigger_points"])
    assert any(risk["severity"] == "critical" for risk in plan["risk_register"])
    assert any("BODY/static" in stage["fallback"] for stage in plan["external_pc_stage_table"])


def test_plan_defines_mocopi_go_as_promotion_not_default() -> None:
    evaluation = _evaluation("mocopi-GO")
    evaluation["go_blockers"] = []
    evaluation["warnings"] = []
    plan = tool.export_mocopi_rehearsal_plan(evaluation)

    assert plan["status"] == "ready_with_fallback"
    assert any("local-pass" in item for item in plan["mocopi_go_promotion_conditions"]["conditions"])
    assert any("fallback recovery" in item for item in plan["mocopi_go_promotion_conditions"]["conditions"])
    assert plan["quest_mocopi_connection_stage_table"][-1]["fallback"].startswith("When in doubt")


def test_cli_reads_evaluation_json_writes_out_and_prints_report(tmp_path: Path) -> None:
    evaluation_path = tmp_path / "evaluation.json"
    out_path = tmp_path / "mocopi-rehearsal-plan.json"
    evaluation_path.write_text(json.dumps(_evaluation(), ensure_ascii=False), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--evaluation-json",
            str(evaluation_path),
            "--out",
            str(out_path),
            "--report-json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    stdout_plan = json.loads(completed.stdout)
    file_plan = json.loads(out_path.read_text(encoding="utf-8"))

    assert stdout_plan["current_gate_label"] == "mocopi-DEMO-ONLY"
    assert file_plan["current_gate_label"] == stdout_plan["current_gate_label"]
    assert file_plan["operator_script"]


def test_cli_accepts_three_evidence_packs_and_calls_evaluator(tmp_path: Path) -> None:
    body = _write_pack(tmp_path, "body", token="BODY 12f", motion_source="body_sim")
    mocopi = _write_pack(tmp_path, "mocopi", token="MOCOPI 12f", motion_source="mocopi")
    fallback = _write_pack(tmp_path, "fallback", token="STATIC", motion_source="static_fallback")
    out_path = tmp_path / "plan.json"

    completed = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--body-baseline",
            str(body),
            "--mocopi-candidate",
            str(mocopi),
            "--fallback-recovery",
            str(fallback),
            "--out",
            str(out_path),
            "--report-json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    plan = json.loads(completed.stdout)

    assert plan["current_gate_label"] == "mocopi-DEMO-ONLY"
    assert plan["source_evaluation"]["mocopi_candidate_usable"] is True
    assert out_path.exists()
