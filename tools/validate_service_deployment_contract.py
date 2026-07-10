"""Validate the Web/API/Quest service deployment contract before release.

The gate is meant for two paths:

- `local`: exhibition-PC fallback where 127.0.0.1/localhost and ports 8010/5173
  are valid.
- `external`: service/GCP rehearsal where public URLs must not depend on
  localhost, private LAN addresses, or plaintext HTTP.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


CONTRACT_VERSION = "service-deployment-contract.v1"
MODES = {"local", "external"}
REQUIRED_ENV_KEYS = (
    "APP_ENV",
    "PUBLIC_API_BASE_URL",
    "PUBLIC_ASSET_BASE_URL",
    "PUBLIC_VIEWER_BASE_URL",
    "CORS_ALLOWED_ORIGINS",
    "STORE_DRIVER",
    "ARTIFACT_STORE_DRIVER",
    "QUEST_API_TARGET",
    "QUEST_VIEWER_PORT",
    "DASHBOARD_PORT",
    "REPLAY_ARTIFACT_ROOT",
)
SECRET_KEY_MARKERS = (
    "API_KEY",
    "KEY",
    "TOKEN",
    "SECRET",
    "PASSWORD",
    "CREDENTIAL",
    "PRIVATE_KEY",
    "DATABASE_URL",
)
SECRET_VALUE_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"ghp_[0-9A-Za-z_]{20,}"),
    re.compile(r"github_pat_[0-9A-Za-z_]+"),
    re.compile(r"xox[baprs]-[0-9A-Za-z-]{10,}"),
    re.compile(r"ya29\.[0-9A-Za-z_-]{10,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)
PLACEHOLDER_VALUES = {
    "",
    "changeme",
    "change_me",
    "todo",
    "tbd",
    "placeholder",
    "redacted",
    "replace_me",
    "set_me",
    "not-set",
    "not_set",
    "example",
    "none",
    "null",
}
PRIVATE_HOST_SUFFIXES = (".local", ".lan", ".home", ".internal")
HTTP_USER_AGENT = "gavai-henshin-service-deployment-contract/1"


def validate_service_deployment_contract(
    *,
    web_base_url: str,
    api_base_url: str,
    quest_base_url: str,
    mode: str,
    env_file: str | Path,
    check_http: bool = False,
    timeout: float = 5.0,
) -> dict[str, Any]:
    normalized_mode = str(mode or "").strip().lower()
    reasons: list[str] = []
    warnings: list[str] = []
    if normalized_mode not in MODES:
        reasons.append(f"mode must be one of {sorted(MODES)}")
        normalized_mode = "external"

    urls = {
        "web": _normalize_url(web_base_url),
        "api": _normalize_url(api_base_url),
        "quest": _normalize_url(quest_base_url),
    }
    for name, report in urls.items():
        _validate_url(name, report, normalized_mode, reasons, warnings)

    env_report = _validate_env_file(env_file, urls, normalized_mode, reasons, warnings)
    operator_urls = _operator_urls(urls)
    http_report = _http_report(urls, check_http=check_http, timeout=timeout, reasons=reasons)

    return {
        "contract_version": CONTRACT_VERSION,
        "ok": not reasons,
        "status": "fail" if reasons else "warn" if warnings else "pass",
        "mode": normalized_mode,
        "urls": urls,
        "operator_urls": operator_urls,
        "env": env_report,
        "http": http_report,
        "reasons": reasons,
        "warnings": warnings,
    }


def _normalize_url(value: str) -> dict[str, Any]:
    raw = str(value or "").strip()
    trimmed = raw.rstrip("/")
    parsed = urlparse(trimmed)
    host = (parsed.hostname or "").strip().lower()
    port = parsed.port
    origin = ""
    if parsed.scheme and parsed.netloc:
        origin = f"{parsed.scheme}://{host}"
        if port is not None:
            origin = f"{origin}:{port}"
    return {
        "raw": raw,
        "url": trimmed,
        "scheme": parsed.scheme.lower(),
        "host": host,
        "port": port,
        "path": parsed.path or "",
        "origin": origin,
        "is_loopback": _is_loopback_host(host),
        "is_private_lan": _is_private_host(host),
        "is_private_name": host.endswith(PRIVATE_HOST_SUFFIXES),
    }


def _validate_url(
    name: str,
    report: dict[str, Any],
    mode: str,
    reasons: list[str],
    warnings: list[str],
) -> None:
    if not report["scheme"] or not report["host"]:
        reasons.append(f"{name}_base_url must be an absolute URL")
        return
    if report["scheme"] not in {"http", "https"}:
        reasons.append(f"{name}_base_url must use http or https")
    if mode == "external":
        if report["scheme"] != "https":
            reasons.append(f"external {name}_base_url must use https")
        if report["is_loopback"] or report["is_private_lan"] or report["is_private_name"]:
            reasons.append(f"external {name}_base_url must not use localhost, loopback, private LAN, or .local-style host")
    else:
        if not (report["is_loopback"] or report["is_private_lan"] or report["host"] == "localhost"):
            warnings.append(f"local {name}_base_url is not localhost/loopback/private LAN: {report['url']}")
        if name in {"web", "api"} and report["port"] not in {None, 8010}:
            warnings.append(f"local {name}_base_url usually uses port 8010")
        if name == "quest" and report["port"] not in {None, 5173}:
            warnings.append("local quest_base_url usually uses port 5173")


def _validate_env_file(
    env_file: str | Path,
    urls: dict[str, dict[str, Any]],
    mode: str,
    reasons: list[str],
    warnings: list[str],
) -> dict[str, Any]:
    path = Path(env_file)
    env: dict[str, str] = {}
    duplicates: list[str] = []
    if not path.is_file():
        reasons.append(f"env file is missing: {path}")
    else:
        env, duplicates = _parse_env_file(path)
        for key in duplicates:
            warnings.append(f"env key is duplicated: {key}")

    missing = [key for key in REQUIRED_ENV_KEYS if key not in env]
    reasons.extend(f"env missing required key: {key}" for key in missing)

    _validate_env_url("PUBLIC_API_BASE_URL", urls["api"], env, mode, reasons, warnings)
    _validate_env_url("QUEST_API_TARGET", urls["api"], env, mode, reasons, warnings)
    _validate_env_url("PUBLIC_VIEWER_BASE_URL", urls["web"], env, mode, reasons, warnings)
    _validate_env_url("PUBLIC_ASSET_BASE_URL", None, env, mode, reasons, warnings)
    _validate_cors(env, urls, mode, reasons, warnings)
    _validate_driver_keys(env, reasons)
    secret_hits = _secret_value_hits(env)
    reasons.extend(secret_hits)

    return {
        "path": path.as_posix(),
        "present": path.is_file(),
        "required_keys": list(REQUIRED_ENV_KEYS),
        "missing_keys": missing,
        "duplicate_keys": duplicates,
        "checked_key_count": len(env),
        "public_api_base_url": env.get("PUBLIC_API_BASE_URL"),
        "public_viewer_base_url": env.get("PUBLIC_VIEWER_BASE_URL"),
        "public_asset_base_url": env.get("PUBLIC_ASSET_BASE_URL"),
        "quest_api_target": env.get("QUEST_API_TARGET"),
        "cors_allowed_origins": _split_csv(env.get("CORS_ALLOWED_ORIGINS", "")),
        "secret_value_violation_count": len(secret_hits),
    }


def _parse_env_file(path: Path) -> tuple[dict[str, str], list[str]]:
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
        value = _strip_env_value(value.strip())
        if not key:
            continue
        if key in env:
            duplicates.append(key)
        env[key] = value
    return env, duplicates


def _strip_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _validate_env_url(
    key: str,
    expected_url: dict[str, Any] | None,
    env: dict[str, str],
    mode: str,
    reasons: list[str],
    warnings: list[str],
) -> None:
    if key not in env:
        return
    report = _normalize_url(env[key])
    if not report["scheme"] or not report["host"]:
        reasons.append(f"env {key} must be an absolute URL")
        return
    if mode == "external":
        if report["scheme"] != "https":
            reasons.append(f"external env {key} must use https")
        if report["is_loopback"] or report["is_private_lan"] or report["is_private_name"]:
            reasons.append(f"external env {key} must not point at localhost or private LAN")
    if expected_url is not None and report["url"] != expected_url["url"]:
        reasons.append(f"env {key} must match {expected_url['url']}")
    elif expected_url is None and mode == "local" and report["scheme"] == "https":
        warnings.append(f"local env {key} uses https; ensure the exhibition PC trusts the certificate")


def _validate_cors(
    env: dict[str, str],
    urls: dict[str, dict[str, Any]],
    mode: str,
    reasons: list[str],
    warnings: list[str],
) -> None:
    raw = env.get("CORS_ALLOWED_ORIGINS")
    if raw is None:
        return
    origins = _split_csv(raw)
    if "*" in origins:
        if mode == "external":
            reasons.append("external CORS_ALLOWED_ORIGINS must not be '*'")
        else:
            warnings.append("local CORS_ALLOWED_ORIGINS uses '*'")
        return
    required = {urls["web"]["origin"], urls["quest"]["origin"]}
    missing = sorted(origin for origin in required if origin and origin not in origins)
    reasons.extend(f"CORS_ALLOWED_ORIGINS must include {origin}" for origin in missing)


def _validate_driver_keys(env: dict[str, str], reasons: list[str]) -> None:
    store_driver = env.get("STORE_DRIVER", "").strip().lower()
    artifact_driver = env.get("ARTIFACT_STORE_DRIVER", "").strip().lower()
    if store_driver in {"postgres", "postgresql", "cloudsql"} and "DATABASE_URL" not in env:
        reasons.append("STORE_DRIVER=postgres/cloudsql requires DATABASE_URL key in env file")
    if artifact_driver in {"object", "gcs", "s3", "r2", "azure"} and "ARTIFACT_BUCKET" not in env:
        reasons.append("ARTIFACT_STORE_DRIVER=object/gcs/s3/r2/azure requires ARTIFACT_BUCKET key in env file")


def _secret_value_hits(env: dict[str, str]) -> list[str]:
    hits: list[str] = []
    for key, value in sorted(env.items()):
        key_upper = key.upper()
        if key_upper.startswith("PUBLIC_") and any(marker in key_upper for marker in SECRET_KEY_MARKERS):
            hits.append(f"PUBLIC env key must not carry secret semantics: {key}")
        if any(pattern.search(value) for pattern in SECRET_VALUE_PATTERNS):
            hits.append(f"env {key} appears to contain a real secret value")
            continue
        if any(marker in key_upper for marker in SECRET_KEY_MARKERS):
            if not _is_placeholder_secret(value):
                hits.append(f"env {key} must be blank or placeholder in release/demo env files")
    return hits


def _is_placeholder_secret(value: str) -> bool:
    text = str(value or "").strip()
    lower = text.lower()
    if lower in PLACEHOLDER_VALUES:
        return True
    if lower.startswith("your_") or lower.startswith("your-"):
        return True
    if lower.startswith("<") and lower.endswith(">"):
        return True
    if lower.startswith("__") and lower.endswith("__"):
        return True
    if "placeholder" in lower or "example" in lower or "redacted" in lower:
        return True
    return False


def _http_report(
    urls: dict[str, dict[str, Any]],
    *,
    check_http: bool,
    timeout: float,
    reasons: list[str],
) -> dict[str, Any]:
    report: dict[str, Any] = {"requested": check_http, "checks": []}
    if not check_http:
        return report
    checks = [
        ("api_health", f"{urls['api']['url']}/health", True),
        ("web_forge", f"{urls['web']['url']}/viewer/armor-forge/", False),
        ("quest_viewer", f"{urls['quest']['url']}/viewer/quest-iw-demo/", False),
    ]
    for name, url, expect_json in checks:
        check = _fetch_http_check(name, url, timeout=timeout, expect_json=expect_json)
        report["checks"].append(check)
        if not check["ok"]:
            reasons.append(f"http check failed: {name} {url}: {check['error']}")
    report["ok"] = all(check["ok"] for check in report["checks"])
    return report


def _fetch_http_check(name: str, url: str, *, timeout: float, expect_json: bool) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": HTTP_USER_AGENT, "Accept": "application/json,*/*"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(4096)
            status = int(response.status)
    except urllib.error.HTTPError as exc:
        return {"name": name, "url": url, "ok": False, "status": exc.code, "error": f"HTTP {exc.code}"}
    except urllib.error.URLError as exc:
        return {"name": name, "url": url, "ok": False, "status": None, "error": str(exc.reason)}
    except TimeoutError as exc:
        return {"name": name, "url": url, "ok": False, "status": None, "error": str(exc)}
    ok = 200 <= status < 400
    error = ""
    if expect_json and ok:
        try:
            json.loads(body.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            ok = False
            error = f"response is not JSON: {exc}"
    return {"name": name, "url": url, "ok": ok, "status": status, "error": error}


def _operator_urls(urls: dict[str, dict[str, Any]]) -> dict[str, str]:
    return {
        "forge_url": f"{urls['web']['url']}/viewer/armor-forge/",
        "quest_url_template": f"{urls['quest']['url']}/viewer/quest-iw-demo/?newRoute=1&code={{code}}",
        "quest_recall_api_template": f"{urls['api']['url']}/v1/quest/recall/{{code}}",
        "api_health": f"{urls['api']['url']}/health",
    }


def _split_csv(value: str) -> list[str]:
    return [part.strip().rstrip("/") for part in str(value or "").split(",") if part.strip()]


def _is_loopback_host(host: str) -> bool:
    return host in {"localhost", "::1"} or host.startswith("127.")


def _is_private_host(host: str) -> bool:
    if not host:
        return False
    if _is_loopback_host(host):
        return True
    try:
        ip = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return False
    return bool(ip.is_private or ip.is_loopback or ip.is_link_local)


def _print_text_report(result: dict[str, Any]) -> None:
    print(f"[{result['status'].upper()}] mode={result['mode']}")
    print(f"web:   {result['urls']['web']['url']}")
    print(f"api:   {result['urls']['api']['url']}")
    print(f"quest: {result['urls']['quest']['url']}")
    print(f"env:   {result['env']['path']}")
    for reason in result["reasons"]:
        print(f"  fail  {reason}")
    for warning in result["warnings"]:
        print(f"  warn  {warning}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--web-base-url", required=True)
    parser.add_argument("--api-base-url", required=True)
    parser.add_argument("--quest-base-url", required=True)
    parser.add_argument("--mode", choices=sorted(MODES), required=True)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--check-http", action="store_true")
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--report-json", action="store_true")
    args = parser.parse_args(argv)

    result = validate_service_deployment_contract(
        web_base_url=args.web_base_url,
        api_base_url=args.api_base_url,
        quest_base_url=args.quest_base_url,
        mode=args.mode,
        env_file=args.env_file,
        check_http=args.check_http,
        timeout=args.timeout,
    )
    if args.report_json:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        _print_text_report(result)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
