"""Validate whether an external GCP/Cloud Run service may be used for exhibition.

The gate consumes already-generated JSON reports. It never calls GCP or live
HTTP itself. The intent is to keep the external PC local fallback as the
required visitor baseline, while allowing a GCP service lane only when its
contracts and smoke evidence are strong enough.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CONTRACT_VERSION = "exhibition-service-gate.v1"
PHASE0_CONTRACT_VERSION = "gcp-phase0-service-contract.v1"
SERVICE_CONTRACT_VERSION = "service-deployment-contract.v1"
LOCAL_SMOKE_CONTRACT_VERSION = "exhibition-local-preflight.v1"
GATE_GO = "GO"
GATE_DEMO_ONLY = "DEMO-ONLY"
GATE_NO_GO = "NO-GO"


def validate_exhibition_service_gate(
    gcp_phase0_contract: str | Path | dict[str, Any],
    service_deployment_contract: str | Path | dict[str, Any],
    *,
    exhibition_smoke_report: str | Path | dict[str, Any] | None = None,
    strict: bool = False,
) -> dict[str, Any]:
    phase0, phase0_path = _load_json(gcp_phase0_contract)
    service, service_path = _load_json(service_deployment_contract)
    smoke, smoke_path = _load_optional_json(exhibition_smoke_report)
    mode = _mode(phase0, service)
    blockers: list[dict[str, str]] = []

    _validate_contract_versions(phase0, service, blockers)
    _validate_service_contract(mode, service, blockers)
    _validate_phase0_contract(mode, phase0, blockers)
    if mode == "external":
        _validate_external_http_reachability(service, blockers)
        _validate_external_smoke(smoke, blockers)

    no_go_blockers = [blocker for blocker in blockers if blocker["severity"] == "no_go"]
    demo_blockers = [blocker for blocker in blockers if blocker["severity"] == "demo_only"]
    if mode == "local" and not no_go_blockers and not demo_blockers:
        gate_status = GATE_GO
    elif no_go_blockers or (strict and demo_blockers):
        gate_status = GATE_NO_GO
    elif demo_blockers:
        gate_status = GATE_DEMO_ONLY
    else:
        gate_status = GATE_GO

    allowed_runtime_mode = _allowed_runtime_mode(mode, gate_status, smoke)
    return {
        "contract_version": CONTRACT_VERSION,
        "ok": gate_status == GATE_GO,
        "gate_status": gate_status,
        "strict": bool(strict),
        "mode": mode,
        "allowed_runtime_mode": allowed_runtime_mode,
        "local_fallback_required": True,
        "external_service_blockers": blockers,
        "operator_decision_summary": _operator_decision_summary(
            mode=mode,
            gate_status=gate_status,
            allowed_runtime_mode=allowed_runtime_mode,
            blockers=blockers,
        ),
        "inputs": {
            "gcp_phase0_contract": phase0_path,
            "service_deployment_contract": service_path,
            "exhibition_smoke_report": smoke_path,
        },
        "generated_at": _now_iso(),
    }


def _validate_contract_versions(
    phase0: dict[str, Any],
    service: dict[str, Any],
    blockers: list[dict[str, str]],
) -> None:
    if phase0.get("contract_version") != PHASE0_CONTRACT_VERSION:
        _block(blockers, "phase0_contract_version", "no_go", "GCP phase0 contract version is missing or unsupported.")
    if service.get("contract_version") != SERVICE_CONTRACT_VERSION:
        _block(blockers, "service_contract_version", "no_go", "Service deployment contract version is missing or unsupported.")


def _validate_service_contract(mode: str, service: dict[str, Any], blockers: list[dict[str, str]]) -> None:
    service_mode = str(service.get("mode") or "").strip().lower()
    if service_mode != mode:
        _block(blockers, "service_contract_mode", "no_go", f"Service contract mode {service_mode!r} does not match gate mode {mode!r}.")
    if service.get("ok") is not True:
        reasons = "; ".join(str(reason) for reason in service.get("reasons", [])) or "service contract ok=false"
        _block(blockers, "service_deployment_contract", "no_go", reasons)
    if mode == "external":
        for name in ("web", "api", "quest"):
            report = service.get("urls", {}).get(name) if isinstance(service.get("urls"), dict) else {}
            if not isinstance(report, dict):
                _block(blockers, f"{name}_url_report", "no_go", f"Missing service URL report for {name}.")
                continue
            if report.get("scheme") != "https":
                _block(blockers, f"{name}_https", "no_go", f"External {name} URL must use HTTPS.")
            if report.get("is_loopback") or report.get("is_private_lan") or report.get("is_private_name"):
                _block(blockers, f"{name}_public_url", "no_go", f"External {name} URL must be public, not localhost/private LAN.")


def _validate_phase0_contract(mode: str, phase0: dict[str, Any], blockers: list[dict[str, str]]) -> None:
    phase0_mode = str(phase0.get("mode") or "").strip().lower()
    if phase0_mode != mode:
        _block(blockers, "phase0_contract_mode", "no_go", f"Phase0 contract mode {phase0_mode!r} does not match gate mode {mode!r}.")
    if phase0.get("ok") is not True:
        _block(blockers, "phase0_contract", "no_go", "GCP phase0 service contract is not passing.")
    if mode == "external":
        for blocker in phase0.get("blocked_until", []):
            if not isinstance(blocker, dict):
                continue
            gate = str(blocker.get("gate") or "phase0_blocked_until")
            detail = str(blocker.get("detail") or "Phase0 contract still has an unresolved promotion gate.")
            _block(blockers, gate, "demo_only", detail)


def _validate_external_http_reachability(service: dict[str, Any], blockers: list[dict[str, str]]) -> None:
    http = service.get("http") if isinstance(service.get("http"), dict) else {}
    if http.get("requested") is not True:
        _block(
            blockers,
            "external_http_check_not_requested",
            "demo_only",
            "Run validate_service_deployment_contract.py with --check-http before using the service for visitors.",
        )
        return
    if http.get("ok") is not True:
        _block(blockers, "external_http_check_failed", "no_go", "External Web/API/Quest HTTP checks did not all pass.")
    checks = http.get("checks") if isinstance(http.get("checks"), list) else []
    if not checks:
        _block(blockers, "external_http_check_empty", "no_go", "HTTP check report has no checks.")
        return
    required = {"api_health", "web_forge", "quest_viewer"}
    present = {str(check.get("name")) for check in checks if isinstance(check, dict)}
    missing = sorted(required - present)
    if missing:
        _block(blockers, "external_http_check_missing_routes", "no_go", "Missing HTTP check(s): " + ", ".join(missing))
    for check in checks:
        if isinstance(check, dict) and check.get("ok") is not True:
            name = str(check.get("name") or "unknown")
            error = str(check.get("error") or "not ok")
            _block(blockers, f"external_http_{name}", "no_go", error)


def _validate_external_smoke(smoke: dict[str, Any] | None, blockers: list[dict[str, str]]) -> None:
    if smoke is None:
        _block(
            blockers,
            "external_pc_local_smoke_missing",
            "demo_only",
            "No exhibition smoke report was supplied; local-pass prerequisite is not evidenced.",
        )
        return
    preflight = smoke.get("preflight_gate") if isinstance(smoke.get("preflight_gate"), dict) else {}
    if preflight.get("contract_version") not in {LOCAL_SMOKE_CONTRACT_VERSION, None}:
        _block(blockers, "local_smoke_contract_version", "demo_only", "Unexpected local preflight contract version.")
    if preflight.get("operator_label") != "local-pass" or preflight.get("status") != "pass":
        _block(blockers, "external_pc_local_pass", "no_go", "External PC local fallback smoke must be local-pass.")
    service_label = (
        smoke.get("optional_enhancement_lanes", {}).get("gcp_service")
        if isinstance(smoke.get("optional_enhancement_lanes"), dict)
        else None
    )
    service_report = (
        smoke.get("optional_lane_reports", {}).get("gcp_service")
        if isinstance(smoke.get("optional_lane_reports"), dict)
        else None
    )
    if service_label == "service-fail":
        _block(blockers, "gcp_service_smoke", "no_go", "Exhibition smoke reported service-fail.")
    elif service_label != "service-pass" or not isinstance(service_report, dict):
        _block(
            blockers,
            "gcp_service_smoke_missing",
            "demo_only",
            "No service-pass optional lane smoke evidence was supplied.",
        )
    elif service_report.get("ok") is not True:
        _block(blockers, "gcp_service_smoke_report", "no_go", "GCP service optional lane report is not ok.")


def _allowed_runtime_mode(mode: str, gate_status: str, smoke: dict[str, Any] | None) -> str:
    if mode == "local":
        return "local_fallback"
    if gate_status == GATE_GO:
        return "external_service_with_local_fallback"
    if _smoke_local_failed(smoke):
        return "none_until_local_pass"
    if gate_status == GATE_DEMO_ONLY:
        return "local_fallback_with_external_service_demo_only"
    return "local_fallback_only"


def _operator_decision_summary(
    *,
    mode: str,
    gate_status: str,
    allowed_runtime_mode: str,
    blockers: list[dict[str, str]],
) -> dict[str, Any]:
    if mode == "local":
        decision = "Use the exhibition PC local fallback as the visitor path."
    elif gate_status == GATE_GO:
        decision = "External service may be rehearsed for visitors, while keeping local fallback ready."
    elif gate_status == GATE_DEMO_ONLY:
        decision = "External service is demo-only; use local fallback for visitors."
    else:
        decision = "Do not use the external service; use local fallback only, or stop if local-pass is missing."
    return {
        "label": gate_status,
        "decision": decision,
        "allowed_runtime_mode": allowed_runtime_mode,
        "local_fallback_rule": "local-pass cannot be overridden by service, PlayCanvas, or mocopi lanes.",
        "next_action": _next_action(gate_status, blockers),
    }


def _next_action(gate_status: str, blockers: list[dict[str, str]]) -> str:
    if gate_status == GATE_GO:
        return "Keep local fallback running and record the service gate JSON with show evidence."
    if not blockers:
        return "Re-run gate with service contract and smoke reports."
    first = blockers[0]
    return f"Resolve {first['gate']}: {first['detail']}"


def _smoke_local_failed(smoke: dict[str, Any] | None) -> bool:
    if smoke is None:
        return False
    preflight = smoke.get("preflight_gate") if isinstance(smoke.get("preflight_gate"), dict) else {}
    return bool(preflight) and preflight.get("operator_label") != "local-pass"


def _mode(phase0: dict[str, Any], service: dict[str, Any]) -> str:
    for payload in (phase0, service):
        mode = str(payload.get("mode") or "").strip().lower()
        if mode in {"local", "external"}:
            return mode
    return "external"


def _block(blockers: list[dict[str, str]], gate: str, severity: str, detail: str) -> None:
    blockers.append({"gate": gate, "severity": severity, "detail": detail})


def _load_optional_json(value: str | Path | dict[str, Any] | None) -> tuple[dict[str, Any] | None, str | None]:
    if value is None:
        return None, None
    payload, path = _load_json(value)
    return payload, path


def _load_json(value: str | Path | dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    if isinstance(value, dict):
        return value, None
    path = Path(value)
    payload = _read_json_file(path)
    if not isinstance(payload, dict):
        raise ValueError(f"JSON input must be an object: {path}")
    return payload, path.as_posix()


def _read_json_file(path: Path) -> Any:
    raw = path.read_bytes()
    errors: list[str] = []
    for encoding in ("utf-8-sig", "utf-16"):
        try:
            return json.loads(raw.decode(encoding))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            errors.append(f"{encoding}: {exc}")
    raise ValueError(f"JSON input is not valid UTF-8/UTF-16 JSON: {path}: {'; '.join(errors)}")


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _print_text_report(result: dict[str, Any]) -> None:
    print(f"[{result['gate_status']}] allowed_runtime_mode={result['allowed_runtime_mode']}")
    print(result["operator_decision_summary"]["decision"])
    for blocker in result["external_service_blockers"]:
        print(f"  {blocker['severity']}  {blocker['gate']}: {blocker['detail']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("gcp_phase0_contract", type=Path)
    parser.add_argument("service_deployment_contract", type=Path)
    parser.add_argument("--exhibition-smoke-report", type=Path)
    parser.add_argument("--strict", action="store_true", help="Treat DEMO-ONLY blockers as NO-GO.")
    parser.add_argument("--report-json", action="store_true")
    args = parser.parse_args(argv)

    result = validate_exhibition_service_gate(
        args.gcp_phase0_contract,
        args.service_deployment_contract,
        exhibition_smoke_report=args.exhibition_smoke_report,
        strict=args.strict,
    )
    if args.report_json:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        _print_text_report(result)
    if result["gate_status"] == GATE_NO_GO:
        return 1
    if args.strict and result["gate_status"] != GATE_GO:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
