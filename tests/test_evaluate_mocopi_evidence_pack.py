from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "evaluate_mocopi_evidence_pack.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("evaluate_mocopi_evidence_pack", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["evaluate_mocopi_evidence_pack"] = module
    spec.loader.exec_module(module)
    return module


tool = _load_tool()


def _write_pack(
    root: Path,
    name: str,
    *,
    token: str,
    motion_source: str,
    centerline_verdict: str = "pass",
    centerline_classification: str = "pass",
    code: str = "3601",
    user_agent: str = "Mozilla/5.0 Quest Browser",
) -> Path:
    pack = root / name
    pack.mkdir()
    pack.joinpath("operator-summary.txt").write_text(
        "\n".join(
            [
                f"snapshotDir: {pack.as_posix()}",
                f"code: {code}",
                "qaCenterlineExpected: True",
                "apiUrl: http://127.0.0.1:8010/api/quest-debug/latest",
                f"href: http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code={code}&qa=centerline",
                f"userAgent: {user_agent}",
                f"telemetryCode: {code}",
                "xrSession: True",
                "uxState: playing",
                f"centerlineVerdict: {centerline_verdict}",
                f"centerlineClassification: {centerline_classification}",
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
                            "href": f"http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code={code}&qa=centerline",
                            "code": code,
                            "userAgent": user_agent,
                            "qa": "centerline",
                        },
                        "uxState": "playing",
                        "xr": {"session": True},
                        "replayMotionDiagnostic": {
                            "token": token,
                            "motion_source": motion_source,
                            "source": motion_source,
                            "body_sim_frames": 12 if "BODY" in token or "MOCOPI" in token else 0,
                            "live_pose_frames": 0,
                        },
                        "centerlineQa": {
                            "verdict": centerline_verdict,
                            "classification": centerline_classification,
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


def test_three_expected_packs_evaluate_as_demo_only_until_manual_go_gates(tmp_path: Path) -> None:
    body = _write_pack(tmp_path, "body", token="BODY 12f", motion_source="body_sim")
    mocopi = _write_pack(tmp_path, "mocopi", token="MOCOPI 12f", motion_source="mocopi")
    fallback = _write_pack(tmp_path, "fallback", token="STATIC", motion_source="static_fallback")

    result = tool.evaluate_mocopi_evidence_packs(
        body_baseline=body,
        mocopi_candidate=mocopi,
        fallback_recovery=fallback,
    )

    assert result["status"] == "warn"
    assert result["label"] == "mocopi-DEMO-ONLY"
    assert result["automatic_pack_gate_pass"] is True
    assert result["mocopi_candidate_usable"] is True
    assert result["packs"]["body_baseline"]["status"] == "pass"
    assert result["packs"]["mocopi_candidate"]["motion"]["category"] == "mocopi"
    assert result["packs"]["fallback_recovery"]["motion"]["usable_body_or_static"] is True
    assert any("latency" in blocker for blocker in result["go_blockers"])


def test_candidate_without_usable_mocopi_token_is_no_go(tmp_path: Path) -> None:
    body = _write_pack(tmp_path, "body", token="BODY 12f", motion_source="body_sim")
    mocopi = _write_pack(tmp_path, "mocopi", token="BODY 12f", motion_source="body_sim")
    fallback = _write_pack(tmp_path, "fallback", token="STATIC", motion_source="static_fallback")

    result = tool.evaluate_mocopi_evidence_packs(
        body_baseline=body,
        mocopi_candidate=mocopi,
        fallback_recovery=fallback,
    )

    assert result["status"] == "fail"
    assert result["label"] == "mocopi-NO-GO"
    assert result["packs"]["mocopi_candidate"]["status"] == "fail"
    assert any("does not show usable MOCOPI" in reason for reason in result["reasons"])


def test_mocopi_zero_frame_token_is_no_go(tmp_path: Path) -> None:
    body = _write_pack(tmp_path, "body", token="BODY 12f", motion_source="body_sim")
    mocopi = _write_pack(tmp_path, "mocopi", token="MOCOPI 0f", motion_source="mocopi")
    fallback = _write_pack(tmp_path, "fallback", token="BODY 12f", motion_source="body_sim")

    result = tool.evaluate_mocopi_evidence_packs(
        body_baseline=body,
        mocopi_candidate=mocopi,
        fallback_recovery=fallback,
    )

    assert result["label"] == "mocopi-NO-GO"
    assert result["packs"]["mocopi_candidate"]["motion"]["frame_count"] == 0


def test_powershell_bom_summary_and_payload_unwrap_are_supported(tmp_path: Path) -> None:
    body = _write_pack(tmp_path, "body", token="BODY 12f", motion_source="body_sim")
    body.joinpath("operator-summary.txt").write_text(
        body.joinpath("operator-summary.txt").read_text(encoding="utf-8"),
        encoding="utf-8-sig",
    )
    mocopi = _write_pack(tmp_path, "mocopi", token="MOCOPI+LIVE", motion_source="mocopi")
    fallback = _write_pack(tmp_path, "fallback", token="STATIC", motion_source="static_fallback")

    result = tool.evaluate_mocopi_evidence_packs(
        body_baseline=body,
        mocopi_candidate=mocopi,
        fallback_recovery=fallback,
    )

    assert result["packs"]["body_baseline"]["summary"]["telemetryCode"] == "3601"
    assert result["packs"]["mocopi_candidate"]["motion"]["token"] == "MOCOPI+LIVE"
    assert result["automatic_pack_gate_pass"] is True


def test_cli_emits_json_report(tmp_path: Path) -> None:
    body = _write_pack(tmp_path, "body", token="BODY 12f", motion_source="body_sim")
    mocopi = _write_pack(tmp_path, "mocopi", token="MOCOPI 12f", motion_source="mocopi")
    fallback = _write_pack(tmp_path, "fallback", token="BODY 12f", motion_source="body_sim")

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
            "--report-json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)

    assert result["label"] == "mocopi-DEMO-ONLY"
    assert result["packs"]["mocopi_candidate"]["motion"]["usable_mocopi"] is True
