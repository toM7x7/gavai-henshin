"""Evaluate Quest mocopi exhibition evidence packs.

The evaluator reads snapshot folders created by
tools/capture_quest_debug_snapshot.ps1 and emits a structured decision report
for the BODY baseline, MOCOPI candidate, and fallback recovery packs.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


CONTRACT_VERSION = "mocopi-evidence-pack-evaluator.v1"
ROLE_BODY_BASELINE = "body_baseline"
ROLE_MOCOPI_CANDIDATE = "mocopi_candidate"
ROLE_FALLBACK_RECOVERY = "fallback_recovery"
ROLE_DISPLAY = {
    ROLE_BODY_BASELINE: "BODY fallback baseline",
    ROLE_MOCOPI_CANDIDATE: "MOCOPI candidate",
    ROLE_FALLBACK_RECOVERY: "fallback recovery",
}
MOTION_TOKEN_RE = re.compile(
    r"\b(MOCOPI\+LIVE|MOCOPI\s+\d+f|BODY\+LIVE|BODY\s+\d+f|STATIC|SELF|CAPTURE|LIVE\s+\d+f)\b",
    re.IGNORECASE,
)
FRAME_COUNT_RE = re.compile(r"(\d+)\s*f", re.IGNORECASE)
CENTERLINE_GO_BLOCKERS = {"runtime_anchor", "hard_sync_centerline", "mixed"}


def evaluate_mocopi_evidence_packs(
    *,
    body_baseline: str | Path,
    mocopi_candidate: str | Path,
    fallback_recovery: str | Path,
    expected_code: str = "3601",
) -> dict[str, Any]:
    """Evaluate the three required mocopi evidence snapshot folders."""

    packs = {
        ROLE_BODY_BASELINE: evaluate_evidence_pack(body_baseline, ROLE_BODY_BASELINE, expected_code=expected_code),
        ROLE_MOCOPI_CANDIDATE: evaluate_evidence_pack(
            mocopi_candidate,
            ROLE_MOCOPI_CANDIDATE,
            expected_code=expected_code,
        ),
        ROLE_FALLBACK_RECOVERY: evaluate_evidence_pack(
            fallback_recovery,
            ROLE_FALLBACK_RECOVERY,
            expected_code=expected_code,
        ),
    }
    reasons: list[str] = []
    warnings: list[str] = []

    for role, pack in packs.items():
        for reason in pack["reasons"]:
            reasons.append(f"{role}: {reason}")
        for warning in pack["warnings"]:
            warnings.append(f"{role}: {warning}")

    all_packs_usable = all(pack["ok"] for pack in packs.values())
    candidate = packs[ROLE_MOCOPI_CANDIDATE]
    go_blockers = _go_blockers(packs)

    if not all_packs_usable:
        label = "mocopi-NO-GO"
        status = "fail"
        ok = False
    else:
        label = "mocopi-DEMO-ONLY" if go_blockers or warnings else "mocopi-GO"
        status = "warn" if label == "mocopi-DEMO-ONLY" else "pass"
        ok = True

    if label == "mocopi-DEMO-ONLY":
        warnings.extend(f"GO blocker: {blocker}" for blocker in go_blockers)

    return {
        "contract_version": CONTRACT_VERSION,
        "ok": ok,
        "status": status,
        "label": label,
        "expected_code": expected_code,
        "automatic_pack_gate_pass": all_packs_usable,
        "mocopi_candidate_usable": bool(candidate["motion"]["usable_mocopi"]),
        "packs": packs,
        "go_blockers": go_blockers,
        "reasons": reasons,
        "warnings": warnings,
    }


def evaluate_evidence_pack(path: str | Path, role: str, *, expected_code: str = "3601") -> dict[str, Any]:
    pack_path = Path(path)
    reasons: list[str] = []
    warnings: list[str] = []
    summary_path = pack_path / "operator-summary.txt"
    debug_path = pack_path / "quest-debug-latest.json"

    summary = _read_operator_summary(summary_path, reasons)
    debug_raw = _read_json(debug_path, reasons)
    payload = _quest_payload(debug_raw)
    if debug_raw.get("error"):
        reasons.append(f"quest-debug-latest.json contains API error: {debug_raw.get('error')}")

    query = payload.get("query") if isinstance(payload.get("query"), dict) else {}
    telemetry_code = _first_non_empty(summary.get("telemetryCode"), query.get("code"))
    href = _first_non_empty(summary.get("href"), query.get("href"))
    user_agent = _first_non_empty(summary.get("userAgent"), query.get("userAgent"))
    xr_session = _truthy(_first_non_empty(summary.get("xrSession"), _nested_get(payload, ["xr", "session"])))
    ux_state = _first_non_empty(summary.get("uxState"), payload.get("uxState"))
    api_error = summary.get("apiError", "").strip()
    if api_error:
        reasons.append(f"operator-summary apiError is set: {api_error}")

    if expected_code and telemetry_code and telemetry_code.upper() != expected_code.upper():
        reasons.append(f"telemetryCode {telemetry_code} does not match expected code {expected_code}")
    elif expected_code and not telemetry_code:
        warnings.append("telemetryCode is missing from summary and debug payload")

    if user_agent and "Quest" not in user_agent:
        reasons.append("userAgent does not identify Quest Browser")
    elif not user_agent:
        warnings.append("userAgent is missing; physical Quest evidence is not explicit")

    if not xr_session:
        warnings.append("xrSession is not true; pack does not prove in-headset XR runtime state")

    centerline = _centerline_material(summary, payload)
    _evaluate_centerline(centerline, role, reasons, warnings)
    motion = _motion_material(summary, payload)
    _evaluate_role_motion(role, motion, reasons)
    adb = _adb_material(pack_path)

    status = "fail" if reasons else "warn" if warnings else "pass"
    return {
        "role": role,
        "role_label": ROLE_DISPLAY.get(role, role),
        "path": pack_path.as_posix(),
        "ok": status != "fail",
        "status": status,
        "files": {
            "operator_summary": summary_path.exists(),
            "quest_debug_latest": debug_path.exists(),
            "adb_devices": (pack_path / "adb-devices.txt").exists(),
            "adb_reverse": (pack_path / "adb-reverse.txt").exists(),
            "screencap": (pack_path / "screencap.png").exists(),
        },
        "summary": {
            "href": href,
            "telemetryCode": telemetry_code,
            "uxState": ux_state,
            "xrSession": xr_session,
            "userAgentIsQuest": bool(user_agent and "Quest" in user_agent),
            "qaCenterlineExpected": _truthy(summary.get("qaCenterlineExpected")),
        },
        "adb": adb,
        "motion": motion,
        "centerline": centerline,
        "reasons": reasons,
        "warnings": warnings,
    }


def _go_blockers(packs: dict[str, dict[str, Any]]) -> list[str]:
    blockers = [
        "physical mocopi pairing/calibration evidence is not represented in the snapshot pack yet",
        "median/p95 latency and freeze/drop thresholds are not represented in the snapshot pack yet",
        "consent and retention evidence is not represented in the snapshot pack yet",
    ]
    candidate_centerline = packs[ROLE_MOCOPI_CANDIDATE]["centerline"]
    classification = str(candidate_centerline.get("classification") or "").strip()
    verdict = str(candidate_centerline.get("verdict") or "").strip()
    if verdict != "pass" or classification in CENTERLINE_GO_BLOCKERS:
        blockers.append(
            f"MOCOPI candidate centerline is {verdict or 'unknown'}/{classification or 'unknown'}"
        )
    candidate_adb = packs[ROLE_MOCOPI_CANDIDATE]["adb"]
    if candidate_adb["devices_present"] and not candidate_adb["device_authorized"]:
        blockers.append("MOCOPI candidate adb-devices.txt does not show an authorized device")
    if candidate_adb["reverse_present"] and not (candidate_adb["reverse_5173"] and candidate_adb["reverse_8010"]):
        blockers.append("MOCOPI candidate adb-reverse.txt does not show both tcp:5173 and tcp:8010")
    return blockers


def _read_operator_summary(path: Path, reasons: list[str]) -> dict[str, str]:
    if not path.exists():
        reasons.append("operator-summary.txt is missing")
        return {}
    summary: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        summary[key.strip()] = value.strip()
    return summary


def _read_json(path: Path, reasons: list[str]) -> dict[str, Any]:
    if not path.exists():
        reasons.append("quest-debug-latest.json is missing")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        reasons.append(f"quest-debug-latest.json is invalid JSON: {exc}")
        return {}
    return payload if isinstance(payload, dict) else {}


def _quest_payload(debug_raw: dict[str, Any]) -> dict[str, Any]:
    record = debug_raw.get("record")
    if isinstance(record, dict) and isinstance(record.get("payload"), dict):
        return record["payload"]
    if isinstance(debug_raw.get("payload"), dict):
        return debug_raw["payload"]
    return debug_raw


def _centerline_material(summary: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
    centerline = payload.get("centerlineQa") if isinstance(payload.get("centerlineQa"), dict) else {}
    return {
        "present": bool(centerline) or bool(summary.get("centerlineVerdict")),
        "verdict": _first_non_empty(summary.get("centerlineVerdict"), centerline.get("verdict")),
        "classification": _first_non_empty(summary.get("centerlineClassification"), centerline.get("classification")),
        "displayLine": _first_non_empty(summary.get("centerlineDisplayLine"), centerline.get("displayLine")),
        "flags": centerline.get("flags") if isinstance(centerline.get("flags"), list) else [],
    }


def _evaluate_centerline(
    centerline: dict[str, Any],
    role: str,
    reasons: list[str],
    warnings: list[str],
) -> None:
    if not centerline["present"]:
        reasons.append("centerlineQa is missing")
        return
    verdict = str(centerline.get("verdict") or "").strip()
    classification = str(centerline.get("classification") or "").strip()
    if verdict == "pass" and classification == "pass":
        return
    if role in {ROLE_BODY_BASELINE, ROLE_FALLBACK_RECOVERY} and verdict == "fail":
        reasons.append(f"centerlineQa blocks baseline/fallback: {verdict}/{classification}")
    else:
        warnings.append(f"centerlineQa blocks GO: {verdict or 'unknown'}/{classification or 'unknown'}")


def _motion_material(summary: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
    candidates = _motion_candidates(payload)
    for value in summary.values():
        if isinstance(value, str):
            token_match = MOTION_TOKEN_RE.search(value)
            if token_match:
                candidates.append({"token": token_match.group(1), "path": "operator-summary.txt"})
    best = _select_motion_candidate(candidates)
    token = str(best.get("token") or "").strip()
    category = _motion_category(token, best)
    frame_count = _motion_frame_count(token, best)
    usable_mocopi = category == "mocopi" and (frame_count is None or frame_count > 0)
    usable_body_or_static = category in {"body", "static"}
    return {
        "present": bool(token or best.get("motion_source")),
        "token": token,
        "category": category,
        "frame_count": frame_count,
        "motion_source": best.get("motion_source") or "",
        "source": best.get("source") or "",
        "live_pose_frames": _number_or_none(best.get("live_pose_frames")),
        "body_sim_frames": _number_or_none(best.get("body_sim_frames")),
        "path": best.get("path") or "",
        "usable_mocopi": usable_mocopi,
        "usable_body_or_static": usable_body_or_static,
    }


def _evaluate_role_motion(role: str, motion: dict[str, Any], reasons: list[str]) -> None:
    token = motion["token"] or motion["motion_source"] or motion["source"] or "missing"
    if role == ROLE_MOCOPI_CANDIDATE:
        if not motion["usable_mocopi"]:
            reasons.append(f"MOCOPI candidate does not show usable MOCOPI motion token: {token}")
        return
    if motion["category"] == "mocopi":
        reasons.append(f"{ROLE_DISPLAY[role]} unexpectedly still shows MOCOPI motion: {token}")
    elif not motion["usable_body_or_static"]:
        reasons.append(f"{ROLE_DISPLAY[role]} does not show BODY/static fallback motion: {token}")


def _motion_candidates(payload: Any) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    def visit(value: Any, path: str) -> None:
        if isinstance(value, dict):
            token = value.get("token")
            token_text = str(token).strip() if token is not None else ""
            if token_text and (_motion_category(token_text, value) != "unknown" or "motion_source" in value):
                candidates.append(
                    {
                        "path": path or "$",
                        "token": token_text,
                        "motion_source": value.get("motion_source", ""),
                        "source": value.get("source", ""),
                        "live_pose_frames": value.get("live_pose_frames"),
                        "body_sim_frames": value.get("body_sim_frames"),
                    }
                )
            elif any(key in value for key in ("motion_source", "live_pose_frames", "body_sim_frames")):
                candidates.append(
                    {
                        "path": path or "$",
                        "token": "",
                        "motion_source": value.get("motion_source", ""),
                        "source": value.get("source", ""),
                        "live_pose_frames": value.get("live_pose_frames"),
                        "body_sim_frames": value.get("body_sim_frames"),
                    }
                )
            for key, child in value.items():
                visit(child, f"{path}.{key}" if path else str(key))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{path}[{index}]")
        elif isinstance(value, str):
            match = MOTION_TOKEN_RE.search(value)
            if match:
                candidates.append({"path": path, "token": match.group(1)})

    visit(payload, "")
    return candidates


def _select_motion_candidate(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    if not candidates:
        return {}
    categories = {"mocopi": 0, "body": 1, "static": 2, "live": 3, "capture": 4, "self": 5, "unknown": 6}
    return sorted(candidates, key=lambda item: categories.get(_motion_category(str(item.get("token") or ""), item), 6))[0]


def _motion_category(token: str, diagnostic: dict[str, Any] | None = None) -> str:
    upper = token.upper().strip()
    source = ""
    if diagnostic:
        source = " ".join(
            str(diagnostic.get(key) or "").lower()
            for key in ("motion_source", "source")
        )
    if upper.startswith("MOCOPI") or "mocopi" in source:
        return "mocopi"
    if upper.startswith("BODY") or "body_sim" in source:
        return "body"
    if upper.startswith("STATIC") or "static" in source:
        return "static"
    if upper.startswith("LIVE") or "live_pose" in source:
        return "live"
    if upper.startswith("CAPTURE") or "capture" in source:
        return "capture"
    if upper.startswith("SELF") or "first_person" in source:
        return "self"
    return "unknown"


def _motion_frame_count(token: str, diagnostic: dict[str, Any]) -> int | None:
    match = FRAME_COUNT_RE.search(token)
    if match:
        return int(match.group(1))
    frame_values = [
        _number_or_none(diagnostic.get("body_sim_frames")),
        _number_or_none(diagnostic.get("live_pose_frames")),
    ]
    usable = [value for value in frame_values if value is not None]
    if usable:
        return int(max(usable))
    return None


def _adb_material(pack_path: Path) -> dict[str, Any]:
    devices_path = pack_path / "adb-devices.txt"
    reverse_path = pack_path / "adb-reverse.txt"
    devices_text = devices_path.read_text(encoding="utf-8-sig", errors="replace") if devices_path.exists() else ""
    reverse_text = reverse_path.read_text(encoding="utf-8-sig", errors="replace") if reverse_path.exists() else ""
    device_lines = [line for line in devices_text.splitlines() if "\tdevice" in line or " device " in f" {line} "]
    unauthorized = "unauthorized" in devices_text.lower()
    return {
        "devices_present": devices_path.exists(),
        "reverse_present": reverse_path.exists(),
        "device_authorized": bool(device_lines) and not unauthorized,
        "unauthorized": unauthorized,
        "reverse_5173": "tcp:5173" in reverse_text,
        "reverse_8010": "tcp:8010" in reverse_text,
    }


def _first_non_empty(*values: Any) -> str:
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _number_or_none(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _nested_get(payload: dict[str, Any], keys: list[str]) -> Any:
    value: Any = payload
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _print_text_report(result: dict[str, Any]) -> None:
    print(f"{result['label']} ({result['status']})")
    for role, pack in result["packs"].items():
        motion = pack["motion"]
        print(f"- {role}: {pack['status']} token={motion['token'] or motion['motion_source'] or 'missing'}")
        for reason in pack["reasons"]:
            print(f"  reason: {reason}")
        for warning in pack["warnings"]:
            print(f"  warning: {warning}")
    for blocker in result["go_blockers"]:
        print(f"GO blocker: {blocker}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--body-baseline", required=True, type=Path, help="BODY fallback baseline snapshot folder")
    parser.add_argument("--mocopi-candidate", required=True, type=Path, help="MOCOPI candidate snapshot folder")
    parser.add_argument("--fallback-recovery", required=True, type=Path, help="fallback recovery snapshot folder")
    parser.add_argument("--code", default="3601", help="Expected recall code, default: 3601")
    parser.add_argument("--report-json", action="store_true", help="Emit a structured JSON report")
    args = parser.parse_args(argv)

    result = evaluate_mocopi_evidence_packs(
        body_baseline=args.body_baseline,
        mocopi_candidate=args.mocopi_candidate,
        fallback_recovery=args.fallback_recovery,
        expected_code=args.code,
    )
    if args.report_json:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        _print_text_report(result)
    return 0 if result["status"] != "fail" else 1


if __name__ == "__main__":
    raise SystemExit(main())
