from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "validate_exhibition_service_gate.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("validate_exhibition_service_gate", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["validate_exhibition_service_gate"] = module
    spec.loader.exec_module(module)
    return module


tool = _load_tool()


def _phase0_contract(*, mode: str = "local", ok: bool = True, blocked_until: list[dict] | None = None) -> dict:
    return {
        "contract_version": "gcp-phase0-service-contract.v1",
        "ok": ok,
        "status": "pass" if ok else "fail",
        "mode": mode,
        "phase0_promotion_status": "ready" if not blocked_until else "blocked",
        "blocked_until": blocked_until or [],
        "public_urls": {},
        "api_endpoints": [],
        "storage_future_mapping": [],
    }


def _url_report(url: str, *, https: bool = True, public: bool = True) -> dict:
    scheme = "https" if https else "http"
    host = url.split("://", 1)[1].split("/", 1)[0].split(":", 1)[0]
    return {
        "raw": url,
        "url": url.rstrip("/"),
        "scheme": scheme,
        "host": host,
        "port": None,
        "origin": url.rstrip("/"),
        "is_loopback": not public,
        "is_private_lan": False,
        "is_private_name": False,
    }


def _service_contract(
    *,
    mode: str = "local",
    ok: bool = True,
    http_requested: bool = False,
    http_ok: bool | None = None,
    https: bool = True,
    public: bool = True,
) -> dict:
    if mode == "local":
        urls = {
            "web": _url_report("http://127.0.0.1:8010", https=False, public=False),
            "api": _url_report("http://127.0.0.1:8010", https=False, public=False),
            "quest": _url_report("http://localhost:5173", https=False, public=False),
        }
    else:
        urls = {
            "web": _url_report("https://web.example.com", https=https, public=public),
            "api": _url_report("https://api.example.com", https=https, public=public),
            "quest": _url_report("https://quest.example.com", https=https, public=public),
        }
    http = {"requested": http_requested, "checks": []}
    if http_requested:
        http["ok"] = bool(http_ok)
        http["checks"] = [
            {"name": "api_health", "url": urls["api"]["url"] + "/health", "ok": bool(http_ok), "error": "" if http_ok else "down"},
            {"name": "web_forge", "url": urls["web"]["url"] + "/viewer/armor-forge/", "ok": bool(http_ok), "error": "" if http_ok else "down"},
            {"name": "quest_viewer", "url": urls["quest"]["url"] + "/viewer/quest-iw-demo/", "ok": bool(http_ok), "error": "" if http_ok else "down"},
        ]
    return {
        "contract_version": "service-deployment-contract.v1",
        "ok": ok,
        "status": "pass" if ok else "fail",
        "mode": mode,
        "urls": urls,
        "http": http,
        "reasons": [] if ok else ["contract failed"],
        "warnings": [],
    }


def _smoke_report(*, local_pass: bool = True, service_label: str = "service-pass") -> dict:
    return {
        "ok": local_pass,
        "preflight_gate": {
            "contract_version": "exhibition-local-preflight.v1",
            "status": "pass" if local_pass else "fail",
            "operator_label": "local-pass" if local_pass else "local-fail",
        },
        "optional_enhancement_lanes": {"gcp_service": service_label},
        "optional_lane_reports": {
            "gcp_service": {
                "ok": service_label == "service-pass",
                "status_label": service_label,
            }
        },
    }


def _write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def test_local_mode_passes_as_local_fallback() -> None:
    result = tool.validate_exhibition_service_gate(_phase0_contract(), _service_contract())

    assert result["gate_status"] == "GO"
    assert result["ok"] is True
    assert result["allowed_runtime_mode"] == "local_fallback"
    assert result["local_fallback_required"] is True
    assert result["external_service_blockers"] == []
    assert "local fallback" in result["operator_decision_summary"]["decision"]


