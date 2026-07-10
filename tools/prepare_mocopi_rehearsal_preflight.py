"""Prepare a local mocopi rehearsal preflight report.

This tool is intentionally conservative. It checks whether the local repo,
current PC, Quest transport, diagnostic endpoint, evidence workflow, and manual
operator gates are ready before starting a physical mocopi rehearsal.
"""

from __future__ import annotations

import argparse
import json
import shutil
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


CONTRACT_VERSION = "mocopi-rehearsal-preflight.v1"
DEFAULT_OUT = Path("qa/mocopi-rehearsal-preflight-latest.json")
REQUIRED_FILES = [
    "tools/probe_mocopi_udp.py",
    "tools/evaluate_mocopi_evidence_pack.py",
    "tools/export_mocopi_rehearsal_plan.py",
    "tools/package_mocopi_evidence.py",
    "tools/capture_quest_debug_snapshot.ps1",
    "viewer/quest-iw-demo/quest-demo.js",
    "tests/test_quest_mocopi_motion_source.py",
    "docs/quest-mocopi-exhibition-spike-2026-05-04.md",
    "docs/exhibition-mocopi-external-pc-stage-plan-2026-05-05.md",
]
VIEWER_TOKENS = [
    "REPLAY_MOTION_SOURCE_MOCOPI",
    "MOCOPI",
    "BODY",
    "STATIC",
    "replayMotionSourceFromRecord",
    "makeReplayMotionDiagnostic",
    "body-sim replay unavailable; falling back to replay motion/static",
    "/api/quest-debug",
    "centerlineQa",
]
DOC_TOKENS = [
    "Quest + mocopi Connection Stage Table",
    "BODY/static fallback",
    "mocopi-GO",
    "mocopi-DEMO-ONLY",
    "mocopi-NO-GO",
    "capture_quest_debug_snapshot.ps1",
]


