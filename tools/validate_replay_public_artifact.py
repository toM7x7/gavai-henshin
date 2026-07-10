"""Validate ReplayRecord artifacts before public Web/service use.

The checker accepts either a ReplayRecord JSON file or a
``prepare_replay_qa_artifact.py`` summary. It is intentionally static: it does
not open a browser or resolve remote URLs. Its job is to catch portability
breaks before a QA artifact is promoted from local exhibition proof files to a
Web-service-facing bundle.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse


CONTRACT_VERSION = "replay-public-artifact-preflight.v1"
REPLAY_SCHEMA_VERSION = "0.2"
REPLAY_CONTRACT_VERSION = "replay-record.v0.2"
QA_SUMMARY_CONTRACT_VERSION = "replay-qa-artifact-summary.v1"
SNAPSHOT_CONTRACT_VERSION = "runtime-variant-placement-snapshot.v1"
PUBLIC_ARTIFACT_POLICY_CONTRACT_VERSION = "replay-public-artifact-policy.v1"
LOCAL_MODES = {"local", "external"}
LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
QUEST_REPLAY_VIEWER_PATH = "viewer/quest-iw-demo/index.html"
QUEST_REPLAY_RECORD_QUERY_PARAM = "replay"
QUEST_RECALL_CODE_QUERY_PARAM = "code"
QUEST_QA_CODE_QUERY_PARAM = "qa"
LEGACY_WEB_REPLAY_QUERY_PARAMS = {"replayRecord", "qaCode"}
RECALL_CODE_RE = re.compile(r"^[A-Z0-9]{4}$")
WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:[\\/]")
WINDOWS_UNC_RE = re.compile(r"^(\\\\|//[^/]+/[^/]+)")
PATHLIKE_BACKSLASH_RE = re.compile(r"\\.*\.(json|glb|gltf|bin|png|jpg|jpeg|webp|wav|webm|mp4)([?#].*)?$", re.I)
PLAYCANVAS_POLICY_KEYS = {
    "allow_playcanvas_writeback",
    "playcanvas_authoritative",
    "playcanvas_can_write",
    "playcanvas_mutation_endpoint",
    "playcanvas_owner",
    "playcanvas_save_endpoint",
    "playcanvas_source_of_truth",
    "playcanvas_writeback",
    "playcanvas_writeback_allowed",
    "playcanvas_writeback_enabled",
    "playcanvas_write_authority",
    "playcanvas_write_endpoint",
    "playcanvas_write_enabled",
}
PLAYCANVAS_CONTEXT_KEYS = {
    "authoritative",
    "can_write",
    "mutation_endpoint",
    "mutation_allowed",
    "mutations_allowed",
    "owner",
    "owns_placement",
    "save_allowed",
    "save_endpoint",
    "source_of_truth",
    "write_authority",
    "write_endpoint",
    "writeback",
    "writeback_allowed",
    "writeback_enabled",
    "write_enabled",
}
PLAYCANVAS_ENDPOINT_KEYS = {
    "mutation_endpoint",
    "playcanvas_mutation_endpoint",
    "playcanvas_save_endpoint",
    "playcanvas_write_endpoint",
    "save_endpoint",
    "write_endpoint",
}
PLAYCANVAS_ALLOWED_ROLES = {
    "adapter",
    "consumer",
    "preview_adapter",
    "read_only",
    "read_only_snapshot_consumer",
    "readonly",
    "snapshot_consumer",
    "visual_qa_adapter",
}
FALSE_POLICY_VALUES = {"false", "forbidden", "disabled", "no", "none", "read_only", "read-only", "readonly"}
TRUE_POLICY_VALUES = {"true", "allowed", "enabled", "yes", "write", "write_enabled", "writeback_allowed"}


def validate_replay_public_artifact(
    artifact: str | Path | dict[str, Any],
    *,
    mode: str = "local",
) -> dict[str, Any]:
    if mode not in LOCAL_MODES:
        raise ValueError("mode must be 'local' or 'external'")

    payload, input_path = _load_payload(artifact)
    reasons: list[str] = []
    warnings: list[str] = []
    record, source_type, artifact_path = _replay_record_from_payload(payload, input_path, reasons)
    if record is None:
        record = {}

    runtime_package = _dict(record.get("runtime_package"))
    variant_snapshot = _dict(runtime_package.get("variant_placement_snapshot"))
    selected_variants = _selected_variant_keys(record, runtime_package, variant_snapshot)
    scan_payload = _scan_payload(payload, record=record, source_type=source_type)
    local_path_leaks = _find_local_path_leaks(scan_payload)
    localhost_urls = _find_localhost_urls(scan_payload)
    public_artifact_policy = _inspect_public_artifact_policy(record)
    playcanvas_policy = _inspect_playcanvas_writeback(record)
    web_replay_url_contract = _validate_web_replay_url_contract(payload, record, source_type=source_type)

    schema_version = str(record.get("schema_version") or "")
    record_contract = str(record.get("contract_version") or "")
    if schema_version != REPLAY_SCHEMA_VERSION:
        reasons.append(f"ReplayRecord.schema_version must be {REPLAY_SCHEMA_VERSION}")
    if record_contract != REPLAY_CONTRACT_VERSION:
        reasons.append(f"ReplayRecord.contract_version must be {REPLAY_CONTRACT_VERSION}")

    if not runtime_package:
        reasons.append("ReplayRecord.runtime_package is required")
    if not variant_snapshot:
        reasons.append("ReplayRecord.runtime_package.variant_placement_snapshot is required")
    elif variant_snapshot.get("contract_version") != SNAPSHOT_CONTRACT_VERSION:
        reasons.append(
            f"ReplayRecord.runtime_package.variant_placement_snapshot.contract_version must be {SNAPSHOT_CONTRACT_VERSION}"
        )
    if not selected_variants:
        reasons.append("ReplayRecord selected variants are required")

    for leak in local_path_leaks:
        reasons.append(f"local filesystem path is not public-portable at {leak['path']}: {leak['value']}")

    localhost_message = "localhost/loopback URL is not allowed for external public artifacts"
    if mode == "external":
        for url in localhost_urls:
            reasons.append(f"{localhost_message} at {url['path']}: {url['value']}")
    elif localhost_urls:
        warnings.append("localhost/loopback URLs are tolerated only in local mode")

    url_contract_issues = web_replay_url_contract.get("issues", [])
    for issue in url_contract_issues:
        message = issue["message"]
        if issue["severity"] == "warning" or (issue["severity"] == "legacy" and mode == "local"):
            warnings.append(message)
        else:
            reasons.append(message)

    reasons.extend(public_artifact_policy["reasons"])
    warnings.extend(public_artifact_policy["warnings"])

    if not playcanvas_policy["writeback_forbidden_explicit"]:
        reasons.append("PlayCanvas write-back prohibition must be explicit in the ReplayRecord")
    for violation in playcanvas_policy["writeback_violations"]:
        reasons.append(f"PlayCanvas write-back appears enabled at {violation['path']}: {violation['value']}")

    return {
        "contract_version": CONTRACT_VERSION,
        "ok": not reasons,
        "status": "fail" if reasons else "pass",
        "mode": mode,
        "input_path": input_path,
        "source_type": source_type,
        "artifact_path": artifact_path,
        "replay_id": record.get("replay_id"),
        "recall_code": record.get("recall_code"),
        "schema_version": schema_version,
        "replay_contract_version": record_contract,
        "runtime_package_present": bool(runtime_package),
        "variant_placement_snapshot_present": bool(variant_snapshot),
        "selected_variant_count": len(selected_variants),
        "selected_variants": selected_variants,
        "local_path_leak_count": len(local_path_leaks),
        "local_path_leaks": local_path_leaks,
        "localhost_url_count": len(localhost_urls),
        "localhost_urls": localhost_urls,
        "web_replay_url_contract": web_replay_url_contract,
        "public_artifact_policy": public_artifact_policy,
        "playcanvas": playcanvas_policy,
        "reasons": reasons,
        "warnings": warnings,
    }


def _load_payload(artifact: str | Path | dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    if isinstance(artifact, dict):
        return artifact, None
    path = Path(artifact)
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("Replay public artifact input must be a JSON object")
    return payload, path.as_posix()


def _replay_record_from_payload(
    payload: dict[str, Any],
    input_path: str | None,
    reasons: list[str],
) -> tuple[dict[str, Any] | None, str, str | None]:
    if _is_qa_summary(payload):
        artifact_ref = str(payload.get("artifact_path") or "")
        if not artifact_ref:
            reasons.append("QA summary artifact_path is required")
            return None, "qa_summary", None
        artifact_path = _resolve_artifact_path(artifact_ref, input_path)
        if not artifact_path.exists():
            reasons.append(f"QA summary artifact_path does not exist: {artifact_ref}")
            return None, "qa_summary", artifact_path.as_posix()
        record = json.loads(artifact_path.read_text(encoding="utf-8-sig"))
        if not isinstance(record, dict):
            reasons.append("QA summary artifact_path must point to a ReplayRecord JSON object")
            return None, "qa_summary", artifact_path.as_posix()
        return record, "qa_summary", artifact_path.as_posix()
    return payload, "replay_record", input_path


def _is_qa_summary(payload: dict[str, Any]) -> bool:
    return (
        payload.get("contract_version") == QA_SUMMARY_CONTRACT_VERSION
        or ("artifact_path" in payload and "alignment_status" in payload)
    )


def _resolve_artifact_path(artifact_ref: str, input_path: str | None) -> Path:
    path = Path(artifact_ref)
    if path.is_absolute():
        return path
    if input_path:
        summary_relative = Path(input_path).parent / path
        if summary_relative.exists():
            return summary_relative
    return path


def _scan_payload(payload: dict[str, Any], *, record: dict[str, Any], source_type: str) -> dict[str, Any]:
    if source_type == "qa_summary":
        return {"qa_summary": payload, "replay_record": record}
    return {"replay_record": record}


def _selected_variant_keys(
    record: dict[str, Any],
    runtime_package: dict[str, Any],
    variant_snapshot: dict[str, Any],
) -> dict[str, str]:
    selected: dict[str, str] = {}
    for source in (
        _dict(record.get("selected_variants")),
        _dict(variant_snapshot.get("selected_variant_keys")),
        _dict(runtime_package.get("selected_variant_keys")),
        _dict(_dict(_dict(runtime_package.get("visual_layers")).get("armor_overlay")).get("selected_variant_keys")),
    ):
        selected.update({str(part): str(key) for part, key in source.items() if key})
    return dict(sorted(selected.items()))


def _find_local_path_leaks(payload: Any) -> list[dict[str, str]]:
    leaks: list[dict[str, str]] = []
    for path, value in _walk_strings(payload):
        if _is_local_filesystem_ref(value):
            leaks.append({"path": path, "value": value})
    return leaks


def _find_localhost_urls(payload: Any) -> list[dict[str, str]]:
    urls: list[dict[str, str]] = []
    for path, value in _walk_strings(payload):
        if _is_localhost_url(value):
            urls.append({"path": path, "value": value})
    return urls


def _inspect_public_artifact_policy(record: dict[str, Any]) -> dict[str, Any]:
    policy = _dict(record.get("public_artifact_policy"))
    reasons: list[str] = []
    warnings: list[str] = []
    checks = {
        "present": bool(policy),
        "contract_version": str(policy.get("contract_version") or ""),
        "role": str(policy.get("role") or ""),
        "playcanvas_writeback_allowed": policy.get("playcanvas_writeback_allowed") if policy else None,
        "local_path_allowed": policy.get("local_path_allowed") if policy else None,
        "external_publication_requires_preflight": (
            policy.get("external_publication_requires_preflight") if policy else None
        ),
    }
    if not policy:
        reasons.append("ReplayRecord.public_artifact_policy is required")
        return {"ok": False, "checks": checks, "reasons": reasons, "warnings": warnings}

    if policy.get("contract_version") != PUBLIC_ARTIFACT_POLICY_CONTRACT_VERSION:
        reasons.append(
            f"ReplayRecord.public_artifact_policy.contract_version must be {PUBLIC_ARTIFACT_POLICY_CONTRACT_VERSION}"
        )
    role = _normalize_key(str(policy.get("role") or ""))
    if role not in PLAYCANVAS_ALLOWED_ROLES:
        reasons.append("ReplayRecord.public_artifact_policy.role must keep the artifact in snapshot-consumer mode")
    if policy.get("playcanvas_writeback_allowed") is not False:
        reasons.append("ReplayRecord.public_artifact_policy.playcanvas_writeback_allowed must be false")
    if policy.get("local_path_allowed") is not False:
        reasons.append("ReplayRecord.public_artifact_policy.local_path_allowed must be false")
    if policy.get("external_publication_requires_preflight") is not True:
        reasons.append("ReplayRecord.public_artifact_policy.external_publication_requires_preflight must be true")
    return {"ok": not reasons, "checks": checks, "reasons": reasons, "warnings": warnings}


def _validate_web_replay_url_contract(
    payload: dict[str, Any],
    record: dict[str, Any],
    *,
    source_type: str,
) -> dict[str, Any]:
    if source_type != "qa_summary":
        return {
            "checked": False,
            "status": "not_checked",
            "hint": "",
            "issues": [],
        }

    hint = str(payload.get("web_replay_check_url_hint") or "")
    result: dict[str, Any] = {
        "checked": True,
        "status": "pass",
        "hint": hint,
        "expected_viewer_path": QUEST_REPLAY_VIEWER_PATH,
        "path": "",
        "query_keys": [],
        "legacy_query_keys": [],
        "missing_query_keys": [],
        "issues": [],
    }
    if not hint:
        _add_url_contract_issue(result, "error", "QA summary web_replay_check_url_hint is required")
        return _finalize_url_contract(result)

    parsed = urlparse(hint)
    path = parsed.path.lstrip("/")
    query = parse_qs(parsed.query, keep_blank_values=True)
    query_keys = sorted(query)
    legacy_keys = sorted(key for key in query_keys if key in LEGACY_WEB_REPLAY_QUERY_PARAMS)
    result.update({
        "path": path,
        "query_keys": query_keys,
        "legacy_query_keys": legacy_keys,
    })

    if path != QUEST_REPLAY_VIEWER_PATH:
        _add_url_contract_issue(
            result,
            "error",
            f"web_replay_check_url_hint must target {QUEST_REPLAY_VIEWER_PATH}",
        )

    required_keys = [QUEST_REPLAY_RECORD_QUERY_PARAM, QUEST_QA_CODE_QUERY_PARAM]
    expected_recall_code = _viewer_recall_code(record.get("recall_code"))
    if expected_recall_code:
        required_keys.append(QUEST_RECALL_CODE_QUERY_PARAM)
    missing = [key for key in required_keys if key not in query]
    result["missing_query_keys"] = missing

    if legacy_keys:
        _add_url_contract_issue(
            result,
            "legacy",
            f"web_replay_check_url_hint uses legacy query params: {', '.join(legacy_keys)}",
        )
    for key in missing:
        severity = "legacy" if legacy_keys else "error"
        _add_url_contract_issue(result, severity, f"web_replay_check_url_hint missing query param: {key}")

    replay_value = _first_query_value(query, QUEST_REPLAY_RECORD_QUERY_PARAM)
    if replay_value and replay_value != str(payload.get("artifact_path") or ""):
        _add_url_contract_issue(
            result,
            "error",
            "web_replay_check_url_hint replay query must match summary artifact_path",
        )

    qa_value = _first_query_value(query, QUEST_QA_CODE_QUERY_PARAM)
    if qa_value and qa_value != str(payload.get("artifact_code") or ""):
        _add_url_contract_issue(
            result,
            "error",
            "web_replay_check_url_hint qa query must match summary artifact_code",
        )

    code_value = _first_query_value(query, QUEST_RECALL_CODE_QUERY_PARAM)
    if expected_recall_code and code_value and code_value != expected_recall_code:
        _add_url_contract_issue(
            result,
            "error",
            "web_replay_check_url_hint code query must match ReplayRecord recall_code",
        )
    return _finalize_url_contract(result)


def _add_url_contract_issue(result: dict[str, Any], severity: str, message: str) -> None:
    result["issues"].append({"severity": severity, "message": message})


def _finalize_url_contract(result: dict[str, Any]) -> dict[str, Any]:
    severities = {issue["severity"] for issue in result.get("issues", [])}
    if "error" in severities:
        result["status"] = "fail"
    elif "legacy" in severities or "warning" in severities:
        result["status"] = "warn"
    else:
        result["status"] = "pass"
    return result


def _first_query_value(query: dict[str, list[str]], key: str) -> str:
    values = query.get(key) or []
    return str(values[0]) if values else ""


def _viewer_recall_code(value: Any) -> str:
    code = re.sub(r"[^A-Z0-9]+", "", str(value or "").upper())[:4]
    return code if RECALL_CODE_RE.match(code) else ""


def _is_local_filesystem_ref(value: str) -> bool:
    text = value.strip()
    if not text:
        return False
    if WINDOWS_DRIVE_RE.match(text) or WINDOWS_UNC_RE.match(text):
        return True
    parsed = urlparse(text)
    if parsed.scheme:
        return parsed.scheme.lower() == "file"
    if text.startswith("/") and not text.startswith("//"):
        return True
    return "\\" in text and bool(PATHLIKE_BACKSLASH_RE.search(text))


def _is_localhost_url(value: str) -> bool:
    text = value.strip()
    lower = text.lower()
    if not text:
        return False
    if lower.startswith(("localhost:", "127.0.0.1:", "0.0.0.0:", "[::1]:")):
        return True
    parsed = urlparse(text)
    host = (parsed.hostname or "").lower()
    return parsed.scheme in {"http", "https", "ws", "wss"} and host in LOCAL_HOSTS


def _inspect_playcanvas_writeback(record: dict[str, Any]) -> dict[str, Any]:
    explicit_forbidden = False
    violations: list[dict[str, str]] = []
    for path, key, value in _walk_items(record):
        normalized_key = _normalize_key(key)
        normalized_path = _normalize_key(path)
        is_playcanvas_context = "playcanvas" in normalized_path or "playcanvas" in normalized_key
        if is_playcanvas_context and normalized_key in {"mode", "role"}:
            role = _normalize_key(str(value or ""))
            if role and role not in PLAYCANVAS_ALLOWED_ROLES:
                violations.append({"path": path, "value": _value_label(value)})
            continue
        policy_key = normalized_key in PLAYCANVAS_POLICY_KEYS or (
            is_playcanvas_context and normalized_key in PLAYCANVAS_CONTEXT_KEYS
        )
        if not policy_key:
            continue
        state = _policy_state(value)
        if normalized_key in PLAYCANVAS_ENDPOINT_KEYS and _truthy_policy_value(value):
            state = "allowed"
        if state == "forbidden":
            explicit_forbidden = True
        elif state == "allowed":
            violations.append({"path": path, "value": _value_label(value)})
    return {
        "writeback_forbidden_explicit": explicit_forbidden,
        "writeback_violation_count": len(violations),
        "writeback_violations": violations,
    }


def _policy_state(value: Any) -> str:
    if value is False:
        return "forbidden"
    if value is True:
        return "allowed"
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in FALSE_POLICY_VALUES:
            return "forbidden"
        if normalized in TRUE_POLICY_VALUES:
            return "allowed"
    return "unknown"


def _truthy_policy_value(value: Any) -> bool:
    if value in (None, False, "", [], {}):
        return False
    if isinstance(value, str) and value.strip().lower() in FALSE_POLICY_VALUES:
        return False
    return True


def _walk_strings(value: Any, path: str = "$") -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            result.extend(_walk_strings(child, _join_path(path, str(key))))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            result.extend(_walk_strings(child, f"{path}[{index}]"))
    elif isinstance(value, str):
        result.append((path, value))
    return result


def _walk_items(value: Any, path: str = "$", key: str = "") -> list[tuple[str, str, Any]]:
    result: list[tuple[str, str, Any]] = []
    if key:
        result.append((path, key, value))
    if isinstance(value, dict):
        for child_key, child in value.items():
            result.extend(_walk_items(child, _join_path(path, str(child_key)), str(child_key)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            result.extend(_walk_items(child, f"{path}[{index}]", key))
    return result


def _join_path(parent: str, key: str) -> str:
    if key.isidentifier():
        return f"{parent}.{key}"
    return f"{parent}[{json.dumps(key, ensure_ascii=False)}]"


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _value_label(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _print_text_report(result: dict[str, Any]) -> None:
    print(f"[{result['status'].upper()}] {result.get('input_path') or '<payload>'}")
    print(f"mode: {result['mode']}")
    print(f"source: {result['source_type']}")
    print(f"selected variants: {result['selected_variant_count']}")
    print(f"local path leaks: {result['local_path_leak_count']}")
    print(f"localhost urls: {result['localhost_url_count']}")
    if result["web_replay_url_contract"]["checked"]:
        print(f"web replay url: {result['web_replay_url_contract']['status']}")
    print(f"playcanvas write-back forbidden: {result['playcanvas']['writeback_forbidden_explicit']}")
    for reason in result["reasons"]:
        print(f"  fail  {reason}")
    for warning in result["warnings"]:
        print(f"  warn  {warning}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path, help="ReplayRecord JSON or replay QA summary JSON")
    parser.add_argument("--mode", choices=sorted(LOCAL_MODES), default="local", help="Validation strictness")
    parser.add_argument("--report-json", action="store_true", help="Emit a structured JSON report")
    args = parser.parse_args(argv)

    result = validate_replay_public_artifact(args.artifact, mode=args.mode)
    if args.report_json:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        _print_text_report(result)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