def test_external_service_can_go_when_contract_http_and_smoke_are_all_green() -> None:
    result = tool.validate_exhibition_service_gate(
        _phase0_contract(mode="external"),
        _service_contract(mode="external", http_requested=True, http_ok=True),
        exhibition_smoke_report=_smoke_report(),
    )

    assert result["gate_status"] == "GO"
    assert result["allowed_runtime_mode"] == "external_service_with_local_fallback"
    assert result["external_service_blockers"] == []


def test_external_without_http_or_smoke_is_demo_only_unless_strict() -> None:
    result = tool.validate_exhibition_service_gate(
        _phase0_contract(mode="external"),
        _service_contract(mode="external", http_requested=False),
    )
    strict_result = tool.validate_exhibition_service_gate(
        _phase0_contract(mode="external"),
        _service_contract(mode="external", http_requested=False),
        strict=True,
    )

    assert result["gate_status"] == "DEMO-ONLY"
    assert result["allowed_runtime_mode"] == "local_fallback_with_external_service_demo_only"
    assert {blocker["gate"] for blocker in result["external_service_blockers"]} == {
        "external_http_check_not_requested",
        "external_pc_local_smoke_missing",
    }
    assert strict_result["gate_status"] == "NO-GO"


def test_external_http_failure_is_no_go() -> None:
    result = tool.validate_exhibition_service_gate(
        _phase0_contract(mode="external"),
        _service_contract(mode="external", http_requested=True, http_ok=False),
        exhibition_smoke_report=_smoke_report(),
    )

    assert result["gate_status"] == "NO-GO"
    assert result["allowed_runtime_mode"] == "local_fallback_only"
    assert any(blocker["gate"] == "external_http_check_failed" for blocker in result["external_service_blockers"])


def test_external_local_smoke_failure_blocks_all_public_runtime() -> None:
    result = tool.validate_exhibition_service_gate(
        _phase0_contract(mode="external"),
        _service_contract(mode="external", http_requested=True, http_ok=True),
        exhibition_smoke_report=_smoke_report(local_pass=False),
    )

    assert result["gate_status"] == "NO-GO"
    assert result["allowed_runtime_mode"] == "none_until_local_pass"
    assert any(blocker["gate"] == "external_pc_local_pass" for blocker in result["external_service_blockers"])


def test_phase0_blocked_until_keeps_external_service_demo_only() -> None:
    result = tool.validate_exhibition_service_gate(
        _phase0_contract(
            mode="external",
            blocked_until=[{"gate": "cloud_sql_schema_written", "detail": "schema not written"}],
        ),
        _service_contract(mode="external", http_requested=True, http_ok=True),
        exhibition_smoke_report=_smoke_report(),
    )

    assert result["gate_status"] == "DEMO-ONLY"
    assert any(blocker["gate"] == "cloud_sql_schema_written" for blocker in result["external_service_blockers"])


def test_cli_report_json_and_strict_exit_code(tmp_path: Path) -> None:
    phase0_path = _write_json(tmp_path / "phase0.json", _phase0_contract(mode="external"))
    service_path = _write_json(tmp_path / "service.json", _service_contract(mode="external", http_requested=False))

    completed = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            str(phase0_path),
            str(service_path),
            "--strict",
            "--report-json",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)

    assert completed.returncode == 1
    assert result["gate_status"] == "NO-GO"
    assert result["strict"] is True
    assert result["inputs"]["gcp_phase0_contract"] == phase0_path.as_posix()


def test_cli_accepts_powershell_utf16_redirected_json(tmp_path: Path) -> None:
    phase0_path = _write_json(tmp_path / "phase0.json", _phase0_contract())
    service_path = tmp_path / "service-utf16.json"
    service_path.write_text(json.dumps(_service_contract(), ensure_ascii=False), encoding="utf-16")

    completed = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            str(phase0_path),
            str(service_path),
            "--report-json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)

    assert result["gate_status"] == "GO"
    assert result["inputs"]["service_deployment_contract"] == service_path.as_posix()
