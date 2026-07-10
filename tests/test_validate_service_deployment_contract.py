from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterator


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "validate_service_deployment_contract.py"


def _load_validator():
    spec = importlib.util.spec_from_file_location("validate_service_deployment_contract", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["validate_service_deployment_contract"] = module
    spec.loader.exec_module(module)
    return module


validator = _load_validator()


def _env_text(
    *,
    api: str = "http://127.0.0.1:8010",
    web: str = "http://127.0.0.1:8010",
    asset: str = "http://127.0.0.1:8010",
    cors: str = "http://127.0.0.1:8010,http://localhost:5173",
    quest_api_target: str | None = None,
    app_env: str = "exhibition-local",
    extra: str = "",
) -> str:
    return f"""APP_ENV={app_env}
PUBLIC_API_BASE_URL={api}
PUBLIC_ASSET_BASE_URL={asset}
PUBLIC_VIEWER_BASE_URL={web}
CORS_ALLOWED_ORIGINS={cors}
DASHBOARD_PORT=8010
QUEST_VIEWER_PORT=5173
QUEST_API_TARGET={quest_api_target or api}
STORE_DRIVER=json
ARTIFACT_STORE_DRIVER=local
REPLAY_ARTIFACT_ROOT=qa/replay
GEMINI_API_KEY=
OPENAI_API_KEY=
FAL_KEY=
SAKURA_AI_ENGINE_TOKEN=
{extra}"""


def _write_env(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


@contextmanager
def _service_server() -> Iterator[str]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
            if self.path == "/health":
                body = json.dumps({"ok": True, "service": "new-route-api"}).encode("utf-8")
                content_type = "application/json"
            elif self.path in {"/viewer/armor-forge/", "/viewer/quest-iw-demo/"}:
                body = b"ok"
                content_type = "text/plain"
            else:
                body = b"not found"
                self.send_response(404)
                self.send_header("Content-Type", "text/plain")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type)
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


def test_local_mode_allows_127_api_and_localhost_quest(tmp_path: Path) -> None:
    env_path = _write_env(tmp_path / ".env.demo.example", _env_text())

    result = validator.validate_service_deployment_contract(
        web_base_url="http://127.0.0.1:8010",
        api_base_url="http://127.0.0.1:8010",
        quest_base_url="http://localhost:5173",
        mode="local",
        env_file=env_path,
    )

    assert result["ok"] is True
    assert result["mode"] == "local"
    assert result["operator_urls"]["forge_url"] == "http://127.0.0.1:8010/viewer/armor-forge/"
    assert result["operator_urls"]["quest_url_template"] == "http://localhost:5173/viewer/quest-iw-demo/?newRoute=1&code={code}"


def test_external_mode_accepts_https_public_urls_and_matching_env(tmp_path: Path) -> None:
    env_path = _write_env(
        tmp_path / ".env.demo.example",
        _env_text(
            api="https://api.example.com",
            web="https://web.example.com",
            asset="https://cdn.example.com",
            cors="https://web.example.com,https://quest.example.com",
            app_env="staging",
        ),
    )

    result = validator.validate_service_deployment_contract(
        web_base_url="https://web.example.com",
        api_base_url="https://api.example.com",
        quest_base_url="https://quest.example.com",
        mode="external",
        env_file=env_path,
    )

    assert result["ok"] is True
    assert result["status"] == "pass"
    assert result["env"]["missing_keys"] == []


def test_external_mode_rejects_plain_http_localhost_private_lan_and_wildcard_cors(tmp_path: Path) -> None:
    env_path = _write_env(
        tmp_path / ".env.demo.example",
        _env_text(
            api="http://127.0.0.1:8010",
            web="http://192.168.1.20:8010",
            asset="http://10.0.0.5:8010",
            cors="*",
            quest_api_target="http://127.0.0.1:8010",
            app_env="staging",
        ),
    )

    result = validator.validate_service_deployment_contract(
        web_base_url="http://192.168.1.20:8010",
        api_base_url="http://127.0.0.1:8010",
        quest_base_url="http://quest.local:5173",
        mode="external",
        env_file=env_path,
    )

    assert result["ok"] is False
    joined = "\n".join(result["reasons"])
    assert "external web_base_url must use https" in joined
    assert "external api_base_url must not use localhost" in joined
    assert "external quest_base_url must not use localhost" in joined
    assert "external CORS_ALLOWED_ORIGINS must not be '*'" in joined


def test_secret_like_real_values_are_rejected(tmp_path: Path) -> None:
    env_path = _write_env(
        tmp_path / ".env.demo.example",
        _env_text(extra="OPENAI_API_KEY=sk-1234567890abcdefghijklmnop\nDATABASE_URL=postgres://user:realpass@db.prod-host.net/app"),
    )

    result = validator.validate_service_deployment_contract(
        web_base_url="http://127.0.0.1:8010",
        api_base_url="http://127.0.0.1:8010",
        quest_base_url="http://localhost:5173",
        mode="local",
        env_file=env_path,
    )

    assert result["ok"] is False
    assert result["env"]["secret_value_violation_count"] >= 2
    assert any("OPENAI_API_KEY" in reason for reason in result["reasons"])
    assert any("DATABASE_URL" in reason for reason in result["reasons"])


def test_check_http_validates_health_forge_and_quest_routes(tmp_path: Path) -> None:
    with _service_server() as base_url:
        env_path = _write_env(
            tmp_path / ".env.demo.example",
            _env_text(
                api=base_url,
                web=base_url,
                asset=base_url,
                cors=base_url,
                quest_api_target=base_url,
            ),
        )
        result = validator.validate_service_deployment_contract(
            web_base_url=base_url,
            api_base_url=base_url,
            quest_base_url=base_url,
            mode="local",
            env_file=env_path,
            check_http=True,
            timeout=2,
        )

    assert result["ok"] is True
    assert result["http"]["ok"] is True
    assert [check["name"] for check in result["http"]["checks"]] == ["api_health", "web_forge", "quest_viewer"]


def test_cli_emits_json_and_nonzero_on_failure(tmp_path: Path) -> None:
    env_path = _write_env(tmp_path / ".env.demo.example", _env_text(cors="*"))

    completed = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--web-base-url",
            "http://127.0.0.1:8010",
            "--api-base-url",
            "http://127.0.0.1:8010",
            "--quest-base-url",
            "http://localhost:5173",
            "--mode",
            "external",
            "--env-file",
            str(env_path),
            "--report-json",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)

    assert completed.returncode == 1
    assert result["ok"] is False
    assert result["status"] == "fail"
