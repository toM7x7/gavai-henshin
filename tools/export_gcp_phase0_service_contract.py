"""Export the project-local GCP phase0 service contract.

This tool does not call GCP APIs. It freezes the current local Web/API/Quest
contract into a machine-readable JSON document so Cloud Run phase0 work can
mirror the existing payloads, URLs, env keys, and storage boundaries before any
infrastructure is changed.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CONTRACT_VERSION = "gcp-phase0-service-contract.v1"
DEFAULT_OUT = Path("qa/gcp-phase0-service-contract-latest.json")
DEFAULT_LOCAL_API_BASE = "http://127.0.0.1:8010"
DEFAULT_LOCAL_WEB_BASE = "http://127.0.0.1:8010"
DEFAULT_LOCAL_QUEST_BASE = "http://localhost:5173"
MODES = {"local", "external"}
PHASE0_FUTURE_ENV_KEYS = (
    "GCP_PROJECT_ID",
    "CLOUD_RUN_SERVICE_URL",
    "DATABASE_URL",
    "ARTIFACT_BUCKET",
    "TASKS_QUEUE_NAME",
    "SECRET_MANAGER_PREFIX",
)
SECRET_ENV_KEYS = (
    "GEMINI_API_KEY",
    "OPENAI_API_KEY",
    "FAL_KEY",
    "SAKURA_AI_ENGINE_TOKEN",
)


def build_gcp_phase0_service_contract(
    *,
    env_file: str | Path = ".env.demo.example",
    mode: str = "local",
    web_base_url: str | None = None,
    api_base_url: str | None = None,
    quest_base_url: str | None = None,
) -> dict[str, Any]:
    service_tool = _load_service_contract_tool()
    normalized_mode = str(mode or "local").strip().lower()
    if normalized_mode not in MODES:
        normalized_mode = "external"

    env_path = Path(env_file)
    env, duplicate_keys = _parse_env_file(env_path)
    urls = _resolve_urls(
        env,
        mode=normalized_mode,
        web_base_url=web_base_url,
        api_base_url=api_base_url,
        quest_base_url=quest_base_url,
    )
    service_contract = service_tool.validate_service_deployment_contract(
        web_base_url=urls["web_base_url"],
        api_base_url=urls["api_base_url"],
        quest_base_url=urls["quest_base_url"],
        mode=normalized_mode,
        env_file=env_path,
        check_http=False,
    )
    required_keys = list(service_tool.REQUIRED_ENV_KEYS)
    required_env = _required_env_report(env, required_keys)
    blocked_until = _blocked_until(service_contract, env, required_keys, mode=normalized_mode)
    contract_valid = bool(service_contract.get("ok"))

    return {
        "contract_version": CONTRACT_VERSION,
        "ok": contract_valid,
        "status": "pass" if contract_valid else "fail",
        "phase0_promotion_status": "ready" if not blocked_until else "blocked",
        "generated_at": _now_iso(),
        "mode": normalized_mode,
        "env_file": env_path.as_posix(),
        "env_duplicate_keys": duplicate_keys,
        "required_env": required_env,
        "public_urls": _public_urls(urls, env, mode=normalized_mode),
        "api_endpoints": _api_endpoints(),
        "storage_future_mapping": _storage_future_mapping(),
        "cloud_run_candidate_services": _cloud_run_candidate_services(required_keys),
        "blocked_until": blocked_until,
        "local_to_gcp_delta": _local_to_gcp_delta(),
        "service_deployment_contract": service_contract,
    }


def export_gcp_phase0_service_contract(
    *,
    env_file: str | Path = ".env.demo.example",
    mode: str = "local",
    web_base_url: str | None = None,
    api_base_url: str | None = None,
    quest_base_url: str | None = None,
    out: str | Path = DEFAULT_OUT,
) -> dict[str, Any]:
    result = build_gcp_phase0_service_contract(
        env_file=env_file,
        mode=mode,
        web_base_url=web_base_url,
        api_base_url=api_base_url,
        quest_base_url=quest_base_url,
    )
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result["out"] = out_path.as_posix()
    _write_json(out_path, result)
    return result


def _load_service_contract_tool():
    module_name = "validate_service_deployment_contract"
    if module_name in sys.modules:
        return sys.modules[module_name]
    tool_path = Path(__file__).with_name("validate_service_deployment_contract.py")
    spec = importlib.util.spec_from_file_location(module_name, tool_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("validate_service_deployment_contract.py could not be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _resolve_urls(
    env: dict[str, str],
    *,
    mode: str,
    web_base_url: str | None,
    api_base_url: str | None,
    quest_base_url: str | None,
) -> dict[str, str]:
    api = api_base_url or env.get("PUBLIC_API_BASE_URL") or DEFAULT_LOCAL_API_BASE
    web = web_base_url or env.get("PUBLIC_VIEWER_BASE_URL") or DEFAULT_LOCAL_WEB_BASE
    if quest_base_url:
        quest = quest_base_url
    elif mode == "local":
        quest = DEFAULT_LOCAL_QUEST_BASE
    else:
        quest = env.get("PUBLIC_VIEWER_BASE_URL") or web
    asset = env.get("PUBLIC_ASSET_BASE_URL") or api
    return {
        "web_base_url": _strip_url(web),
        "api_base_url": _strip_url(api),
        "quest_base_url": _strip_url(quest),
        "asset_base_url": _strip_url(asset),
    }


def _required_env_report(env: dict[str, str], required_keys: list[str]) -> list[dict[str, Any]]:
    reports: list[dict[str, Any]] = []
    for key in required_keys:
        reports.append(
            {
                "key": key,
                "required_now": True,
                "present": key in env,
                "current_value": _safe_env_value(key, env.get(key, "")),
                "phase0_gcp_value_hint": _phase0_env_hint(key),
                "secret_policy": _secret_policy(key),
            }
        )
    for key in PHASE0_FUTURE_ENV_KEYS:
        reports.append(
            {
                "key": key,
                "required_now": False,
                "required_for_gcp_phase0": key in {"GCP_PROJECT_ID", "DATABASE_URL", "ARTIFACT_BUCKET"},
                "present": key in env,
                "current_value": _safe_env_value(key, env.get(key, "")),
                "phase0_gcp_value_hint": _phase0_env_hint(key),
                "secret_policy": _secret_policy(key),
            }
        )
    for key in SECRET_ENV_KEYS:
        reports.append(
            {
                "key": key,
                "required_now": False,
                "required_for_gcp_phase0": False,
                "present": key in env,
                "current_value": _safe_env_value(key, env.get(key, "")),
                "phase0_gcp_value_hint": "Store real value in Secret Manager; keep release/demo env blank or placeholder.",
                "secret_policy": "secret_manager_only_never_public",
            }
        )
    return reports


def _public_urls(urls: dict[str, str], env: dict[str, str], *, mode: str) -> dict[str, Any]:
    api = urls["api_base_url"]
    web = urls["web_base_url"]
    quest = urls["quest_base_url"]
    return {
        "mode": mode,
        "web_base_url": web,
        "api_base_url": api,
        "quest_base_url": quest,
        "asset_base_url": urls["asset_base_url"],
        "forge_url": f"{web}/viewer/armor-forge/",
        "quest_url_template": f"{quest}/viewer/quest-iw-demo/?newRoute=1&code={{code}}",
        "quest_manual_url": f"{quest}/viewer/quest-iw-demo/?newRoute=1",
        "quest_recall_api_template": f"{api}/v1/quest/recall/{{code}}",
        "api_health": f"{api}/health",
        "dashboard_health": f"{api}/api/health",
        "cors_allowed_origins": _split_csv(env.get("CORS_ALLOWED_ORIGINS", "")),
        "external_mode_policy": "HTTPS public origins only; no localhost, loopback, private LAN, or .local-style host.",
        "local_mode_policy": "127.0.0.1:8010 and localhost:5173 are valid only for the exhibition-PC local fallback.",
    }


def _api_endpoints() -> list[dict[str, Any]]:
    return [
        _endpoint("GET", "/health", "Service health and contract metadata.", "health"),
        _endpoint("GET", "/api/health", "Dashboard/static server health.", "health"),
        _endpoint("GET", "/api/runtime-info", "Operator runtime URL hints for Quest local/LAN paths.", "operator"),
        _endpoint("POST", "/v1/suits/forge", "Public Web Forge suit creation and 4-digit code issue.", "suit"),
        _endpoint("POST", "/v1/suits/issue-id", "Issue a suit id and recall code before saving a full suitspec.", "suit"),
        _endpoint("POST", "/v1/suits", "Persist a suitspec under the canonical API contract.", "suit"),
        _endpoint("GET", "/v1/suits/{suit_id}", "Read stored suit metadata by durable suit id.", "suit"),
        _endpoint("GET", "/v1/suits/code/{code}", "Resolve a recall code to its active suit.", "recall_code"),
        _endpoint("POST", "/v1/suits/{suit_id}/manifest", "Attach or update a suit manifest.", "suit_version"),
        _endpoint("GET", "/v1/suits/{suit_id}/manifest", "Read latest manifest for a suit.", "suit_version"),
        _endpoint("GET", "/v1/manifests/{manifest_id}", "Read manifest by durable manifest id.", "suit_version"),
        _endpoint("GET", "/v1/quest/recall/{code}", "Quest/Web recall payload with runtime_package.", "quest_recall"),
        _endpoint("GET", "/v1/catalog/parts", "Part catalog used by forge/modeler diagnostics.", "catalog"),
        _endpoint("GET", "/v1/catalog/part-blueprints", "Modeler blueprint catalog.", "catalog"),
        _endpoint("POST", "/v1/trials", "Create a transform trial/session.", "trial"),
        _endpoint("GET", "/v1/trials", "List transform trials.", "trial"),
        _endpoint("GET", "/v1/trials/latest", "Read latest transform trial.", "trial"),
        _endpoint("GET", "/v1/trials/{trial_id}", "Read a transform trial by id.", "trial"),
        _endpoint("POST", "/v1/trials/{trial_id}/events", "Append transform event rows.", "transform_event"),
        _endpoint("GET", "/v1/trials/{trial_id}/replay", "Read replay script/record for a trial.", "replay"),
    ]


def _endpoint(method: str, path: str, purpose: str, storage_domain: str) -> dict[str, Any]:
    return {
        "method": method,
        "path": path,
        "purpose": purpose,
        "storage_domain": storage_domain,
        "phase0_authority": "current Python NewRouteApi/dashboard_server contract",
        "public_response_policy": (
            "No machine-local paths, file:// refs, real secrets, raw provider payloads, "
            "or PlayCanvas write-back authority."
        ),
    }


def _storage_future_mapping() -> list[dict[str, str]]:
    return [
        _storage("suit", "sessions/new-route/suits/*/suit.json", "Cloud SQL table suit", "Return suit_id, display summary, current version pointer."),
        _storage("suit_version", "suitspec/manifests/runtime_package JSON files", "Cloud SQL table suit_version plus GCS manifest/runtime snapshot", "Return version ids, schema/runtime versions, and artifact refs."),
        _storage("recall_code", "recall_code field in local suit JSON", "Cloud SQL table recall_code", "4-digit code is a short-lived lookup handle, not durable identity."),
        _storage("quest_recall", "Derived runtime_package from local JSON and viewer/assets", "Cloud SQL read plus GCS runtime snapshot/artifacts", "Return selected variants, render placements, cache policy, portable asset refs."),
        _storage("trial", "sessions/new-route/trials/*/transform-session.json", "Cloud SQL table trial", "Return trial_id, state, safe device/session metadata class."),
        _storage("transform_event", "Local append-only trial events", "Cloud SQL transform_event rows and optional GCS archive", "Append-only event type, phase, motion source, error summary, artifact refs."),
        _storage("replay", "qa/replay and local replay JSON bundles", "Cloud SQL replay index plus GCS JSON/media artifacts", "Use relative, gs://, or approved https refs only."),
        _storage("glb_texture_preview_artifacts", "viewer/assets and generated local artifact files", "Cloud Storage bucket namespace", "Public payload uses logical artifact refs or HTTPS URLs, not physical file paths."),
        _storage("generation_jobs", "In-memory/local job manager", "Cloud Tasks queue plus Cloud SQL job/audit rows", "Only after synchronous behavior and idempotency keys are stable."),
        _storage("provider_secrets", ".env on local PC", "Secret Manager", "Never expose through PUBLIC_* env, Web/Quest payloads, or Replay records."),
    ]


def _storage(domain: str, local_now: str, gcp_phase0: str, public_rule: str) -> dict[str, str]:
    return {
        "domain": domain,
        "local_now": local_now,
        "gcp_phase0": gcp_phase0,
        "public_response_rule": public_rule,
    }


def _cloud_run_candidate_services(required_keys: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "service_id": "henshin-api-ui",
            "phase0_status": "candidate_primary",
            "role": "Single Cloud Run service hosting current API/UI/static boundary before any split.",
            "owns_endpoint_prefixes": ["/health", "/api/", "/v1/", "/viewer/armor-forge/"],
            "required_env_keys": required_keys,
            "promotion_gate": (
                "validate_service_deployment_contract.py --mode external must pass with HTTPS public URLs "
                "and no real secrets in demo/release env files."
            ),
        },
        {
            "service_id": "henshin-worker",
            "phase0_status": "future_optional",
            "role": "Narrow async generation/validation worker after idempotent job model exists.",
            "owns_endpoint_prefixes": [],
            "promotion_gate": "Do not introduce until Cloud Tasks queue and retry/idempotency contract are written.",
        },
        {
            "service_id": "quest-viewer-static",
            "phase0_status": "optional_split_later",
            "role": "Static Quest viewer delivery if one-service API/UI boundary becomes limiting.",
            "owns_endpoint_prefixes": ["/viewer/quest-iw-demo/"],
            "promotion_gate": "Must preserve same /v1 Quest recall payload shape and CORS alignment.",
        },
    ]


def _blocked_until(service_contract: dict[str, Any], env: dict[str, str], required_keys: list[str], *, mode: str) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []
    missing_env = [key for key in required_keys if key not in env]
    if missing_env:
        blockers.append({"gate": "required_env_present", "detail": "Missing env key(s): " + ", ".join(missing_env)})
    if not service_contract.get("ok"):
        blockers.append(
            {
                "gate": "service_deployment_contract",
                "detail": "; ".join(str(reason) for reason in service_contract.get("reasons", [])) or "contract failed",
            }
        )
    if mode == "external":
        blockers.extend(
            [
                {"gate": "external_pc_local_pass", "detail": "External PC local-pass remains prerequisite for visitor operation."},
                {"gate": "cloud_sql_schema_written", "detail": "Suit, suit_version, recall_code, trial, transform_event, and replay indexes must be mapped."},
                {"gate": "gcs_artifact_namespace_written", "detail": "GLB, manifest, runtime snapshot, replay, and media artifact buckets/prefixes must be named."},
                {"gate": "secret_manager_migration", "detail": "Provider keys, DB credentials, and signing secrets must be Secret Manager refs only."},
            ]
        )
    return blockers


def _local_to_gcp_delta() -> dict[str, Any]:
    return {
        "urls": {
            "local": "http://127.0.0.1:8010 for Web/API and http://localhost:5173 for Quest USB ADB reverse.",
            "gcp_phase0": "HTTPS public origins for Web/API/Quest with explicit CORS alignment.",
        },
        "runtime": {
            "local": "python tools/run_henshin.py serve-dashboard --port 8010 plus Quest Vite on 5173.",
            "gcp_phase0": "Cloud Run service handles the current API/UI boundary; Quest local fallback remains independent.",
        },
        "store_driver": {"local": "json", "gcp_phase0": "cloudsql/postgres"},
        "artifact_store_driver": {"local": "local", "gcp_phase0": "gcs"},
        "queue_driver": {"local": "inline", "gcp_phase0": "cloud_tasks only after job idempotency is stable"},
        "secrets": {"local": ".env with blank/placeholders for demo", "gcp_phase0": "Secret Manager refs; never PUBLIC_*"},
        "playcanvas": {
            "local": "Optional snapshot consumer validation only.",
            "gcp_phase0": "Still snapshot consumer; no write-back or source-of-truth role.",
        },
    }


def _phase0_env_hint(key: str) -> str:
    hints = {
        "APP_ENV": "Use staging/exhibition-service label; do not imply local fallback is replaced.",
        "PUBLIC_API_BASE_URL": "External mode must be an HTTPS API origin.",
        "PUBLIC_ASSET_BASE_URL": "HTTPS CDN/GCS/Cloud Run asset origin or approved artifact resolver.",
        "PUBLIC_VIEWER_BASE_URL": "HTTPS Web Forge/Quest viewer origin.",
        "CORS_ALLOWED_ORIGINS": "Explicit comma-separated Web and Quest origins; no wildcard in external mode.",
        "STORE_DRIVER": "json locally; cloudsql/postgres when Cloud SQL schema is ready.",
        "ARTIFACT_STORE_DRIVER": "local locally; gcs when artifact namespace is ready.",
        "QUEST_API_TARGET": "Must match PUBLIC_API_BASE_URL for the viewer lane being tested.",
        "QUEST_VIEWER_PORT": "5173 remains local-only; Cloud Run external mode uses public origin instead of fixed Vite port.",
        "DASHBOARD_PORT": "8010 remains local-only; Cloud Run receives its PORT from platform runtime.",
        "REPLAY_ARTIFACT_ROOT": "Local QA path now; GCS prefix or replay artifact resolver later.",
        "GCP_PROJECT_ID": "GCP project id for phase0 deployment records.",
        "CLOUD_RUN_SERVICE_URL": "Resolved public Cloud Run service URL after deployment.",
        "DATABASE_URL": "Secret Manager or connector-backed Cloud SQL credential; never public.",
        "ARTIFACT_BUCKET": "Cloud Storage bucket name or gs:// prefix for public artifacts.",
        "TASKS_QUEUE_NAME": "Cloud Tasks queue only after async jobs are promoted.",
        "SECRET_MANAGER_PREFIX": "Prefix/path for provider keys and deployment-only secrets.",
    }
    return hints.get(key, "Preserve current contract semantics.")


def _secret_policy(key: str) -> str:
    upper = key.upper()
    if upper.startswith("PUBLIC_"):
        return "public_value_allowed_no_secret_semantics"
    if any(marker in upper for marker in ("KEY", "TOKEN", "SECRET", "PASSWORD", "DATABASE_URL", "CREDENTIAL")):
        return "blank_or_placeholder_in_demo_env_secret_manager_for_real_value"
    return "non_secret_configuration"


def _safe_env_value(key: str, value: str) -> str:
    if not value:
        return ""
    if _secret_policy(key).startswith("blank_or_placeholder"):
        return "<redacted-present>"
    return value


def _parse_env_file(path: Path) -> tuple[dict[str, str], list[str]]:
    if not path.is_file():
        return {}, []
    env: dict[str, str] = {}
    duplicates: list[str] = []
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        if key in env:
            duplicates.append(key)
        env[key] = _strip_env_value(value.strip())
    return env, duplicates


def _strip_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _split_csv(value: str) -> list[str]:
    return [part.strip().rstrip("/") for part in str(value or "").split(",") if part.strip()]


def _strip_url(value: str) -> str:
    return str(value or "").strip().rstrip("/")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _print_text_report(result: dict[str, Any]) -> None:
    print(f"[{result['status'].upper()}] {result['out']}")
    print(f"mode={result['mode']} blocked_until={len(result['blocked_until'])}")
    for blocker in result["blocked_until"]:
        print(f"  blocked  {blocker['gate']}: {blocker['detail']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=Path(".env.demo.example"))
    parser.add_argument("--mode", choices=sorted(MODES), default="local")
    parser.add_argument("--web-base-url")
    parser.add_argument("--api-base-url")
    parser.add_argument("--quest-base-url")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--report-json", action="store_true")
    args = parser.parse_args(argv)

    result = export_gcp_phase0_service_contract(
        env_file=args.env_file,
        mode=args.mode,
        web_base_url=args.web_base_url,
        api_base_url=args.api_base_url,
        quest_base_url=args.quest_base_url,
        out=args.out,
    )
    if args.report_json:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        _print_text_report(result)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
