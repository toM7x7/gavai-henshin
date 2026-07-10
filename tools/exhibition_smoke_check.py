"""Exhibition PC smoke check for Web Forge and Quest recall.

This script assumes the Web/API server and Quest Vite server are already
running. It can optionally forge a fresh suit code, then checks that recall
returns a self-contained runtime placement contract.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from typing import Any, Iterable


DEFAULT_API_BASE = "http://127.0.0.1:8010"
DEFAULT_QUEST_BASE = "http://127.0.0.1:5173"
WINDOWS_ABSOLUTE_PATH_RE = re.compile(r"^[A-Za-z]:[\\/]")
LOCAL_PREFLIGHT_CONTRACT_VERSION = "exhibition-local-preflight.v1"
OPTIONAL_LANE_DEFAULTS = {
    "gcp_service": "not-included",
    "playcanvas": "not-included",
    "mocopi": "not-included",
}
SERVICE_LANE_PASS = "service-pass"
SERVICE_LANE_FAIL = "service-fail"
REQUIRED_REVERSE_PORTS = (5173, 8010)


def _get_json(url: str, *, timeout: float) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON response must be an object: {url}")
    return payload


def _get_text_status(url: str, *, timeout: float) -> int:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        response.read(256)
        return int(response.status)


def _post_json(url: str, payload: dict[str, Any], *, timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = json.loads(response.read().decode("utf-8"))
    if not isinstance(body, dict):
        raise ValueError(f"JSON response must be an object: {url}")
    return body


def _quest_url_for_code(code: str) -> str:
    suffix = f"&code={code}" if code else ""
    return f"http://localhost:5173/viewer/quest-iw-demo/?newRoute=1{suffix}"


def _operator_urls(code: str) -> dict[str, str]:
    return {
        "web_forge": f"{DEFAULT_API_BASE}/viewer/armor-forge/",
        "web_forge_exhibition": f"{DEFAULT_API_BASE}/viewer/armor-forge/?mode=exhibition",
        "quest_usb_adb": _quest_url_for_code(code),
        "quest_manual_entry_usb_adb": "http://localhost:5173/viewer/quest-iw-demo/?newRoute=1",
    }


def _parse_adb_devices_output(output: str) -> list[dict[str, str]]:
    devices = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line or line.lower().startswith("list of devices"):
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        devices.append(
            {
                "serial": parts[0],
                "state": parts[1],
                "details": " ".join(parts[2:]),
            }
        )
    return devices


def _parse_adb_reverse_output(output: str) -> list[dict[str, str]]:
    mappings = []
    for raw_line in output.splitlines():
        parts = raw_line.strip().split()
        if len(parts) < 3:
            continue
        local = parts[-2]
        remote = parts[-1]
        mappings.append(
            {
                "transport": " ".join(parts[:-2]),
                "local": local,
                "remote": remote,
            }
        )
    return mappings


def _adb_reverse_report(adb_path: str, *, timeout: float) -> dict[str, Any]:
    report: dict[str, Any] = {
        "requested": True,
        "adb_path": adb_path,
        "device_count": 0,
        "ready_device_count": 0,
        "ready": False,
        "required_reverse_ports": list(REQUIRED_REVERSE_PORTS),
        "reverse_ports_present": [],
        "missing_reverse_ports": list(REQUIRED_REVERSE_PORTS),
        "errors": [],
    }
    try:
        devices_proc = subprocess.run(
            [adb_path, "devices", "-l"],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        report["errors"].append(f"adb devices failed: {exc}")
        return report

    report["devices_stdout"] = devices_proc.stdout
    report["devices_stderr"] = devices_proc.stderr
    if devices_proc.returncode != 0:
        report["errors"].append(f"adb devices returned {devices_proc.returncode}")
        return report

    devices = _parse_adb_devices_output(devices_proc.stdout)
    ready_devices = [device for device in devices if device["state"] == "device"]
    report["devices"] = devices
    report["device_count"] = len(devices)
    report["ready_device_count"] = len(ready_devices)
    if not ready_devices:
        report["errors"].append("adb has no ready Quest/device state")
        return report

    try:
        reverse_proc = subprocess.run(
            [adb_path, "reverse", "--list"],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        report["errors"].append(f"adb reverse --list failed: {exc}")
        return report

    report["reverse_stdout"] = reverse_proc.stdout
    report["reverse_stderr"] = reverse_proc.stderr
    if reverse_proc.returncode != 0:
        report["errors"].append(f"adb reverse --list returned {reverse_proc.returncode}")
        return report

    mappings = _parse_adb_reverse_output(reverse_proc.stdout)
    present_ports = sorted(
        {
            port
            for mapping in mappings
            for port in REQUIRED_REVERSE_PORTS
            if mapping["local"] == f"tcp:{port}" and mapping["remote"] == f"tcp:{port}"
        }
    )
    missing_ports = [port for port in REQUIRED_REVERSE_PORTS if port not in present_ports]
    report["reverse_mappings"] = mappings
    report["reverse_ports_present"] = present_ports
    report["missing_reverse_ports"] = missing_ports
    if missing_ports:
        report["errors"].append(
            "adb reverse is missing required port(s): " + ", ".join(str(port) for port in missing_ports)
        )
    report["ready"] = not report["errors"]
    return report


def _forge_payload() -> dict[str, Any]:
    return {
        "display_name": "Exhibition Smoke",
        "height_cm": 172,
        "archetype": "city",
        "temperament": "steady",
        "brief": (
            "Exhibition smoke suit. Web establishes the suit, Quest verifies the "
            "transformation, Replay records the experience."
        ),
    }


def _iter_string_values(value: Any, *, path: str = "$") -> Iterable[tuple[str, str]]:
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _iter_string_values(child, path=f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _iter_string_values(child, path=f"{path}[{index}]")
    elif isinstance(value, str):
        yield path, value


def _unsafe_public_ref(value: str) -> bool:
    stripped = value.strip()
    normalized = stripped.replace("\\", "/").lower()
    return (
        WINDOWS_ABSOLUTE_PATH_RE.match(stripped) is not None
        or normalized.startswith("file://")
        or "c:/dev/codex/gavai-henshin" in normalized
        or "c:/henshin-demo/gavai-henshin" in normalized
    )


def _public_ref_violations(payload: dict[str, Any]) -> list[dict[str, str]]:
    violations = []
    for path, value in _iter_string_values(payload):
        if _unsafe_public_ref(value):
            violations.append({"path": path, "value": value})
    return violations


def _recall_contract_report(api_base: str, code: str, *, timeout: float) -> dict[str, Any]:
    errors: list[str] = []
    report: dict[str, Any] = {
        "api_base": api_base,
        "code": code,
    }

    if not code:
        errors.append("No recall code supplied. Use --forge, --code 1234, --service-forge, or --service-code 1234.")
    elif len(code) != 4:
        errors.append(f"Recall code must be 4 characters: {code!r}")

    if errors:
        report["ok"] = False
        report["errors"] = errors
        return report

    try:
        recall = _get_json(f"{api_base}/v1/quest/recall/{code}", timeout=timeout)
    except (OSError, ValueError, urllib.error.URLError, json.JSONDecodeError) as exc:
        errors.append(f"Recall failed: {exc}")
        report["ok"] = False
        report["errors"] = errors
        return report

    runtime = recall.get("runtime_package") if isinstance(recall.get("runtime_package"), dict) else {}
    placements = runtime.get("render_placements") if isinstance(runtime.get("render_placements"), dict) else {}
    checks = runtime.get("runtime_checks") if isinstance(runtime.get("runtime_checks"), dict) else {}
    assets = (
        runtime.get("visual_layers", {})
        .get("armor_overlay", {})
        .get("assets", {})
        if isinstance(runtime.get("visual_layers"), dict)
        else {}
    )
    missing_selected = [
        part
        for part, placement in placements.items()
        if isinstance(placement, dict) and not placement.get("selected_variant_key")
    ]
    selected_mismatches = [
        part
        for part, placement in placements.items()
        if isinstance(placement, dict)
        and isinstance(assets.get(part), dict)
        and placement.get("selected_variant_key") != assets[part].get("selected_variant_key")
    ]

    runtime_contract = runtime.get("render_contract", {}).get("render_placement_contract")
    unsafe_refs = _public_ref_violations(recall)
    report.update(
        {
            "recall_status": recall.get("status"),
            "suit_id": recall.get("suit_id"),
            "runtime_contract": runtime_contract,
            "render_placement_count": len(placements),
            "missing_selected_variant_key_count": len(missing_selected),
            "selected_variant_mismatch_count": len(selected_mismatches),
            "runtime_surface_failure_count": checks.get("runtime_surface_failure_count"),
            "invalid_overlay_parts": checks.get("invalid_overlay_parts"),
            "unsafe_public_ref_count": len(unsafe_refs),
            "unsafe_public_refs": unsafe_refs,
        }
    )

    if runtime_contract != "runtime-render-placement.v1":
        errors.append("Recall runtime contract is not runtime-render-placement.v1")
    if len(placements) < 18:
        errors.append(f"Expected at least 18 render placements, got {len(placements)}")
    if missing_selected:
        errors.append(f"Missing selected_variant_key: {', '.join(missing_selected)}")
    if selected_mismatches:
        errors.append(f"Selected variant mismatches: {', '.join(selected_mismatches)}")
    if checks.get("runtime_surface_failure_count") not in (0, None):
        errors.append("Runtime surface gate reported failures")
    if unsafe_refs:
        errors.append("Recall payload contains machine-local absolute path or file:// reference")

    report["ok"] = not errors
    report["errors"] = errors
    return report


def _local_preflight_gate(result: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    adb_required = result.get("adb_reverse_required") is True
    checks = {
        "api_health_ok": result.get("api_health", {}).get("ok") is True,
        "quest_page_ok": isinstance(result.get("quest_http_status"), int)
        and 200 <= int(result["quest_http_status"]) < 400,
        "fresh_or_supplied_code": len(str(result.get("code") or "").strip()) == 4,
        "runtime_contract_ok": result.get("runtime_contract") == "runtime-render-placement.v1",
        "render_placement_count_ok": int(result.get("render_placement_count") or 0) >= 18,
        "selected_variants_ok": result.get("missing_selected_variant_key_count") == 0
        and result.get("selected_variant_mismatch_count") == 0,
        "runtime_surface_ok": result.get("runtime_surface_failure_count") in (0, None),
        "portable_public_refs_ok": result.get("unsafe_public_ref_count") == 0,
        "adb_reverse_ok": not adb_required or result.get("adb_reverse", {}).get("ready") is True,
    }
    return {
        "contract_version": LOCAL_PREFLIGHT_CONTRACT_VERSION,
        "required_lane": "external_pc_local",
        "status": "pass" if not errors and all(checks.values()) else "fail",
        "operator_label": "local-pass" if not errors and all(checks.values()) else "local-fail",
        "checks": checks,
        "optional_enhancement_lanes": dict(result.get("optional_enhancement_lanes") or OPTIONAL_LANE_DEFAULTS),
        "adb_reverse_required": adb_required,
        "promotion_rule": (
            "GCP service, PlayCanvas, and mocopi may be rehearsed only as optional lanes; "
            "none can override local-fail for public visitor operation."
        ),
    }


def run_check(args: argparse.Namespace) -> tuple[int, dict[str, Any]]:
    errors: list[str] = []
    result: dict[str, Any] = {
        "api_base": args.api_base,
        "quest_base": args.quest_base,
        "code": args.code or "",
        "required_preflight": "external_pc_local",
        "optional_enhancement_lanes": dict(OPTIONAL_LANE_DEFAULTS),
        "optional_lane_reports": {},
        "adb_reverse_required": bool(args.require_adb_reverse),
    }

    try:
        health = _get_json(f"{args.api_base}/api/health", timeout=args.timeout)
        result["api_health"] = health
        if health.get("ok") is not True:
            errors.append("API health did not return ok=true")
    except (OSError, ValueError, urllib.error.URLError, json.JSONDecodeError) as exc:
        errors.append(f"API health failed: {exc}")

    quest_url = f"{args.quest_base}/viewer/quest-iw-demo/?newRoute=1"
    try:
        result["quest_http_status"] = _get_text_status(quest_url, timeout=args.timeout)
    except (OSError, urllib.error.URLError) as exc:
        errors.append(f"Quest page failed: {exc}")

    if args.forge:
        try:
            forged = _post_json(f"{args.api_base}/v1/suits/forge", _forge_payload(), timeout=args.timeout)
            result["forge_status"] = forged.get("status")
            result["code"] = str(forged.get("recall_code") or "")
            if len(result["code"]) != 4:
                errors.append(f"Forge did not return a 4-character code: {result['code']!r}")
        except (OSError, ValueError, urllib.error.URLError, json.JSONDecodeError) as exc:
                errors.append(f"Forge failed: {exc}")

    code = str(result.get("code") or "").strip()
    result["operator_urls"] = _operator_urls(code)
    if not code:
        errors.append("No recall code supplied. Use --forge or --code 1234.")
    elif len(code) != 4:
        errors.append(f"Recall code must be 4 characters: {code!r}")
    else:
        recall_report = _recall_contract_report(args.api_base, code, timeout=args.timeout)
        for key, value in recall_report.items():
            if key not in {"api_base", "code", "ok", "errors"}:
                result[key] = value
        errors.extend(str(error) for error in recall_report.get("errors", []))

    if args.service_api_base:
        service_report = _service_lane_report(args, fallback_code=code)
        result["optional_lane_reports"]["gcp_service"] = service_report
        result["optional_enhancement_lanes"]["gcp_service"] = (
            SERVICE_LANE_PASS if service_report.get("ok") is True else SERVICE_LANE_FAIL
        )

    if args.require_adb_reverse:
        adb_report = _adb_reverse_report(args.adb_path, timeout=args.timeout)
        result["adb_reverse"] = adb_report
        if not adb_report.get("ready"):
            errors.append("ADB reverse preflight failed: " + "; ".join(adb_report.get("errors", [])))

    result["preflight_gate"] = _local_preflight_gate(result, errors)
    result["ok"] = not errors and result["preflight_gate"]["status"] == "pass"
    result["errors"] = errors
    return (0 if not errors else 1, result)


def _service_lane_report(args: argparse.Namespace, *, fallback_code: str) -> dict[str, Any]:
    errors: list[str] = []
    code = str(args.service_code or fallback_code or "").strip()
    report: dict[str, Any] = {
        "lane": "gcp_service",
        "api_base": args.service_api_base,
        "code": code,
        "forge_requested": bool(args.service_forge),
        "status_label": SERVICE_LANE_FAIL,
    }

    try:
        health = _get_json(f"{args.service_api_base}/api/health", timeout=args.timeout)
        report["api_health"] = health
        if health.get("ok") is not True:
            errors.append("Service API health did not return ok=true")
    except (OSError, ValueError, urllib.error.URLError, json.JSONDecodeError) as exc:
        errors.append(f"Service API health failed: {exc}")

    if args.service_forge:
        try:
            forged = _post_json(f"{args.service_api_base}/v1/suits/forge", _forge_payload(), timeout=args.timeout)
            report["forge_status"] = forged.get("status")
            code = str(forged.get("recall_code") or "").strip()
            report["code"] = code
            if len(code) != 4:
                errors.append(f"Service forge did not return a 4-character code: {code!r}")
        except (OSError, ValueError, urllib.error.URLError, json.JSONDecodeError) as exc:
            errors.append(f"Service forge failed: {exc}")

    recall_report = _recall_contract_report(args.service_api_base, code, timeout=args.timeout)
    report["recall_contract"] = recall_report
    errors.extend(str(error) for error in recall_report.get("errors", []))

    report["ok"] = not errors
    report["status_label"] = SERVICE_LANE_PASS if report["ok"] else SERVICE_LANE_FAIL
    report["errors"] = errors
    return report


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-base", default=DEFAULT_API_BASE)
    parser.add_argument("--quest-base", default=DEFAULT_QUEST_BASE)
    parser.add_argument("--code", default="")
    parser.add_argument("--forge", action="store_true", help="Create a fresh smoke suit before recall.")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument(
        "--service-api-base",
        default="",
        help=(
            "Optional GCP/hosted service API base URL. This lane reports "
            "service-pass/service-fail and never overrides local-pass/local-fail."
        ),
    )
    parser.add_argument("--service-code", default="", help="Recall code to test against --service-api-base.")
    parser.add_argument(
        "--service-forge",
        action="store_true",
        help="Forge a fresh suit against --service-api-base before service recall.",
    )
    parser.add_argument(
        "--require-adb-reverse",
        action="store_true",
        help="Require a ready adb device and tcp:5173/tcp:8010 reverse mappings for show-floor local-pass.",
    )
    parser.add_argument("--adb-path", default="adb")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    exit_code, result = run_check(parse_args(list(argv or sys.argv[1:])))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
