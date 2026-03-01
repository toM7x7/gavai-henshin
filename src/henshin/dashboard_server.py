"""Local dashboard server for suit generation + preview workflows."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler
from pathlib import Path
from socketserver import TCPServer
from typing import Any
from urllib.parse import parse_qs, urlparse


def _is_within_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _resolve_repo_path(root: Path, raw: str) -> Path:
    if not raw:
        raise ValueError("Path is required.")
    candidate = (root / raw).resolve()
    if not _is_within_root(candidate, root):
        raise ValueError(f"Path is outside repository root: {raw}")
    return candidate


def discover_suitspec_paths(root: Path) -> list[str]:
    candidates: set[str] = set()

    default = root / "examples" / "suitspec.sample.json"
    if default.exists():
        candidates.add(str(default.relative_to(root)).replace("\\", "/"))

    for path in (root / "sessions").glob("*/suitspec.json"):
        if path.is_file():
            candidates.add(str(path.relative_to(root)).replace("\\", "/"))

    for path in (root / "examples").glob("**/*suitspec*.json"):
        if path.is_file():
            candidates.add(str(path.relative_to(root)).replace("\\", "/"))

    return sorted(candidates)


@dataclass(slots=True)
class GeneratePartsPayload:
    suitspec: str
    session_id: str | None = None
    parts: list[str] | None = None
    root: str = "sessions"
    model_id: str | None = None
    api_key: str | None = None
    timeout: int = 90
    texture_mode: str = "mesh_uv"
    fallback_dir: str | None = None
    prefer_fallback: bool = True
    update_suitspec: bool = False


def run_generate_parts(root: Path, payload: GeneratePartsPayload) -> dict[str, Any]:
    _resolve_repo_path(root, payload.suitspec)
    if payload.fallback_dir:
        _resolve_repo_path(root, payload.fallback_dir)

    cmd: list[str] = [
        sys.executable,
        "-m",
        "henshin",
        "generate-parts",
        "--suitspec",
        payload.suitspec,
        "--root",
        payload.root,
        "--timeout",
        str(payload.timeout),
        "--texture-mode",
        payload.texture_mode,
    ]
    if payload.session_id:
        cmd.extend(["--session-id", payload.session_id])
    if payload.parts:
        cmd.extend(["--parts", *payload.parts])
    if payload.model_id:
        cmd.extend(["--model-id", payload.model_id])
    if payload.api_key:
        cmd.extend(["--api-key", payload.api_key])
    if payload.fallback_dir:
        cmd.extend(["--fallback-dir", payload.fallback_dir])
    if payload.prefer_fallback:
        cmd.append("--prefer-fallback")
    if payload.update_suitspec:
        cmd.append("--update-suitspec")

    env = os.environ.copy()
    py_path = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"src{os.pathsep}{py_path}" if py_path else "src"
    proc = subprocess.run(
        cmd,
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
    )

    parsed: dict[str, Any] | None = None
    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    if lines:
        try:
            parsed = json.loads(lines[-1])
        except json.JSONDecodeError:
            parsed = None

    result: dict[str, Any] = {
        "ok": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "parsed": parsed,
    }
    return result


class DashboardHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, directory: str, root: Path, **kwargs: Any) -> None:
        self.repo_root = root
        super().__init__(*args, directory=directory, **kwargs)

    def _write_json(self, payload: dict[str, Any], status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/health":
            self._write_json({"ok": True})
            return

        if parsed.path == "/api/suitspecs":
            self._write_json({"ok": True, "items": discover_suitspec_paths(self.repo_root)})
            return

        if parsed.path == "/api/suitspec":
            query = parse_qs(parsed.query)
            raw_path = (query.get("path") or [""])[0]
            try:
                target = _resolve_repo_path(self.repo_root, raw_path)
                payload = json.loads(target.read_text(encoding="utf-8"))
            except (ValueError, FileNotFoundError, json.JSONDecodeError) as exc:
                self._write_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return
            self._write_json({"ok": True, "path": raw_path, "suitspec": payload})
            return

        super().do_GET()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/generate-parts":
            self._write_json({"ok": False, "error": "Unknown API endpoint."}, status=HTTPStatus.NOT_FOUND)
            return

        try:
            content_len = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
            payload_dict = json.loads(raw)
            payload = GeneratePartsPayload(**payload_dict)
            result = run_generate_parts(self.repo_root, payload)
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            self._write_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        status = HTTPStatus.OK if result.get("ok") else HTTPStatus.BAD_REQUEST
        self._write_json(result, status=status)


def serve_dashboard(*, root: Path, port: int) -> None:
    class ReusableTCPServer(TCPServer):
        allow_reuse_address = True

    directory = str(root)

    def factory(*args: Any, **kwargs: Any) -> DashboardHandler:
        return DashboardHandler(*args, directory=directory, root=root, **kwargs)

    with ReusableTCPServer(("", port), factory) as httpd:
        print(
            json.dumps(
                {
                    "ok": True,
                    "message": "Serving suit dashboard",
                    "root": str(root),
                    "url": f"http://localhost:{port}/viewer/suit-dashboard/",
                },
                ensure_ascii=False,
            )
        )
        httpd.serve_forever()
