"""Export a mocopi exhibition rehearsal plan from evidence evaluation.

The plan keeps mocopi as the ideal line while making BODY/static fallback the
safe show-floor baseline whenever the evidence is incomplete or degraded.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from evaluate_mocopi_evidence_pack import evaluate_mocopi_evidence_packs  # noqa: E402


CONTRACT_VERSION = "mocopi-rehearsal-plan.v1"
DEFAULT_OUT = Path("qa/mocopi-rehearsal-plan-latest.json")
PACK_ROLES = ("body_baseline", "mocopi_candidate", "fallback_recovery")


def export_mocopi_rehearsal_plan(evaluation: dict[str, Any]) -> dict[str, Any]:
    label = str(evaluation.get("label") or "mocopi-NO-GO")
    packs = evaluation.get("packs") if isinstance(evaluation.get("packs"), dict) else {}
    go_blockers = _string_list(evaluation.get("go_blockers"))
    reasons = _string_list(evaluation.get("reasons"))
    warnings = _string_list(evaluation.get("warnings"))

    return {
        "contract_version": CONTRACT_VERSION,
        "current_gate_label": label,
        "status": _plan_status(label),
        "source_evaluation": {
            "contract_version": evaluation.get("contract_version", ""),
            "status": evaluation.get("status", ""),
            "label": label,
            "expected_code": evaluation.get("expected_code", "3601"),
            "automatic_pack_gate_pass": bool(evaluation.get("automatic_pack_gate_pass")),
            "mocopi_candidate_usable": bool(evaluation.get("mocopi_candidate_usable")),
        },
        "target_environment": _target_environment(),
        "lane_policy": _lane_policy(label),
        "external_pc_stage_table": _external_pc_stage_table(label),
        "quest_mocopi_connection_stage_table": _quest_mocopi_connection_stage_table(label, packs),
        "web_service_anshin_lane": _web_service_anshin_lane(),
        "mocopi_go_promotion_conditions": _mocopi_go_promotion_conditions(label),
        "rehearsal_steps": _rehearsal_steps(label, packs, reasons, go_blockers),
        "operator_script": _operator_script(label),
        "risk_register": _risk_register(label, packs, reasons, warnings, go_blockers),
        "fallback_trigger_points": _fallback_trigger_points(label, packs),
        "evidence_to_collect": _evidence_to_collect(label, packs, go_blockers),
    }


def load_evaluation_json(path: str | Path) -> dict[str, Any]:
    loaded = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(loaded, dict):
        raise ValueError("evaluation JSON must be an object")
    return loaded


def load_or_evaluate(args: argparse.Namespace) -> dict[str, Any]:
    if args.evaluation_json:
        return load_evaluation_json(args.evaluation_json)
    missing = [
        flag
        for flag, value in (
            ("--body-baseline", args.body_baseline),
            ("--mocopi-candidate", args.mocopi_candidate),
            ("--fallback-recovery", args.fallback_recovery),
        )
        if value is None
    ]
    if missing:
        raise ValueError(
            "either --evaluation-json or all three evidence pack folders are required: "
            + ", ".join(missing)
        )
    return evaluate_mocopi_evidence_packs(
        body_baseline=args.body_baseline,
        mocopi_candidate=args.mocopi_candidate,
        fallback_recovery=args.fallback_recovery,
        expected_code=args.code,
    )


def _plan_status(label: str) -> str:
    if label.endswith("GO") and label != "mocopi-NO-GO":
        return "ready_with_fallback"
    if label == "mocopi-DEMO-ONLY":
        return "operator_rehearsal_only"
    return "fallback_only"


def _target_environment() -> dict[str, Any]:
    return {
        "operator_profile": "external exhibition PC / Quest / mocopi introduction baseline",
        "pc": {
            "os": "Windows",
            "gpu": "unknown; treat discrete GPU as nice-to-have, not a required gate",
            "required_runtime": ["Python 3.11+", "Node.js/npm", "Android Platform Tools or Meta Quest Developer Hub"],
            "default_repo_path": "C:\\henshin-demo\\gavai-henshin",
        },
        "quest": {
            "preferred_transport": "USB ADB reverse",
            "usb_available": True,
            "same_lan_available": True,
            "same_lan_role": "fallback only when USB cannot be used and client-to-client traffic is verified",
        },
        "mocopi": {
            "hardware_available": True,
            "current_experience": "available but unused; start as operator rehearsal, not public visitor default",
        },
        "fixed_ports": {"web_api": 8010, "quest_vite": 5173},
    }


def _lane_policy(label: str) -> dict[str, Any]:
    return {
        "required_baseline": {
            "lane": "external_pc_local",
            "label": "local-pass/fail",
            "rule": "local-pass is mandatory before visitor operation and cannot be overridden by service, PlayCanvas, or mocopi.",
            "fallback": "BODY/static local fallback must remain runnable without internet, cloud services, provider secrets, or mocopi.",
        },
        "optional_lanes": [
            {
                "lane": "web_service_anshin",
                "label": "service-pass/fail/not-included",
                "role": "安心レーン: prove a hosted/service route without making it the show-floor dependency.",
            },
            {
                "lane": "playcanvas_adapter",
                "label": "playcanvas-pass/fail/not-included",
                "role": "adapter-only preview/QA; never the source of variant, placement, recall, or replay truth.",
            },
            {
                "lane": "mocopi",
                "label": "mocopi-GO/DEMO-ONLY/NO-GO/not-included",
                "role": "hardware enhancement; current label is decided separately after local-pass.",
                "current_label": label,
            },
        ],
    }


def _external_pc_stage_table(label: str) -> list[dict[str, Any]]:
    return [
        {
            "stage": "0",
            "name": "Freeze and carry package",
            "owner": "release owner",
            "actions": [
                "Choose one source package: git checkout, working-tree snapshot, or dated zip.",
                "Copy it to C:\\henshin-demo\\gavai-henshin on the exhibition PC.",
                "Carry qa JSON reports with the package; do not rely on C:\\dev\\codex paths.",
            ],
            "pass_criteria": "Package path is fixed and required files are present on the external PC.",
            "fallback": "Use the last-known-good package; do not repair from the development PC during visitor time.",
        },
        {
            "stage": "1",
            "name": "Install local dependencies",
            "owner": "external PC operator",
            "actions": [
                "Run node --version, npm --version, python --version, and adb version.",
                "Run npm install and python -m pip install -e \".[dev]\".",
                "If imports fail, set PYTHONPATH to $PWD\\src.",
            ],
            "pass_criteria": "Node, Python, and adb are available on the external PC.",
            "fallback": "Stop optional lanes and keep the package for offline review until dependencies are fixed.",
        },
        {
            "stage": "2",
            "name": "Validate local package",
            "owner": "release owner / asset QA",
            "actions": [
                "Run python tools/validate_exhibition_release_package.py --report-json.",
                "Run python tools/smoke_web_glb_load.py --repo-root . --report-json.",
            ],
            "pass_criteria": "missing_count=0, pattern_gap_count=0, no GLB failures, previewFallbackParts=0.",
            "fallback": "local-fail; use last-known-good package or static/BODY fallback only.",
        },
        {
            "stage": "3",
            "name": "Start fixed local servers",
            "owner": "web/Quest owner",
            "actions": [
                "Start Web/API/static on port 8010.",
                "Start Quest Vite on host 0.0.0.0 port 5173.",
                "Confirm both ports with Get-NetTCPConnection.",
            ],
            "pass_criteria": "8010 and 5173 are listening on the external PC.",
            "fallback": "Do not change ports during showtime unless adb reverse, Quest URL, docs, and smoke command are updated together.",
        },
        {
            "stage": "4",
            "name": "Prove Quest transport",
            "owner": "Quest owner",
            "actions": [
                "Prefer USB-C data cable and accept the Quest USB debugging prompt.",
                "Run adb devices -l and require device, not unauthorized.",
                "Run npm run dev:quest:adb or .\\tools\\start_quest_adb_reverse.ps1 -RecallCode <CODE> -CacheBust -LaunchBrowser.",
                "Use same-LAN URL only if USB cannot be used and PC/Quest reachability is verified.",
            ],
            "pass_criteria": "adb reverse --list includes tcp:5173 and tcp:8010, or the verified LAN URL opens from Quest.",
            "fallback": "Return to USB ADB reverse; venue shared Wi-Fi is a fallback path, not the primary baseline.",
        },
        {
            "stage": "5",
            "name": "Record local-pass with fresh code",
            "owner": "PM / exhibition lead",
            "actions": [
                "Open Web Forge at http://127.0.0.1:8010/viewer/armor-forge/.",
                "Generate a fresh 4-digit code; do not reuse historical 3601 as the carry-in proof.",
                "Open Quest at http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=<CODE>.",
                "Run python tools/exhibition_smoke_check.py --forge --require-adb-reverse when USB is selected.",
            ],
            "pass_criteria": "preflight_gate.operator_label=local-pass and Web/Quest agree on the fresh code.",
            "fallback": "If local-pass is not recorded, visitors use only the last-known-good BODY/static local fallback.",
        },
        {
            "stage": "6",
            "name": "Optional lanes after local-pass",
            "owner": "service / adapter / hardware owners",
            "actions": [
                "Mark web service lane service-pass/fail/not-included.",
                "Mark PlayCanvas lane playcanvas-pass/fail/not-included.",
                "Mark mocopi lane mocopi-GO/DEMO-ONLY/NO-GO/not-included.",
            ],
            "pass_criteria": "Optional labels are written after local-pass and do not change the fallback route.",
            "fallback": f"Current mocopi label remains {label}; BODY/static stays public default unless label is mocopi-GO.",
        },
    ]


def _quest_mocopi_connection_stage_table(label: str, packs: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "stage": "Q0",
            "name": "Quest baseline over USB",
            "owner": "Quest owner",
            "actions": [
                "Connect Quest to the external PC with a USB-C data cable.",
                "Accept USB debugging in the headset.",
                "Run adb devices -l and require device.",
                "Run adb reverse for tcp:5173 and tcp:8010.",
            ],
            "pass_criteria": "Quest opens localhost:5173 and can recall the fresh Web Forge code.",
            "evidence_refs": [_pack_path(packs, "body_baseline")],
            "fallback": "If unauthorized or reverse is missing, do not start mocopi; recover USB or use verified same-LAN fallback.",
        },
        {
            "stage": "Q1",
            "name": "BODY/static evidence",
            "owner": "Quest owner",
            "actions": [
                "Keep mocopi off, ignored, or bypassed.",
                "Run the visitor route once with BODY/static.",
                "Capture .\\tools\\capture_quest_debug_snapshot.ps1 -Code <CODE> -QaCenterline.",
            ],
            "pass_criteria": "BODY/static is usable and centerline QA is not failing baseline.",
            "evidence_refs": [_pack_path(packs, "body_baseline")],
            "fallback": "If this fails, mocopi is mocopi-NO-GO for public operation.",
        },
        {
            "stage": "Q2",
            "name": "mocopi pairing and calibration",
            "owner": "mocopi operator",
            "actions": [
                "Charge, label, and pair the six sensors: head, hip, left_wrist, right_wrist, left_ankle, right_ankle.",
                "Confirm all sensors stay connected for at least 60 seconds before calibration.",
                "Calibrate with the participant facing the Quest/exhibition-PC origin.",
                "Run slow arm raise and weight shift checks for left/right correctness.",
            ],
            "pass_criteria": "Pairing, calibration, and left/right mapping are stable before Quest promotion.",
            "evidence_refs": [_pack_path(packs, "mocopi_candidate")],
            "fallback": "If any sensor disconnects twice, stay mocopi-DEMO-ONLY or mocopi-NO-GO and return to BODY/static.",
        },
        {
            "stage": "Q3",
            "name": "mocopi candidate capture",
            "owner": "mocopi operator / Quest owner",
            "actions": [
                "Run imported mocopi or physical sensor rehearsal in an operator-only lane.",
                "Confirm Quest diagnostic shows MOCOPI <n>f or MOCOPI+LIVE, not MOCOPI 0f.",
                "Capture candidate evidence with -QaCenterline -Screencap.",
            ],
            "pass_criteria": "Quest shows usable mocopi frames and no unresolved centerline hard blocker.",
            "evidence_refs": [_pack_path(packs, "mocopi_candidate")],
            "fallback": "If diagnostic is not MOCOPI, do not claim mocopi; continue BODY/static.",
        },
        {
            "stage": "Q4",
            "name": "Fallback recovery capture",
            "owner": "Quest owner",
            "actions": [
                "Disable or bypass mocopi.",
                "Return to BODY/static without changing the public visitor URL.",
                "Capture recovery evidence within 60 seconds.",
            ],
            "pass_criteria": "Fallback recovery pack proves BODY/static within 60 seconds.",
            "evidence_refs": [_pack_path(packs, "fallback_recovery")],
            "fallback": "If recovery exceeds 60 seconds, label mocopi-NO-GO for visitor operation.",
        },
        {
            "stage": "Q5",
            "name": "Write label and public route",
            "owner": "exhibition lead",
            "actions": [
                "Write mocopi-GO, mocopi-DEMO-ONLY, mocopi-NO-GO, or not-included.",
                "Keep public visitor route BODY/static unless the label is mocopi-GO.",
            ],
            "pass_criteria": f"Current plan label is {label}; public wording matches that label.",
            "fallback": "When in doubt, downgrade to DEMO-ONLY and keep BODY/static as the public lane.",
        },
    ]


def _web_service_anshin_lane() -> dict[str, Any]:
    return {
        "lane": "web_service_anshin",
        "label": "service-pass/fail/not-included",
        "definition": "安心レーン: a hosted/service rehearsal that proves future serviceization while preserving the external-PC local fallback as the show-floor source of truth.",
        "entry_condition": "external-PC local-pass is already recorded.",
        "pass_condition": "Hosted/service endpoint passes forge, recall, replay/artifact, and no-local-path checks with HTTPS public URLs.",
        "failure_behavior": "Record service-fail or not-included; do not block visitors and do not replace the local fallback.",
    }


def _mocopi_go_promotion_conditions(label: str) -> dict[str, Any]:
    conditions = [
        "external-PC local-pass is recorded with a fresh Web Forge code",
        "BODY fallback baseline pack exists and passes",
        "physical mocopi pairing and calibration are documented",
        "six sensors stay connected for at least 60 seconds before calibration",
        "Quest diagnostic shows usable MOCOPI frames or MOCOPI+LIVE",
        "median visible latency <= 120 ms and p95 <= 250 ms",
        "frozen/dropped motion < 2% and no freeze > 500 ms",
        "left/right arm raise and weight shift checks do not swap sides",
        "centerline QA does not report runtime_anchor, hard_sync_centerline, mixed, or fail",
        "consent and retention notes exist for raw mocopi motion",
        "fallback recovery to BODY/static is proven within 60 seconds",
    ]
    return {
        "current_label": label,
        "demo_only_default": "Because the equipment exists but is unused, start from mocopi-DEMO-ONLY or not-included until every GO condition has evidence.",
        "conditions": conditions,
        "public_route_rule": "Only mocopi-GO can enter the default visitor path; DEMO-ONLY stays operator-led and NO-GO stays off.",
    }


def _rehearsal_steps(
    label: str,
    packs: dict[str, Any],
    reasons: list[str],
    go_blockers: list[str],
) -> list[dict[str, Any]]:
    steps = [
        {
            "id": "baseline-01",
            "phase": "BODY baseline",
            "owner": "Quest operator",
            "action": "On the external Windows PC, start Web/API 8010 and Quest Vite 5173, apply USB adb reverse, then run the BODY/static visitor route first.",
            "pass_criteria": "local-pass is recorded and the BODY fallback baseline pack is pass or warn-only.",
            "fallback_if_failed": "Stop mocopi rehearsal and recover local BODY/static route before visitors continue.",
            "evidence_refs": [_pack_path(packs, "body_baseline")],
        },
        {
            "id": "baseline-02",
            "phase": "BODY baseline",
            "owner": "Quest operator",
            "action": "Capture BODY fallback evidence with capture_quest_debug_snapshot.ps1 -Code 3601 -QaCenterline.",
            "pass_criteria": "operator-summary.txt and quest-debug-latest.json show code 3601, Quest user agent, centerline QA, and BODY/static motion.",
            "fallback_if_failed": "Treat mocopi as NO-GO until the baseline pack can be captured.",
            "evidence_refs": [_pack_path(packs, "body_baseline")],
        },
        {
            "id": "mocopi-01",
            "phase": "mocopi candidate",
            "owner": "mocopi operator",
            "action": "Pair and calibrate the available mocopi sensors, then run imported mocopi or physical sensor rehearsal in an operator-only lane; do not change the public visitor URL.",
            "pass_criteria": "Quest visibly reports MOCOPI <n>f or MOCOPI+LIVE with usable frames and the pairing/calibration note exists.",
            "fallback_if_failed": "Announce internal BODY fallback and skip public mocopi wording.",
            "evidence_refs": [_pack_path(packs, "mocopi_candidate")],
        },
        {
            "id": "mocopi-02",
            "phase": "mocopi candidate",
            "owner": "Quest operator",
            "action": "Capture MOCOPI candidate evidence with -QaCenterline and -Screencap when visual fit is disputed.",
            "pass_criteria": "MOCOPI candidate pack has usable mocopi motion and centerline QA does not fail runtime anchor.",
            "fallback_if_failed": "Keep the run as DEMO-ONLY or NO-GO according to the evaluation report.",
            "evidence_refs": [_pack_path(packs, "mocopi_candidate")],
        },
        {
            "id": "fallback-01",
            "phase": "fallback recovery",
            "owner": "Quest operator",
            "action": "Disable or bypass mocopi, then return to BODY/static without changing the public route.",
            "pass_criteria": "Fallback recovery pack shows BODY/static within 60 seconds.",
            "fallback_if_failed": "Label mocopi-NO-GO for show-floor operation.",
            "evidence_refs": [_pack_path(packs, "fallback_recovery")],
        },
    ]
    if label == "mocopi-NO-GO":
        steps.insert(
            0,
            {
                "id": "no-go-00",
                "phase": "stop condition",
                "owner": "exhibition lead",
                "action": "Do not rehearse mocopi in front of visitors; keep BODY/static as the only public route.",
                "pass_criteria": "The operator can explain the run as BODY baseline without claiming mocopi.",
                "fallback_if_failed": "Pause public operation until BODY/static local-pass is restored.",
                "blocking_items": reasons,
            },
        )
    elif label == "mocopi-DEMO-ONLY":
        steps.append(
            {
                "id": "demo-only-01",
                "phase": "operator demo",
                "owner": "exhibition lead",
                "action": "Use mocopi only as a guided rehearsal after the visitor baseline is complete.",
                "pass_criteria": "All GO blockers are explicitly named before the demo starts.",
                "fallback_if_failed": "Return to BODY/static and skip mocopi narration.",
                "blocking_items": go_blockers,
            }
        )
    else:
        steps.append(
            {
                "id": "go-01",
                "phase": "public candidate",
                "owner": "exhibition lead",
                "action": "Allow mocopi in the public route only with a staffed fallback operator watching the same gate.",
                "pass_criteria": "No fallback trigger fires during the rehearsal window.",
                "fallback_if_failed": "Switch to BODY/static within 60 seconds and downgrade to DEMO-ONLY.",
            }
        )
    return steps


def _operator_script(label: str) -> list[dict[str, str]]:
    lines = [
        {
            "moment": "before visitors",
            "line": "First we prove Web -> Quest -> Replay on the local BODY fallback. mocopi is checked afterward in an operator lane.",
        },
        {
            "moment": "before mocopi",
            "line": "mocopi is available, but it is not the visitor default until GO evidence is collected. If display or recovery is unstable, return to BODY/static.",
        },
        {
            "moment": "fallback",
            "line": "We are back on BODY fallback now. The visitor flow continues; mocopi adjustment happens off the public route.",
        },
    ]
    if label == "mocopi-NO-GO":
        lines.insert(
            0,
            {
                "moment": "gate",
                "line": "Today mocopi is not used for public operation. BODY baseline is the official route.",
            },
        )
    elif label == "mocopi-DEMO-ONLY":
        lines.append(
            {
                "moment": "demo-only",
                "line": "This is an operator-led mocopi rehearsal, not the visitor default. We collect evidence while BODY/static stays ready.",
            }
        )
    else:
        lines.append(
            {
                "moment": "go",
                "line": "mocopi may run in the public route, with a staffed BODY/static fallback that can recover within 60 seconds.",
            }
        )
    return lines


def _risk_register(
    label: str,
    packs: dict[str, Any],
    reasons: list[str],
    warnings: list[str],
    go_blockers: list[str],
) -> list[dict[str, Any]]:
    risks = [
        {
            "id": "risk-local-baseline",
            "severity": "critical" if label == "mocopi-NO-GO" else "high",
            "trigger": "BODY baseline or fallback recovery pack fails, is missing, or still shows MOCOPI.",
            "mitigation": "Keep the public route on BODY/static and rerun capture_quest_debug_snapshot.ps1 before mocopi.",
            "evidence": [_pack_path(packs, "body_baseline"), _pack_path(packs, "fallback_recovery")],
        },
        {
            "id": "risk-mocopi-claim",
            "severity": "high",
            "trigger": "MOCOPI candidate lacks usable MOCOPI frames or shows only BODY/static.",
            "mitigation": "Do not claim live mocopi; label mocopi-DEMO-ONLY or mocopi-NO-GO.",
            "evidence": [_pack_path(packs, "mocopi_candidate")],
        },
        {
            "id": "risk-centerline",
            "severity": "high",
            "trigger": "centerline QA reports runtime_anchor, hard_sync_centerline, mixed, or fail.",
            "mitigation": "Treat mocopi as source-only rehearsal until Quest anchor/placement QA is cleared.",
            "evidence": [_centerline_summary(packs)],
        },
        {
            "id": "risk-adb-debug",
            "severity": "medium",
            "trigger": "adb devices is unauthorized or adb reverse lacks tcp:5173/tcp:8010.",
            "mitigation": "Fix USB authorization/reverse before trusting the pack or switching URLs.",
            "evidence": [_adb_summary(packs)],
        },
    ]
    for index, item in enumerate(reasons, start=1):
        risks.append(
            {
                "id": f"risk-eval-reason-{index:02d}",
                "severity": "critical",
                "trigger": item,
                "mitigation": "Resolve this evaluator reason, then regenerate the evidence pack and rehearsal plan.",
            }
        )
    for index, item in enumerate(go_blockers or warnings, start=1):
        risks.append(
            {
                "id": f"risk-go-blocker-{index:02d}",
                "severity": "high",
                "trigger": item,
                "mitigation": "Keep mocopi out of the visitor default until this blocker has explicit evidence.",
            }
        )
    return risks


def _fallback_trigger_points(label: str, packs: dict[str, Any]) -> list[dict[str, Any]]:
    triggers = [
        {
            "trigger": "Quest stops showing usable MOCOPI frames or shows MOCOPI 0f.",
            "action": "Switch to BODY/static artifact and capture fallback recovery pack.",
            "max_recovery_sec": 60,
            "public_wording": "Continue the experience on BODY fallback.",
        },
        {
            "trigger": "centerline QA becomes runtime_anchor, hard_sync_centerline, mixed, or fail.",
            "action": "Stop mocopi promotion and keep the run as operator-only evidence.",
            "max_recovery_sec": 60,
            "public_wording": "Return to the normal BODY route while display alignment is checked.",
        },
        {
            "trigger": "adb devices becomes unauthorized or Quest debug latest cannot be captured.",
            "action": "Do not trust the mocopi state; recover USB debug/reverse before retry.",
            "max_recovery_sec": 60,
            "public_wording": "Use BODY route while the headset connection is restored.",
        },
        {
            "trigger": "left/right limb swap, visible freeze above the gate, or operator cannot recover quickly.",
            "action": "Call mocopi-NO-GO for the public route and continue with BODY/static baseline.",
            "max_recovery_sec": 60,
            "public_wording": "Continue on the stable BODY baseline.",
        },
    ]
    if label == "mocopi-NO-GO":
        triggers.insert(
            0,
            {
                "trigger": "Current gate label is mocopi-NO-GO.",
                "action": "Do not start mocopi visitor rehearsal; run BODY/static only.",
                "max_recovery_sec": 0,
                "public_wording": "Today uses the stable BODY baseline.",
                "evidence": [_pack_path(packs, role) for role in PACK_ROLES],
            },
        )
    return triggers


def _evidence_to_collect(
    label: str,
    packs: dict[str, Any],
    go_blockers: list[str],
) -> list[dict[str, Any]]:
    evidence = [
        {
            "id": "evidence-body-baseline",
            "when": "Before mocopi rehearsal",
            "command": ".\\tools\\capture_quest_debug_snapshot.ps1 -Code 3601 -QaCenterline",
            "required_files": ["operator-summary.txt", "quest-debug-latest.json", "adb-devices.txt", "adb-reverse.txt"],
            "decision_use": "Proves BODY/static visitor baseline before mocopi.",
            "current_path": _pack_path(packs, "body_baseline"),
        },
        {
            "id": "evidence-mocopi-candidate",
            "when": "During imported mocopi or physical sensor rehearsal",
            "command": ".\\tools\\capture_quest_debug_snapshot.ps1 -Code 3601 -QaCenterline -Screencap",
            "required_files": [
                "operator-summary.txt",
                "quest-debug-latest.json",
                "adb-devices.txt",
                "adb-reverse.txt",
                "screencap.png",
            ],
            "decision_use": "Proves MOCOPI token, usable frames, centerline state, and visual claim.",
            "current_path": _pack_path(packs, "mocopi_candidate"),
        },
        {
            "id": "evidence-fallback-recovery",
            "when": "After disabling or bypassing mocopi",
            "command": ".\\tools\\capture_quest_debug_snapshot.ps1 -Code 3601 -QaCenterline",
            "required_files": ["operator-summary.txt", "quest-debug-latest.json", "adb-devices.txt", "adb-reverse.txt"],
            "decision_use": "Proves return to BODY/static within 60 seconds.",
            "current_path": _pack_path(packs, "fallback_recovery"),
        },
        {
            "id": "evidence-plan",
            "when": "After all three packs are captured",
            "command": "python tools/export_mocopi_rehearsal_plan.py --evaluation-json <evaluation.json> --out qa/mocopi-rehearsal-plan-latest.json --report-json",
            "required_files": ["qa/mocopi-rehearsal-plan-latest.json"],
            "decision_use": "Hands the show-floor team a concrete rehearsal/fallback runbook.",
        },
    ]
    if label != "mocopi-GO":
        evidence.append(
            {
                "id": "evidence-manual-go-blockers",
                "when": "Only if the team wants to promote beyond DEMO-ONLY",
                "command": "Record pairing/calibration, latency p50/p95, freeze/drop, left/right, consent, and retention notes.",
                "required_files": ["operator notes", "latency notes", "consent/retention note"],
                "decision_use": "Clears the non-snapshot blockers before mocopi-GO.",
                "open_blockers": go_blockers,
            }
        )
    return evidence


def _pack_path(packs: dict[str, Any], role: str) -> str:
    pack = packs.get(role) if isinstance(packs.get(role), dict) else {}
    return str(pack.get("path") or "")


def _centerline_summary(packs: dict[str, Any]) -> dict[str, Any]:
    return {
        role: (packs.get(role) or {}).get("centerline", {})
        for role in PACK_ROLES
        if isinstance(packs.get(role), dict)
    }


def _adb_summary(packs: dict[str, Any]) -> dict[str, Any]:
    return {
        role: (packs.get(role) or {}).get("adb", {})
        for role in PACK_ROLES
        if isinstance(packs.get(role), dict)
    }


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _print_text_report(plan: dict[str, Any]) -> None:
    print(f"{plan['current_gate_label']} ({plan['status']})")
    print("rehearsal_steps:")
    for step in plan["rehearsal_steps"]:
        print(f"- {step['id']}: {step['action']}")
    print("fallback_trigger_points:")
    for trigger in plan["fallback_trigger_points"]:
        print(f"- {trigger['trigger']} -> {trigger['action']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evaluation-json", type=Path, help="Path to evaluate_mocopi_evidence_pack.py JSON output")
    parser.add_argument("--body-baseline", type=Path, help="BODY fallback baseline snapshot folder")
    parser.add_argument("--mocopi-candidate", type=Path, help="MOCOPI candidate snapshot folder")
    parser.add_argument("--fallback-recovery", type=Path, help="fallback recovery snapshot folder")
    parser.add_argument("--code", default="3601", help="Expected recall code when evaluating packs, default: 3601")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"Write plan JSON, default: {DEFAULT_OUT}")
    parser.add_argument("--report-json", action="store_true", help="Emit the plan JSON to stdout")
    args = parser.parse_args(argv)

    try:
        evaluation = load_or_evaluate(args)
    except ValueError as exc:
        parser.error(str(exc))

    plan = export_mocopi_rehearsal_plan(evaluation)
    if args.out:
        _write_json(args.out, plan)
    if args.report_json:
        json.dump(plan, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        _print_text_report(plan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

