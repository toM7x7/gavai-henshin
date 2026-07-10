"""Validate QA evidence privacy before local or external sharing.

The validator is read-only. It scans qa/ evidence for files and JSON fields
that should not be shared to GitHub or an external PC without redaction.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


CONTRACT_VERSION = "qa-evidence-privacy-validation.v1"
DEFAULT_QA_ROOT = Path("qa")
SHARE_SAFE_CONTRACTS = {
    "mocopi-evidence-share-package.v1",
    "release-stage-manifest.v1",
    "release-stage-manifest.v4",
    "release-stage-manifest.v5",
    "release-stage-manifest-validation.v1",
    "release-stage-manifest-validation.v4",
    "release-stage-manifest-validation.v6",
    "shareable-qa-evidence-manifest.v1",
}
MEDIA_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".mp4", ".mov", ".webm"}
RAW_LOG_SUFFIXES = {".log", ".trace", ".har", ".raw", ".dump"}
RAW_DEBUG_FILENAMES = {
    "adb-devices.txt",
    "adb-reverse.txt",
    "operator-summary.txt",
    "quest-debug-latest.json",
}
SECRET_KEY_RE = re.compile(
    r"(api[_-]?key|client[_-]?secret|secret|password|passwd|authorization|access[_-]?token|refresh[_-]?token|private[_-]?key|bearer)",
    re.IGNORECASE,
)
TOKEN_KEY_RE = re.compile(r"(^|[_-])token($|[_-])", re.IGNORECASE)
PII_KEY_RE = re.compile(r"(email|phone|participant|operator[_-]?name|user[_-]?name|full[_-]?name)", re.IGNORECASE)
LOCAL_URL_RE = re.compile(r"https?://(?:localhost|127\.0\.0\.1|\[?::1\]?)(?::\d+)?[^\s\"']*", re.IGNORECASE)
LOCAL_PATH_RE = re.compile(r"(?:[A-Za-z]:[\\/](?:Users|dev|temp|tmp)[\\/][^\s\"']+|/[Uu]sers/[^\s\"']+|/home/[^\s\"']+)")
SECRET_VALUE_RE = re.compile(
    r"(sk-[A-Za-z0-9_-]{12,}|AIza[0-9A-Za-z_-]{12,}|Bearer\s+[A-Za-z0-9._-]{16,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)",
    re.IGNORECASE,
)
MAX_JSON_SCAN_BYTES = 1024 * 1024


def validate_qa_evidence_privacy(
    qa_root: str | Path = DEFAULT_QA_ROOT,
    *,
    mode: str = "share",
    release_stage_manifest: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(qa_root)
    if mode not in {"local", "share"}:
        raise ValueError("mode must be local or share")

    findings: list[dict[str, Any]] = []
    json_reports: list[dict[str, Any]] = []
    files = sorted(path for path in root.rglob("*") if path.is_file()) if root.exists() else []

    for path in files:
        rel = _rel(root, path)
        findings.extend(_file_findings(path, rel, mode))
        if path.suffix.lower() == ".json":
            json_report, json_findings = _json_safety(path, rel, mode)
            json_reports.append(json_report)
            findings.extend(json_findings)

    release_report = _release_manifest_report(root, release_stage_manifest, mode)
    findings.extend(release_report["findings"])

    blockers = [finding for finding in findings if finding["severity"] == "blocker"]
    warnings = [finding for finding in findings if finding["severity"] == "warn"]
    local_evidence = [finding for finding in findings if finding["severity"] == "local-evidence"]

    return {
        "contract_version": CONTRACT_VERSION,
        "mode": mode,
        "qa_root": root.as_posix(),
        "ok": not blockers,
        "status": "fail" if blockers else "warn" if warnings else "pass",
        "counts": {
            "files_scanned": len(files),
            "json_files": len(json_reports),
            "media_files": sum(1 for finding in findings if finding["code"] == "share-exclude-media"),
            "quest_screenshot_files": sum(1 for finding in findings if finding["code"] == "share-exclude-quest-screenshot"),
            "raw_log_files": sum(1 for finding in findings if finding["code"] == "share-exclude-raw-log"),
            "raw_debug_dumps": sum(1 for finding in findings if finding["code"] == "share-exclude-raw-debug"),
            "secret_key_hits": sum(1 for finding in findings if finding["code"] == "secret-like-json-key"),
            "localhost_hits": sum(1 for finding in findings if finding["code"] in {"localhost-url-share-warning", "localhost-url-local-evidence"}),
            "local_path_hits": sum(1 for finding in findings if finding["code"] in {"local-path-share-warning", "local-path-local-evidence"}),
            "blocker_count": len(blockers),
            "warning_count": len(warnings),
            "local_evidence_count": len(local_evidence),
        },
        "json_manifest_safety": json_reports,
        "release_stage_manifest": release_report["summary"],
        "share_readiness": {
            "ready": mode == "local" or not (blockers or warnings),
            "blockers": blockers,
            "warnings": warnings,
            "local_evidence": local_evidence,
        },
        "findings": findings,
    }


def _file_findings(path: Path, rel: str, mode: str) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    name = path.name.lower()
    findings: list[dict[str, Any]] = []
    if _is_quest_screenshot(name, suffix):
        findings.append(
            _finding(
                code="share-exclude-quest-screenshot",
                severity="warn",
                path=rel,
                message="Quest screenshot/screencap should stay out of GitHub or external-share evidence.",
                recommended_action="keep local or replace with a sanitized JSON manifest summary",
            )
        )
    elif suffix in MEDIA_SUFFIXES:
        findings.append(
            _finding(
                code="share-exclude-media",
                severity="warn",
                path=rel,
                message="Image/video evidence can expose participants, venue, browser state, or generated visuals.",
                recommended_action="do not share by default; use a redacted manifest summary",
            )
        )
    if _is_raw_debug_dump(name):
        findings.append(
            _finding(
                code="share-exclude-raw-debug",
                severity="warn",
                path=rel,
                message="Raw ADB/Quest/operator dump may contain device identifiers or local runtime state.",
                recommended_action="keep local; share boolean readiness and gate label only",
            )
        )
    elif suffix in RAW_LOG_SUFFIXES:
        findings.append(
            _finding(
                code="share-exclude-raw-log",
                severity="warn",
                path=rel,
                message="Raw log/dump files should not be part of external evidence sharing.",
                recommended_action="keep local or convert to a sanitized report",
            )
        )
    return findings


def _json_safety(path: Path, rel: str, mode: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    size = path.stat().st_size
    if size > MAX_JSON_SCAN_BYTES:
        return (
            {
                "path": rel,
                "parseable": False,
                "contract_version": "",
                "safe_manifest": False,
                "notes": ["json file exceeds scan budget"],
            },
            [
                _finding(
                    code="json-too-large-for-share-review",
                    severity="warn",
                    path=rel,
                    message=f"JSON file exceeds the {MAX_JSON_SCAN_BYTES} byte scan budget.",
                    recommended_action="keep local or create a smaller sanitized manifest",
                )
            ],
        )
    try:
        payload = json.loads(_read_json_text(path))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return (
            {
                "path": rel,
                "parseable": False,
                "contract_version": "",
                "safe_manifest": False,
                "notes": [f"invalid json: {exc}"],
            },
            [
                _finding(
                    code="json-parse-error",
                    severity="warn",
                    path=rel,
                    message=f"JSON evidence cannot be parsed: {exc}",
                    recommended_action="keep local until regenerated or manually reviewed",
                )
            ],
        )

    contract_version = str(payload.get("contract_version") or "") if isinstance(payload, dict) else ""
    if contract_version in SHARE_SAFE_CONTRACTS:
        notes = ["known share-safe manifest contract"]
    elif contract_version:
        notes = ["unknown manifest contract; review before sharing"]
        if mode == "share":
            findings.append(
                _finding(
                    code="unknown-json-manifest-contract",
                    severity="warn",
                    path=rel,
                    message=f"JSON contract_version {contract_version} is not in the share-safe allowlist.",
                    recommended_action="share only after redaction review or package into a sanitized manifest",
                )
            )
    else:
        notes = ["no contract_version; treat as raw JSON evidence"]
        if mode == "share":
            findings.append(
                _finding(
                    code="json-no-contract-version",
                    severity="warn",
                    path=rel,
                    message="JSON evidence has no contract_version and may be raw local evidence.",
                    recommended_action="keep local or wrap with a sanitized package manifest",
                )
            )

    findings.extend(_scan_json_value(payload, rel, mode))
    safe_manifest = contract_version in SHARE_SAFE_CONTRACTS and not any(
        finding["path"] == rel and finding["severity"] == "blocker" for finding in findings
    )
    return (
        {
            "path": rel,
            "parseable": True,
            "contract_version": contract_version,
            "safe_manifest": safe_manifest,
            "notes": notes,
        },
        findings,
    )


def _read_json_text(path: Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-16", "utf-16-le", "utf-16-be"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8-sig")


def _scan_json_value(value: Any, rel: str, mode: str, json_path: str = "$") -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            child_path = f"{json_path}.{key_text}"
            findings.extend(_key_findings(key_text, child, rel, child_path, mode))
            findings.extend(_scan_json_value(child, rel, mode, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_scan_json_value(child, rel, mode, f"{json_path}[{index}]"))
    elif isinstance(value, str):
        findings.extend(_string_findings(value, rel, json_path, mode))
    return findings


def _key_findings(key: str, value: Any, rel: str, json_path: str, mode: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    text_value = str(value) if isinstance(value, (str, int, float, bool)) else ""
    if SECRET_KEY_RE.search(key) or _token_key_looks_secret(key, text_value):
        severity = "blocker" if mode == "share" and _value_is_not_placeholder(text_value) else "warn"
        findings.append(
            _finding(
                code="secret-like-json-key",
                severity=severity,
                path=rel,
                json_path=json_path,
                message=f"JSON key '{key}' looks like a secret-bearing field.",
                recommended_action="remove, redact, or replace with a non-secret placeholder before sharing",
            )
        )
    elif PII_KEY_RE.search(key):
        findings.append(
            _finding(
                code="pii-like-json-key",
                severity="warn" if mode == "share" else "local-evidence",
                path=rel,
                json_path=json_path,
                message=f"JSON key '{key}' may contain personal/operator identity.",
                recommended_action="redact or summarize before external sharing",
            )
        )
    if text_value and SECRET_VALUE_RE.search(text_value):
        findings.append(
            _finding(
                code="secret-like-json-value",
                severity="blocker" if mode == "share" else "warn",
                path=rel,
                json_path=json_path,
                message="JSON value matches a secret-like token pattern.",
                recommended_action="remove or rotate the secret before sharing",
            )
        )
    return findings


def _string_findings(value: str, rel: str, json_path: str, mode: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if LOCAL_URL_RE.search(value):
        findings.append(
            _finding(
                code="localhost-url-share-warning" if mode == "share" else "localhost-url-local-evidence",
                severity="warn" if mode == "share" else "local-evidence",
                path=rel,
                json_path=json_path,
                message="localhost/127.0.0.1 URL is valid local evidence but should not be treated as external-share proof.",
                recommended_action="share only a sanitized summary or replace with an approved external endpoint reference",
            )
        )
    if LOCAL_PATH_RE.search(value):
        findings.append(
            _finding(
                code="local-path-share-warning" if mode == "share" else "local-path-local-evidence",
                severity="warn" if mode == "share" else "local-evidence",
                path=rel,
                json_path=json_path,
                message="Local absolute path may expose usernames, machine layout, or non-portable evidence.",
                recommended_action="redact local path or replace with bundle-relative evidence reference",
            )
        )
    if SECRET_VALUE_RE.search(value):
        findings.append(
            _finding(
                code="secret-like-json-value",
                severity="blocker" if mode == "share" else "warn",
                path=rel,
                json_path=json_path,
                message="JSON string matches a secret-like token pattern.",
                recommended_action="remove or rotate the secret before sharing",
            )
        )
    return findings


def _release_manifest_report(
    qa_root: Path,
    release_stage_manifest: str | Path | None,
    mode: str,
) -> dict[str, Any]:
    if not release_stage_manifest:
        return {
            "summary": {"provided": False},
            "findings": [],
        }
    path = Path(release_stage_manifest)
    findings: list[dict[str, Any]] = []
    try:
        manifest = json.loads(_read_json_text(path))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return {
            "summary": {"provided": True, "path": path.as_posix(), "parseable": False},
            "findings": [
                _finding(
                    code="release-stage-manifest-unreadable",
                    severity="warn",
                    path=path.as_posix(),
                    message=f"Release stage manifest could not be read: {exc}",
                    recommended_action="regenerate release stage manifest before share review",
                )
            ],
        }
    sample_paths = _qa_evidence_sample_paths(manifest)
    for sample_path in sample_paths:
        kind = _release_sample_share_risk(sample_path)
        if kind:
            findings.append(
                _finding(
                    code="release-manifest-qa-evidence-unsafe",
                    severity="warn",
                    path=sample_path,
                    message=f"Release stage manifest includes QA evidence sample that should stay local by default: {kind}.",
                    recommended_action="remove from share staging or replace with a sanitized package manifest",
                )
            )
    return {
        "summary": {
            "provided": True,
            "path": path.as_posix(),
            "parseable": True,
            "contract_version": manifest.get("contract_version", "") if isinstance(manifest, dict) else "",
            "qa_evidence_sample_count": len(sample_paths),
            "qa_evidence_samples": sample_paths,
        },
        "findings": findings,
    }


def _qa_evidence_sample_paths(manifest: Any) -> list[str]:
    if not isinstance(manifest, dict):
        return []
    qa_category = manifest.get("categories", {}).get("qa-evidence") if isinstance(manifest.get("categories"), dict) else {}
    samples = qa_category.get("samples") if isinstance(qa_category, dict) else []
    paths: list[str] = []
    if isinstance(samples, list):
        for sample in samples:
            if isinstance(sample, dict) and sample.get("path"):
                paths.append(str(sample["path"]))
            elif isinstance(sample, str):
                paths.append(sample)
    return paths


def _release_sample_share_risk(sample_path: str) -> str:
    lower = sample_path.lower().replace("\\", "/")
    suffix = Path(lower).suffix
    name = Path(lower).name
    if _is_quest_screenshot(name, suffix) or suffix in MEDIA_SUFFIXES:
        return "media-or-screenshot"
    if _is_raw_debug_dump(name) or suffix in RAW_LOG_SUFFIXES or "/logs/" in lower:
        return "raw-log-or-debug-dump"
    return ""


def _is_quest_screenshot(name: str, suffix: str) -> bool:
    return suffix in MEDIA_SUFFIXES and any(token in name for token in ("screencap", "screenshot", "quest-screen"))


def _is_raw_debug_dump(name: str) -> bool:
    return (
        name in RAW_DEBUG_FILENAMES
        or (name.startswith("adb") and Path(name).suffix.lower() in {".txt", ".log", ".json"})
        or ("quest-debug" in name and Path(name).suffix.lower() == ".json")
        or ("raw-dump" in name)
    )


def _token_key_looks_secret(key: str, value: str) -> bool:
    if not TOKEN_KEY_RE.search(key):
        return False
    upper = value.upper().strip()
    if upper.startswith(("MOCOPI", "BODY", "STATIC", "LIVE", "SELF", "CAPTURE")):
        return False
    return len(value.strip()) >= 20 or bool(SECRET_VALUE_RE.search(value))


def _value_is_not_placeholder(value: str) -> bool:
    stripped = value.strip().lower()
    return stripped not in {"", "none", "null", "placeholder", "<redacted>", "redacted", "***", "todo"}


def _finding(
    *,
    code: str,
    severity: str,
    path: str,
    message: str,
    recommended_action: str,
    json_path: str = "",
) -> dict[str, Any]:
    payload = {
        "code": code,
        "severity": severity,
        "path": path,
        "message": message,
        "recommended_action": recommended_action,
    }
    if json_path:
        payload["json_path"] = json_path
    return payload


def _rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _print_text_report(result: dict[str, Any]) -> None:
    print(f"{result['status']} mode={result['mode']} qa_root={result['qa_root']}")
    for finding in result["share_readiness"]["blockers"]:
        print(f"BLOCKER {finding['path']}: {finding['message']}")
    for finding in result["share_readiness"]["warnings"]:
        print(f"WARN {finding['path']}: {finding['message']}")
    for finding in result["share_readiness"]["local_evidence"]:
        print(f"LOCAL {finding['path']}: {finding['message']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--qa-root", type=Path, default=DEFAULT_QA_ROOT, help="QA evidence root, default: qa")
    parser.add_argument("--mode", choices=("local", "share"), default="share", help="Validation mode")
    parser.add_argument("--release-stage-manifest", type=Path, help="Optional release stage manifest JSON")
    parser.add_argument("--report-json", action="store_true", help="Emit a structured JSON report")
    args = parser.parse_args(argv)

    result = validate_qa_evidence_privacy(
        args.qa_root,
        mode=args.mode,
        release_stage_manifest=args.release_stage_manifest,
    )
    if args.report_json:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        _print_text_report(result)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
