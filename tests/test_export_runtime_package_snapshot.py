from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterator


REPO_ROOT = Path(__file__).resolve().parents[1]
EXPORT_TOOL_PATH = REPO_ROOT / "tools" / "export_runtime_package_snapshot.py"
VALIDATOR_TOOL_PATH = REPO_ROOT / "tools" / "validate_playcanvas_snapshot.py"


def _load_tool(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


exporter = _load_tool("export_runtime_package_snapshot", EXPORT_TOOL_PATH)
validator = _load_tool("validate_playcanvas_snapshot", VALIDATOR_TOOL_PATH)


def _runtime_package() -> dict[str, Any]:
    return {
        "contract_version": "base-suit-overlay.v1",
        "render_contract": {
            "render_placement_contract": "runtime-render-placement.v1",
            "render_placement_parts": ["helmet"],
        },
        "visual_layers": {
            "armor_overlay": {
                "selected_variant_keys": {"helmet": "helmet:base"},
                "assets": {
                    "helmet": {
                        "selected_variant_key": "helmet:base",
                        "asset_ref": "viewer/assets/armor-parts/helmet/variants/base/helmet__base.glb",
                    }
                },
            }
        },
        "render_placements": {
            "helmet": {
                "contract_version": "runtime-render-placement.v1",
                "part": "helmet",
                "asset_ref": "viewer/assets/armor-parts/helmet/variants/base/helmet__base.glb",
                "selected_variant_key": "helmet:base",
                "coordinate_space": "vrm_humanoid_local_y_up_z_front",
                "quest_coordinate_space": "quest_rig_local_y_up_z_back",
                "offset_m": [0.0, 0.0, 0.0],
                "quest_rig_offset_m": [0.0, 0.0, -0.0],
                "surface_offset_clamped_m": [0.0, 0.02, 0.0],
                "quest_surface_offset_clamped_m": [0.0, 0.02, -0.0],
                "surface_anchor": {
                    "contract_version": "runtime-body-surface-anchor.v1",
                    "offset_clamped_m": [0.0, 0.02, 0.0],
                    "quest_rig_offset_clamped_m": [0.0, 0.02, -0.0],
                },
            }
        },
    }


@contextmanager
def _quest_recall_server(routes: dict[str, tuple[int, dict[str, Any]]]) -> Iterator[str]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
            status, payload = routes.get(
                self.path,
                (404, {"ok": False, "error": f"unknown path: {self.path}"}),
            )
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_export_writes_bomless_validator_ready_runtime_package(tmp_path: Path) -> None:
    snapshot = _runtime_package()
    out = tmp_path / "qa" / "runtime-package-3601.snapshot.json"
    with _quest_recall_server({"/v1/quest/recall/3601": (200, {"ok": True, "runtime_package": snapshot})}) as api_base:
        report = exporter.export_runtime_package_snapshot(
            api_base=f"{api_base}/",
            code="3601",
            out=out,
            timeout=2,
        )

    data = out.read_bytes()
    saved = json.loads(data.decode("utf-8"))
    validation = validator.validate_playcanvas_snapshot(out)

    assert report["ok"] is True
    assert report["endpoint"].endswith("/v1/quest/recall/3601")
    assert report["render_placement_count"] == 1
    assert not data.startswith(b"\xef\xbb\xbf")
    assert saved == snapshot
    assert "runtime_package" not in saved
    assert validation["ok"] is True


def test_cli_exports_snapshot_and_validator_cli_accepts_it(tmp_path: Path) -> None:
    snapshot = _runtime_package()
    out = tmp_path / "qa" / "runtime-package-3601.snapshot.json"
    with _quest_recall_server({"/v1/quest/recall/3601": (200, {"ok": True, "runtime_package": snapshot})}) as api_base:
        completed = subprocess.run(
            [
                sys.executable,
                str(EXPORT_TOOL_PATH),
                "--api-base",
                api_base,
                "--code",
                "3601",
                "--out",
                str(out),
                "--report-json",
            ],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

    export_report = json.loads(completed.stdout)
    validation = subprocess.run(
        [sys.executable, str(VALIDATOR_TOOL_PATH), str(out), "--report-json"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    validation_report = json.loads(validation.stdout)

    assert export_report["ok"] is True
    assert export_report["out"] == out.as_posix()
    assert validation_report["ok"] is True
    assert validation_report["selected_parts"] == ["helmet"]


def test_export_rejects_missing_runtime_package_without_writing(tmp_path: Path) -> None:
    out = tmp_path / "qa" / "runtime-package-0000.snapshot.json"
    with _quest_recall_server({"/v1/quest/recall/0000": (200, {"ok": True})}) as api_base:
        try:
            exporter.export_runtime_package_snapshot(
                api_base=api_base,
                code="0000",
                out=out,
                timeout=2,
            )
        except exporter.SnapshotExportError as exc:
            error = str(exc)
        else:
            raise AssertionError("expected SnapshotExportError")

    assert "runtime_package object" in error
    assert not out.exists()


def test_cli_reports_http_error_without_writing_snapshot(tmp_path: Path) -> None:
    out = tmp_path / "qa" / "runtime-package-4040.snapshot.json"
    with _quest_recall_server({"/v1/quest/recall/4040": (404, {"ok": False, "error": "Unknown recall_code"})}) as api_base:
        completed = subprocess.run(
            [
                sys.executable,
                str(EXPORT_TOOL_PATH),
                "--api-base",
                api_base,
                "--code",
                "4040",
                "--out",
                str(out),
                "--report-json",
            ],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

    report = json.loads(completed.stdout)

    assert completed.returncode == 1
    assert report["ok"] is False
    assert "HTTP 404" in report["error"]
    assert not out.exists()
