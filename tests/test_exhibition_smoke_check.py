from __future__ import annotations

import importlib.util
import sys
import urllib.error
from pathlib import Path
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "exhibition_smoke_check.py"


def _load_smoke_check():
    spec = importlib.util.spec_from_file_location("exhibition_smoke_check", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["exhibition_smoke_check"] = module
    spec.loader.exec_module(module)
    return module


smoke_check = _load_smoke_check()


def _recall_payload(*, local_path: str | None = None) -> dict:
    placements = {
        f"part_{index:02d}": {
            "selected_variant_key": f"variant_{index:02d}",
            "asset_ref": f"viewer/assets/armor-parts/part_{index:02d}/part_{index:02d}.glb",
        }
        for index in range(18)
    }
    assets = {
        part: {
            "selected_variant_key": placement["selected_variant_key"],
            "asset_ref": placement["asset_ref"],
        }
        for part, placement in placements.items()
    }
    payload = {
        "status": "READY",
        "suit_id": "VDA-SERVICE-SMOKE",
        "runtime_package": {
            "render_contract": {"render_placement_contract": "runtime-render-placement.v1"},
            "render_placements": placements,
            "runtime_checks": {
                "runtime_surface_failure_count": 0,
                "invalid_overlay_parts": [],
            },
            "visual_layers": {"armor_overlay": {"assets": assets}},
        },
    }
    if local_path:
        payload["runtime_package"]["debug_path"] = local_path
    return payload


def _args(**overrides):
    data = {
        "api_base": "http://local.test",
        "quest_base": "http://quest.test",
        "code": "3601",
        "forge": False,
        "timeout": 1.0,
        "require_adb_reverse": False,
        "adb_path": "adb",
        "service_api_base": "",
        "service_code": "",
        "service_forge": False,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_public_ref_violations_detect_machine_local_paths() -> None:
    payload = {
        "status": "ok",
        "runtime_package": {
            "manifest_uri": "artifacts/suits/demo/manifest.json",
            "debug_path": r"C:\dev\codex\gavai-henshin\sessions\demo.json",
            "file_url": "file:///C:/henshin-demo/gavai-henshin/viewer/assets/demo.glb",
        },
    }

    violations = smoke_check._public_ref_violations(payload)

    assert {entry["path"] for entry in violations} == {
        "$.runtime_package.debug_path",
        "$.runtime_package.file_url",
    }


def test_public_ref_violations_allow_portable_and_local_http_refs() -> None:
    payload = {
        "artifact_ref": "viewer/assets/armor-parts/helmet/helmet.glb",
        "asset_base_url": "http://127.0.0.1:8010",
        "cloud_ref": "gs://henshin-demo/artifacts/manifest.json",
        "public_ref": "https://example.invalid/artifacts/manifest.json",
    }

    assert smoke_check._public_ref_violations(payload) == []


def test_local_preflight_gate_keeps_optional_lanes_out_of_required_pass() -> None:
    result = {
        "api_health": {"ok": True},
        "quest_http_status": 200,
        "code": "1234",
        "runtime_contract": "runtime-render-placement.v1",
        "render_placement_count": 18,
        "missing_selected_variant_key_count": 0,
        "selected_variant_mismatch_count": 0,
        "runtime_surface_failure_count": 0,
        "unsafe_public_ref_count": 0,
    }

    gate = smoke_check._local_preflight_gate(result, [])

    assert gate["status"] == "pass"
    assert gate["operator_label"] == "local-pass"
    assert gate["required_lane"] == "external_pc_local"
    assert gate["optional_enhancement_lanes"] == {
        "gcp_service": "not-included",
        "playcanvas": "not-included",
        "mocopi": "not-included",
    }


def test_local_preflight_gate_fails_without_runtime_contract_even_if_optionals_are_excluded() -> None:
    result = {
        "api_health": {"ok": True},
        "quest_http_status": 200,
        "code": "1234",
        "runtime_contract": "legacy",
        "render_placement_count": 18,
        "missing_selected_variant_key_count": 0,
        "selected_variant_mismatch_count": 0,
        "runtime_surface_failure_count": 0,
        "unsafe_public_ref_count": 0,
    }

    gate = smoke_check._local_preflight_gate(result, [])

    assert gate["status"] == "fail"
    assert gate["operator_label"] == "local-fail"
    assert gate["checks"]["runtime_contract_ok"] is False


def test_local_preflight_gate_can_require_adb_reverse_for_show_floor_pass() -> None:
    result = {
        "api_health": {"ok": True},
        "quest_http_status": 200,
        "code": "1234",
        "runtime_contract": "runtime-render-placement.v1",
        "render_placement_count": 18,
        "missing_selected_variant_key_count": 0,
        "selected_variant_mismatch_count": 0,
        "runtime_surface_failure_count": 0,
        "unsafe_public_ref_count": 0,
        "adb_reverse_required": True,
        "adb_reverse": {
            "ready": True,
            "reverse_ports_present": [5173, 8010],
            "missing_reverse_ports": [],
        },
    }

    gate = smoke_check._local_preflight_gate(result, [])

    assert gate["status"] == "pass"
    assert gate["checks"]["adb_reverse_ok"] is True
    assert gate["adb_reverse_required"] is True


def test_local_preflight_gate_fails_when_required_adb_reverse_is_missing() -> None:
    result = {
        "api_health": {"ok": True},
        "quest_http_status": 200,
        "code": "1234",
        "runtime_contract": "runtime-render-placement.v1",
        "render_placement_count": 18,
        "missing_selected_variant_key_count": 0,
        "selected_variant_mismatch_count": 0,
        "runtime_surface_failure_count": 0,
        "unsafe_public_ref_count": 0,
        "adb_reverse_required": True,
        "adb_reverse": {
            "ready": False,
            "reverse_ports_present": [5173],
            "missing_reverse_ports": [8010],
        },
    }

    gate = smoke_check._local_preflight_gate(result, [])

    assert gate["status"] == "fail"
    assert gate["checks"]["adb_reverse_ok"] is False


def test_adb_parsers_report_ready_device_and_reverse_ports() -> None:
    devices = smoke_check._parse_adb_devices_output(
        """
List of devices attached
2G0YC5ZF9P05Z2 device product:eureka model:Quest_3 device:eureka transport_id:1
"""
    )
    reverses = smoke_check._parse_adb_reverse_output(
        """
UsbFfs tcp:5173 tcp:5173
UsbFfs tcp:8010 tcp:8010
"""
    )

    assert devices == [
        {
            "serial": "2G0YC5ZF9P05Z2",
            "state": "device",
            "details": "product:eureka model:Quest_3 device:eureka transport_id:1",
        }
    ]
    assert reverses == [
        {"transport": "UsbFfs", "local": "tcp:5173", "remote": "tcp:5173"},
        {"transport": "UsbFfs", "local": "tcp:8010", "remote": "tcp:8010"},
    ]


def test_operator_urls_include_quest_usb_path_with_code() -> None:
    urls = smoke_check._operator_urls("3601")

    assert urls["web_forge"] == "http://127.0.0.1:8010/viewer/armor-forge/"
    assert urls["web_forge_exhibition"] == "http://127.0.0.1:8010/viewer/armor-forge/?mode=exhibition"
    assert urls["quest_usb_adb"] == "http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code=3601"
    assert urls["quest_manual_entry_usb_adb"] == "http://localhost:5173/viewer/quest-iw-demo/?newRoute=1"


def test_service_lane_pass_does_not_replace_local_pass(monkeypatch) -> None:
    def fake_get_json(url: str, *, timeout: float) -> dict:
        if url.endswith("/api/health"):
            return {"ok": True}
        if "/v1/quest/recall/" in url:
            return _recall_payload()
        raise AssertionError(url)

    monkeypatch.setattr(smoke_check, "_get_json", fake_get_json)
    monkeypatch.setattr(smoke_check, "_get_text_status", lambda url, *, timeout: 200)

    exit_code, result = smoke_check.run_check(
        _args(service_api_base="https://service.example.invalid", service_code="SVC1")
    )

    assert exit_code == 0
    assert result["ok"] is True
    assert result["preflight_gate"]["operator_label"] == "local-pass"
    assert result["optional_enhancement_lanes"]["gcp_service"] == "service-pass"
    assert result["preflight_gate"]["optional_enhancement_lanes"]["gcp_service"] == "service-pass"
    assert result["optional_lane_reports"]["gcp_service"]["status_label"] == "service-pass"
    assert result["optional_lane_reports"]["gcp_service"]["recall_contract"]["runtime_contract"] == (
        "runtime-render-placement.v1"
    )


def test_service_lane_fail_is_reported_without_failing_local_preflight(monkeypatch) -> None:
    def fake_get_json(url: str, *, timeout: float) -> dict:
        if url == "http://local.test/api/health":
            return {"ok": True}
        if url == "http://local.test/v1/quest/recall/3601":
            return _recall_payload()
        if url == "https://service.example.invalid/api/health":
            return {"ok": True}
        raise urllib.error.URLError("service recall unavailable")

    monkeypatch.setattr(smoke_check, "_get_json", fake_get_json)
    monkeypatch.setattr(smoke_check, "_get_text_status", lambda url, *, timeout: 200)

    exit_code, result = smoke_check.run_check(
        _args(service_api_base="https://service.example.invalid", service_code="SVC1")
    )

    assert exit_code == 0
    assert result["ok"] is True
    assert result["preflight_gate"]["operator_label"] == "local-pass"
    assert result["optional_enhancement_lanes"]["gcp_service"] == "service-fail"
    assert result["optional_lane_reports"]["gcp_service"]["ok"] is False
    assert any("Recall failed" in error for error in result["optional_lane_reports"]["gcp_service"]["errors"])


def test_service_lane_forge_can_supply_its_own_recall_code(monkeypatch) -> None:
    seen_posts: list[str] = []

    def fake_get_json(url: str, *, timeout: float) -> dict:
        if url.endswith("/api/health"):
            return {"ok": True}
        if url == "http://local.test/v1/quest/recall/3601":
            return _recall_payload()
        if url == "https://service.example.invalid/v1/quest/recall/SVC1":
            return _recall_payload()
        raise AssertionError(url)

    def fake_post_json(url: str, payload: dict, *, timeout: float) -> dict:
        seen_posts.append(url)
        return {"status": "READY", "recall_code": "SVC1"}

    monkeypatch.setattr(smoke_check, "_get_json", fake_get_json)
    monkeypatch.setattr(smoke_check, "_post_json", fake_post_json)
    monkeypatch.setattr(smoke_check, "_get_text_status", lambda url, *, timeout: 200)

    exit_code, result = smoke_check.run_check(
        _args(service_api_base="https://service.example.invalid", service_forge=True)
    )

    assert exit_code == 0
    assert seen_posts == ["https://service.example.invalid/v1/suits/forge"]
    service_report = result["optional_lane_reports"]["gcp_service"]
    assert service_report["code"] == "SVC1"
    assert service_report["status_label"] == "service-pass"


def test_recall_contract_report_rejects_public_local_path_leak() -> None:
    def fake_get_json(url: str, *, timeout: float) -> dict:
        return _recall_payload(local_path=r"C:\dev\codex\gavai-henshin\sessions\demo.json")

    original_get_json = smoke_check._get_json
    smoke_check._get_json = fake_get_json
    try:
        report = smoke_check._recall_contract_report("https://service.example.invalid", "SVC1", timeout=1.0)
    finally:
        smoke_check._get_json = original_get_json

    assert report["ok"] is False
    assert report["unsafe_public_ref_count"] == 1
    assert any("machine-local absolute path" in error for error in report["errors"])
