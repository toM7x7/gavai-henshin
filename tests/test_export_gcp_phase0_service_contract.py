from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "export_gcp_phase0_service_contract.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("export_gcp_phase0_service_contract", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["export_gcp_phase0_service_contract"] = module
    spec.loader.exec_module(module)
    return module


tool = _load_tool()


def _env_text(
    *,
    api: str = "http://127.0.0.1:8010",
    web: str = "http://127.0.0.1:8010",
    asset: str = "http://127.0.0.1:8010",
    quest: str = "http://localhost:5173",
    cors: str | None = None,
    app_env: str = "exhibition-local",
) -> str:
    origins = cors or f"{web},{quest}"
    return f"""APP_ENV={app_env}
PUBLIC_API_BASE_URL={api}
PUBLIC_ASSET_BASE_URL={asset}
PUBLIC_VIEWER_BASE_URL={web}
CORS_ALLOWED_ORIGINS={origins}
LOG_LEVEL=info
DASHBOARD_PORT=8010
QUEST_VIEWER_PORT=5173
QUEST_API_TARGET={api}
QUEST_HOST=0.0.0.0
QUEST_PORT=5173
STORE_DRIVER=json
ARTIFACT_STORE_DRIVER=local
LIVE_STATE_DRIVER=memory
QUEUE_DRIVER=inline
REPLAY_ARTIFACT_ROOT=qa/replay
GEMINI_API_KEY=
OPENAI_API_KEY=
FAL_KEY=
SAKURA_AI_ENGINE_TOKEN=
VOICE_TRIGGER_PHRASE=seisei
"""


def _write_env(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_local_contract_exports_required_env_urls_endpoints_and_storage_mapping(tmp_path: Path) -> None:
    env_path = _write_env(tmp_path / ".env.demo.example", _env_text())

    result = tool.build_gcp_phase0_service_contract(env_file=env_path)
    env_by_key = {entry["key"]: entry for entry in result["required_env"]}
    endpoint_paths = {entry["path"] for entry in result["api_endpoints"]}
    storage_by_domain = {entry["domain"]: entry for entry in result["storage_future_mapping"]}

    assert result["ok"] is True
    assert result["status"] == "pass"
    assert result["phase0_promotion_status"] == "ready"
    assert result["public_urls"]["web_base_url"] == "http://127.0.0.1:8010"
    assert result["public_urls"]["quest_base_url"] == "http://localhost:5173"
    assert result["public_urls"]["quest_recall_api_template"].endswith("/v1/quest/recall/{code}")
    assert env_by_key["PUBLIC_API_BASE_URL"]["required_now"] is True
    assert env_by_key["ARTIFACT_BUCKET"]["required_for_gcp_phase0"] is True
    assert env_by_key["OPENAI_API_KEY"]["secret_policy"] == "secret_manager_only_never_public"
    assert "/v1/suits/forge" in endpoint_paths
    assert "/v1/quest/recall/{code}" in endpoint_paths
    assert "/v1/trials/{trial_id}/events" in endpoint_paths
    assert storage_by_domain["recall_code"]["gcp_phase0"] == "Cloud SQL table recall_code"
    assert storage_by_domain["provider_secrets"]["gcp_phase0"] == "Secret Manager"
    assert result["cloud_run_candidate_services"][0]["service_id"] == "henshin-api-ui"
    assert result["local_to_gcp_delta"]["store_driver"]["gcp_phase0"] == "cloudsql/postgres"


def test_external_contract_uses_https_urls_and_keeps_phase0_blockers_explicit(tmp_path: Path) -> None:
    api = "https://api.example.com"
    web = "https://web.example.com"
    quest = "https://quest.example.com"
    env_path = _write_env(
        tmp_path / ".env.demo.example",
        _env_text(
            api=api,
            web=web,
            asset="https://cdn.example.com",
            quest=quest,
            app_env="staging",
        ),
    )

    result = tool.build_gcp_phase0_service_contract(
        env_file=env_path,
        mode="external",
        web_base_url=web,
        api_base_url=api,
        quest_base_url=quest,
    )

    assert result["ok"] is True
    assert result["service_deployment_contract"]["status"] == "pass"
    assert result["public_urls"]["forge_url"] == "https://web.example.com/viewer/armor-forge/"
    assert result["public_urls"]["quest_url_template"] == (
        "https://quest.example.com/viewer/quest-iw-demo/?newRoute=1&code={code}"
    )
    assert result["phase0_promotion_status"] == "blocked"
    assert {blocker["gate"] for blocker in result["blocked_until"]} >= {
        "external_pc_local_pass",
        "cloud_sql_schema_written",
        "gcs_artifact_namespace_written",
        "secret_manager_migration",
    }


def test_missing_env_file_fails_but_preserves_machine_readable_sections(tmp_path: Path) -> None:
    result = tool.build_gcp_phase0_service_contract(env_file=tmp_path / "missing.env")
    env_by_key = {entry["key"]: entry for entry in result["required_env"]}

    assert result["ok"] is False
    assert result["status"] == "fail"
    assert env_by_key["APP_ENV"]["present"] is False
    assert any(blocker["gate"] == "required_env_present" for blocker in result["blocked_until"])
    assert result["public_urls"]["api_base_url"] == "http://127.0.0.1:8010"
    assert result["api_endpoints"]
    assert result["storage_future_mapping"]


def test_cli_writes_report_json_without_bom(tmp_path: Path) -> None:
    env_path = _write_env(tmp_path / ".env.demo.example", _env_text())
    out_path = tmp_path / "qa" / "gcp-phase0.json"

    completed = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--env-file",
            str(env_path),
            "--out",
            str(out_path),
            "--report-json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    stdout_payload = json.loads(completed.stdout)
    raw = out_path.read_bytes()
    file_payload = json.loads(raw.decode("utf-8"))

    assert stdout_payload["ok"] is True
    assert stdout_payload["out"] == out_path.as_posix()
    assert file_payload["contract_version"] == "gcp-phase0-service-contract.v1"
    assert not raw.startswith(b"\xef\xbb\xbf")


def test_cli_returns_nonzero_for_invalid_external_service_contract(tmp_path: Path) -> None:
    env_path = _write_env(tmp_path / ".env.demo.example", _env_text())

    completed = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--env-file",
            str(env_path),
            "--mode",
            "external",
            "--web-base-url",
            "http://127.0.0.1:8010",
            "--api-base-url",
            "http://127.0.0.1:8010",
            "--quest-base-url",
            "http://localhost:5173",
            "--out",
            str(tmp_path / "qa" / "bad.json"),
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
    assert any("external web_base_url must use https" in reason for reason in result["service_deployment_contract"]["reasons"])