def prepare_mocopi_rehearsal_preflight(
    *,
    repo_root: str | Path = ".",
    code: str = "3601",
    api_url: str = "http://127.0.0.1:8010/api/quest-debug/latest",
    evaluation_json: str | Path | None = None,
    skip_runtime: bool = False,
    timeout_sec: float = 1.5,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    static_checks = _static_checks(root)
    command_checks = _command_checks(skip_runtime)
    port_checks = _port_checks(skip_runtime, timeout_sec=timeout_sec)
    adb_checks = _adb_checks(skip_runtime)
    api_check = _api_check(api_url, skip_runtime, timeout_sec=timeout_sec)
    evaluation = _load_evaluation(evaluation_json) if evaluation_json else None

    blockers = _collect_blockers(static_checks, command_checks, port_checks, adb_checks, api_check)
    warnings = _collect_warnings(command_checks, api_check, evaluation)
    label = _decision_label(blockers, evaluation)

    return {
        "contract_version": CONTRACT_VERSION,
        "code": code,
        "api_url": api_url,
        "current_gate_label": label,
        "ready_to_start_physical_rehearsal": label in {"mocopi-DEMO-ONLY", "mocopi-GO"},
        "ready_for_public_mocopi": label == "mocopi-GO",
        "static_checks": static_checks,
        "command_checks": command_checks,
        "port_checks": port_checks,
        "adb_checks": adb_checks,
        "quest_debug_api": api_check,
        "source_evaluation": _evaluation_summary(evaluation),
        "missing_reception_points": _missing_reception_points(static_checks),
        "blocking_items": blockers,
        "warnings": warnings,
        "operator_next_actions": _operator_next_actions(label, code, blockers, evaluation),
        "codex_next_commands": _codex_next_commands(code, evaluation_json),
        "fallback_procedure": _fallback_procedure(code),
        "go_demo_no_go_rules": _go_demo_no_go_rules(),
    }


def _static_checks(root: Path) -> dict[str, Any]:
    missing_files = [path for path in REQUIRED_FILES if not (root / path).exists()]
    viewer_text = _read_text(root / "viewer/quest-iw-demo/quest-demo.js")
    docs_text = "\n".join(
        _read_text(root / path)
        for path in (
            "docs/quest-mocopi-exhibition-spike-2026-05-04.md",
            "docs/exhibition-mocopi-external-pc-stage-plan-2026-05-05.md",
        )
    )
    missing_viewer_tokens = [token for token in VIEWER_TOKENS if token not in viewer_text]
    missing_doc_tokens = [token for token in DOC_TOKENS if token not in docs_text]
    return {
        "ok": not missing_files and not missing_viewer_tokens and not missing_doc_tokens,
        "missing_files": missing_files,
        "viewer_tokens_ok": not missing_viewer_tokens,
        "missing_viewer_tokens": missing_viewer_tokens,
        "doc_tokens_ok": not missing_doc_tokens,
        "missing_doc_tokens": missing_doc_tokens,
        "known_reception_points": [
            "probe_mocopi_udp.py confirms phone-to-PC UDP reachability without storing raw motion payloads",
            "Quest archive/replay diagnostic can display MOCOPI/BODY/STATIC",
            "capture_quest_debug_snapshot.ps1 records ADB, Quest debug API, centerline, and optional screencap",
            "evaluate_mocopi_evidence_pack.py judges BODY baseline, MOCOPI candidate, and fallback recovery packs",
            "export_mocopi_rehearsal_plan.py turns evaluation into stage/fallback plan",
        ],
    }


def _command_checks(skip_runtime: bool) -> dict[str, Any]:
    if skip_runtime:
        return {"skipped": True, "commands": {}}
    commands = {
        name: {"present": shutil.which(name) is not None}
        for name in ("python", "node", "npm", "adb")
    }
    return {"skipped": False, "commands": commands, "ok": all(item["present"] for item in commands.values())}


def _port_checks(skip_runtime: bool, *, timeout_sec: float) -> dict[str, Any]:
    if skip_runtime:
        return {"skipped": True, "ports": {}}
    ports = {
        "8010": _tcp_connects("127.0.0.1", 8010, timeout_sec),
        "5173": _tcp_connects("127.0.0.1", 5173, timeout_sec),
    }
    return {"skipped": False, "ports": ports, "ok": all(ports.values())}


def _adb_checks(skip_runtime: bool) -> dict[str, Any]:
    if skip_runtime:
        return {"skipped": True}
    adb = shutil.which("adb")
    if not adb:
        return {
            "skipped": False,
            "adb_present": False,
            "device_authorized": False,
            "reverse_5173": False,
            "reverse_8010": False,
            "raw_devices": "",
            "raw_reverse": "",
        }
    devices = _run_command([adb, "devices", "-l"])
    reverse = _run_command([adb, "reverse", "--list"])
    devices_text = devices["stdout"] + devices["stderr"]
    reverse_text = reverse["stdout"] + reverse["stderr"]
    device_lines = [line for line in devices_text.splitlines() if "\tdevice" in line or " device " in f" {line} "]
    unauthorized = "unauthorized" in devices_text.lower()
    return {
        "skipped": False,
        "adb_present": True,
        "device_authorized": bool(device_lines) and not unauthorized,
        "unauthorized": unauthorized,
        "reverse_5173": "tcp:5173" in reverse_text,
        "reverse_8010": "tcp:8010" in reverse_text,
        "raw_devices": devices_text.strip(),
        "raw_reverse": reverse_text.strip(),
    }


def _api_check(api_url: str, skip_runtime: bool, *, timeout_sec: float) -> dict[str, Any]:
    if skip_runtime:
        return {"skipped": True, "ok": False}
    try:
        with urllib.request.urlopen(api_url, timeout=timeout_sec) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except (OSError, urllib.error.URLError) as exc:
        return {"skipped": False, "ok": False, "error": str(exc)}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {"skipped": False, "ok": False, "error": "Quest debug API did not return JSON"}
    return _quest_debug_api_summary(payload)


def _quest_debug_api_summary(payload: dict[str, Any]) -> dict[str, Any]:
    record_payload = _quest_debug_record_payload(payload)
    query = record_payload.get("query", {}) if isinstance(record_payload.get("query"), dict) else {}
    diagnostic = _quest_motion_diagnostic(record_payload, fallback_payload=payload)
    centerline = record_payload.get("centerlineQa", {})
    return {
        "skipped": False,
        "ok": True,
        "telemetry_code": str(query.get("code") or ""),
        "user_agent_is_quest": "Quest" in str(query.get("userAgent") or ""),
        "ux_state": str(record_payload.get("uxState") or ""),
        "xr_session": bool(record_payload.get("xr", {}).get("session")) if isinstance(record_payload.get("xr"), dict) else False,
        "motion_token": str(diagnostic.get("token") or "") if isinstance(diagnostic, dict) else "",
        "centerline_verdict": str(centerline.get("verdict") or "") if isinstance(centerline, dict) else "",
        "centerline_classification": str(centerline.get("classification") or "") if isinstance(centerline, dict) else "",
    }


def _quest_debug_record_payload(payload: dict[str, Any]) -> dict[str, Any]:
    record = payload.get("record")
    if isinstance(record, dict) and isinstance(record.get("payload"), dict):
        return record["payload"]
    if isinstance(payload.get("payload"), dict):
        return payload["payload"]
    return payload


def _quest_motion_diagnostic(
    record_payload: dict[str, Any],
    *,
    fallback_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    for key in ("replayMotionDiagnostic", "replayMotion"):
        value = record_payload.get(key)
        if isinstance(value, dict):
            return value
    route = record_payload.get("route")
    if isinstance(route, dict):
        value = route.get("replayMotionDiagnostic")
        if isinstance(value, dict):
            return value
    if fallback_payload and fallback_payload is not record_payload:
        return _quest_motion_diagnostic(fallback_payload)
    return {}


def _load_evaluation(path: str | Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    loaded = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    return loaded if isinstance(loaded, dict) else None


def _evaluation_summary(evaluation: dict[str, Any] | None) -> dict[str, Any]:
    if not evaluation:
        return {"present": False}
    return {
        "present": True,
        "label": evaluation.get("label", ""),
        "status": evaluation.get("status", ""),
        "automatic_pack_gate_pass": bool(evaluation.get("automatic_pack_gate_pass")),
        "mocopi_candidate_usable": bool(evaluation.get("mocopi_candidate_usable")),
        "go_blockers": evaluation.get("go_blockers", []),
        "reasons": evaluation.get("reasons", []),
        "warnings": evaluation.get("warnings", []),
    }


def _collect_blockers(
    static_checks: dict[str, Any],
    command_checks: dict[str, Any],
    port_checks: dict[str, Any],
    adb_checks: dict[str, Any],
    api_check: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    for path in static_checks["missing_files"]:
        blockers.append(f"missing required file: {path}")
    for token in static_checks["missing_viewer_tokens"]:
        blockers.append(f"Quest viewer missing diagnostic token: {token}")
    for token in static_checks["missing_doc_tokens"]:
        blockers.append(f"mocopi docs missing procedure token: {token}")
    if not command_checks.get("skipped"):
        for name, item in command_checks.get("commands", {}).items():
            if not item["present"]:
                blockers.append(f"command not found on PATH: {name}")
    if not port_checks.get("skipped"):
        ports = port_checks.get("ports", {})
        if not ports.get("8010"):
            blockers.append("Web/API port 8010 is not listening on 127.0.0.1")
        if not ports.get("5173"):
            blockers.append("Quest Vite port 5173 is not listening on 127.0.0.1")
    if not adb_checks.get("skipped"):
        if not adb_checks.get("adb_present"):
            blockers.append("adb is not available; Quest USB evidence cannot be captured")
        elif not adb_checks.get("device_authorized"):
            blockers.append("adb devices does not show an authorized Quest device")
        elif not (adb_checks.get("reverse_5173") and adb_checks.get("reverse_8010")):
            blockers.append("adb reverse does not include both tcp:5173 and tcp:8010")
    if not api_check.get("skipped") and not api_check.get("ok"):
        blockers.append("Quest debug API is not reachable at the configured api_url")
    return blockers


def _collect_warnings(
    command_checks: dict[str, Any],
    api_check: dict[str, Any],
    evaluation: dict[str, Any] | None,
) -> list[str]:
    warnings: list[str] = []
    if command_checks.get("skipped"):
        warnings.append("Runtime checks were skipped; this report only validates static readiness.")
    if api_check.get("ok"):
        if not api_check.get("user_agent_is_quest"):
            warnings.append("Quest debug API is reachable, but the latest user agent is not Quest.")
        if not api_check.get("motion_token"):
            warnings.append("Quest debug API has no replayMotionDiagnostic token yet.")
    if not evaluation:
        warnings.append("No evaluation JSON supplied; physical mocopi evidence packs are not evaluated yet.")
    elif evaluation.get("label") != "mocopi-GO":
        warnings.extend(str(item) for item in evaluation.get("go_blockers", []) or [])
    return warnings


def _decision_label(blockers: list[str], evaluation: dict[str, Any] | None) -> str:
    if blockers:
        return "mocopi-NO-GO"
    if evaluation and evaluation.get("label") == "mocopi-GO":
        return "mocopi-GO"
    return "mocopi-DEMO-ONLY"


def _missing_reception_points(static_checks: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if static_checks["missing_files"]:
        missing.append("required local tool/doc/viewer files")
    if static_checks["missing_viewer_tokens"]:
        missing.append("Quest-side MOCOPI/BODY/STATIC diagnostics or fallback code")
    if static_checks["missing_doc_tokens"]:
        missing.append("operator-facing mocopi/fallback procedure documentation")
    return missing


def _operator_next_actions(
    label: str,
    code: str,
    blockers: list[str],
    evaluation: dict[str, Any] | None,
) -> list[str]:
    actions = []
    if blockers:
        actions.extend(
            [
                "Start Web/API on 8010 and Quest Vite on 5173.",
                "Connect Quest by USB, accept USB debugging, then run npm run dev:quest:adb.",
                f"Open Quest URL http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code={code}&qa=centerline.",
            ]
        )
    actions.extend(
        [
            "Capture BODY baseline pack before mocopi.",
            "Pair and calibrate mocopi sensors; confirm six sensors stay connected for 60 seconds.",
            "Capture MOCOPI candidate pack with -QaCenterline -Screencap.",
            "Disable/bypass mocopi and capture BODY/static fallback recovery within 60 seconds.",
        ]
    )
    if label == "mocopi-GO" and evaluation:
        actions.append("Keep a staffed BODY/static fallback operator watching the same gate during public mocopi use.")
    return actions


def _codex_next_commands(code: str, evaluation_json: str | Path | None) -> list[str]:
    commands = [
        "python tools/probe_mocopi_udp.py --port 12351 --seconds 20 --out qa\\mocopi-udp-probe-latest.json",
        f".\\tools\\capture_quest_debug_snapshot.ps1 -Code {code} -QaCenterline",
        f".\\tools\\capture_quest_debug_snapshot.ps1 -Code {code} -QaCenterline -Screencap",
        (
            "python tools/evaluate_mocopi_evidence_pack.py "
            "--body-baseline qa\\logs\\quest-<body> "
            "--mocopi-candidate qa\\logs\\quest-<mocopi> "
            "--fallback-recovery qa\\logs\\quest-<fallback> "
            f"--code {code} --report-json"
        ),
    ]
    if evaluation_json:
        commands.append(
            f"python tools/export_mocopi_rehearsal_plan.py --evaluation-json {evaluation_json} --report-json"
        )
    return commands


def _fallback_procedure(code: str) -> list[str]:
    return [
        "Stop claiming mocopi in operator/public wording.",
        "Disable or bypass the mocopi source.",
        f"Keep the same Quest URL code={code}; return to BODY/static without changing the visitor URL.",
        "Capture fallback recovery evidence within 60 seconds.",
        "If recovery fails, label mocopi-NO-GO and continue only with the stable BODY/static route.",
    ]


def _go_demo_no_go_rules() -> dict[str, list[str]]:
    return {
        "mocopi-GO": [
            "local stack and Quest USB/reverse are currently reachable",
            "evaluation JSON label is mocopi-GO",
            "BODY baseline, MOCOPI candidate, and fallback recovery packs pass",
            "manual pairing/calibration, latency, freeze/drop, left/right, consent, and retention gates are documented",
        ],
        "mocopi-DEMO-ONLY": [
            "local stack and Quest USB/reverse are reachable",
            "MOCOPI can be rehearsed with an operator",
            "one or more manual GO gates or evidence packs are still missing",
        ],
        "mocopi-NO-GO": [
            "required local files or diagnostics are missing",
            "8010/5173, adb authorization, adb reverse, or Quest debug API is not ready",
            "BODY/static baseline or fallback recovery is missing/failing",
        ],
    }


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except OSError:
        return ""


def _tcp_connects(host: str, port: int, timeout_sec: float) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_sec):
            return True
    except OSError:
        return False


def _run_command(args: list[str]) -> dict[str, Any]:
    try:
        completed = subprocess.run(args, check=False, capture_output=True, text=True, timeout=3)
    except OSError as exc:
        return {"returncode": 127, "stdout": "", "stderr": str(exc)}
    except subprocess.TimeoutExpired as exc:
        return {"returncode": 124, "stdout": exc.stdout or "", "stderr": exc.stderr or "command timed out"}
    return {"returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _print_text_report(report: dict[str, Any]) -> None:
    print(f"{report['current_gate_label']}: ready_to_start={report['ready_to_start_physical_rehearsal']}")
    if report["blocking_items"]:
        print("blocking_items:")
        for item in report["blocking_items"]:
            print(f"- {item}")
    print("operator_next_actions:")
    for item in report["operator_next_actions"]:
        print(f"- {item}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."), help="Repository root, default: current directory")
    parser.add_argument("--code", default="3601", help="Recall code to use in instructions, default: 3601")
    parser.add_argument("--api-url", default="http://127.0.0.1:8010/api/quest-debug/latest")
    parser.add_argument("--evaluation-json", type=Path, help="Optional mocopi evidence evaluation JSON")
    parser.add_argument("--skip-runtime", action="store_true", help="Only validate static repo/tool/doc readiness")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"Write JSON report, default: {DEFAULT_OUT}")
    parser.add_argument("--report-json", action="store_true", help="Emit JSON report to stdout")
    args = parser.parse_args(argv)

    report = prepare_mocopi_rehearsal_preflight(
        repo_root=args.repo_root,
        code=args.code,
        api_url=args.api_url,
        evaluation_json=args.evaluation_json,
        skip_runtime=args.skip_runtime,
    )
    if args.out:
        _write_json(args.out, report)
    if args.report_json:
        json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        _print_text_report(report)
    return 0 if report["current_gate_label"] != "mocopi-NO-GO" else 1


if __name__ == "__main__":
    raise SystemExit(main())
