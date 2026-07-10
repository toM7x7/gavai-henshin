"""Validate a shareable QA evidence manifest against release staging.

This read-only checker ensures the curated QA evidence list does not recommend
raw/local-only evidence for Git staging and, when provided, does not conflict
with the release stage manifest's qa-evidence bucket.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


CONTRACT_VERSION = "shareable-qa-evidence-manifest-validation.v1"
DEFAULT_MANIFEST = Path("qa/shareable-qa-evidence-latest.json")
RAW_PATH_MARKERS = (
    "qa/logs/",
    "/logs/",
    "screencap",
    "screenshot",
    "quest-screen",
    "adb-devices",
    "adb-reverse",
    "quest-debug-latest",
    "operator-summary",
)
RAW_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".mp4", ".mov", ".webm", ".log", ".trace", ".har", ".raw", ".dump")


def validate_shareable_qa_evidence_manifest(
    manifest: str | Path | dict[str, Any] = DEFAULT_MANIFEST,
    *,
    release_stage_manifest: str | Path | dict[str, Any] | None = None,
    strict: bool = False,
) -> dict[str, Any]:
    shareable, manifest_path = _load_json_with_path(manifest)
    qa_root = Path(str(shareable.get("qa_root") or "qa"))
    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    _validate_manifest_structure(shareable, manifest_path, blockers)
    shareable_files = _list_of_dicts(shareable.get("shareable_files"))
    local_only_files = _list_of_dicts(shareable.get("local_only_files"))
    blocked_files = _list_of_dicts(shareable.get("blocked_files"))
    recommended_paths = sorted(str(path).replace("\\", "/") for path in _string_list(shareable.get("recommended_git_stage_paths")))

    _validate_shareable_file_existence(qa_root, shareable_files, blockers)
    _validate_blocked_files(blocked_files, strict, blockers, warnings)
    _validate_recommended_paths(
        recommended_paths,
        shareable_files,
        local_only_files,
        blocked_files,
        strict,
        blockers,
        warnings,
    )

    release_alignment = _release_alignment(
        release_stage_manifest,
        recommended_paths,
        local_only_files,
        blocked_files,
        strict,
        blockers,
        warnings,
    )

    status = "fail" if blockers else "warn" if warnings else "pass"
    return {
        "contract_version": CONTRACT_VERSION,
        "ok": not blockers,
        "status": status,
        "strict": strict,
        "manifest_path": str(manifest_path) if manifest_path else "",
        "qa_root": qa_root.as_posix(),
        "counts": {
            "shareable_files": len(shareable_files),
            "local_only_files": len(local_only_files),
            "blocked_files": len(blocked_files),
            "recommended_git_stage_paths": len(recommended_paths),
            "blocker_count": len(blockers),
            "warning_count": len(warnings),
        },
        "release_alignment": release_alignment,
        "recommended_git_stage_paths": recommended_paths,
        "blockers": blockers,
        "warnings": warnings,
    }


def _validate_manifest_structure(
    manifest: dict[str, Any],
    manifest_path: Path | None,
    blockers: list[dict[str, Any]],
) -> None:
    if manifest.get("contract_version") != "shareable-qa-evidence-manifest.v1":
        blockers.append(
            _issue(
                code="invalid-contract-version",
                severity="blocker",
                message="Manifest contract_version must be shareable-qa-evidence-manifest.v1.",
                recommended_action="regenerate with tools/export_shareable_qa_evidence_manifest.py",
            )
        )
    if not _list_of_dicts(manifest.get("shareable_files")):
        blockers.append(
            _issue(
                code="shareable-files-empty",
                severity="blocker",
                message="shareable_files must contain at least the curated manifest itself.",
                recommended_action="regenerate the shareable QA evidence manifest after privacy validation",
            )
        )
    if not isinstance(manifest.get("recommended_git_stage_paths"), list):
        blockers.append(
            _issue(
                code="recommended-stage-paths-missing",
                severity="blocker",
                message="recommended_git_stage_paths must be present as a list.",
                recommended_action="regenerate the shareable QA evidence manifest",
            )
        )
    if manifest_path and not manifest_path.exists():
        blockers.append(
            _issue(
                code="manifest-file-missing",
                severity="blocker",
                path=manifest_path.as_posix(),
                message="The shareable QA evidence manifest file does not exist.",
                recommended_action="write qa/shareable-qa-evidence-latest.json before validating it",
            )
        )


def _validate_shareable_file_existence(
    qa_root: Path,
    shareable_files: list[dict[str, Any]],
    blockers: list[dict[str, Any]],
) -> None:
    for item in shareable_files:
        path = str(item.get("path") or "").replace("\\", "/")
        if not path:
            blockers.append(
                _issue(
                    code="shareable-file-path-missing",
                    severity="blocker",
                    message="A shareable_files item is missing path.",
                    recommended_action="regenerate the shareable QA evidence manifest",
                )
            )
            continue
        if not _path_exists(qa_root, path):
            blockers.append(
                _issue(
                    code="shareable-file-missing",
                    severity="blocker",
                    path=path,
                    message="A shareable_files path does not exist under qa_root.",
                    recommended_action="regenerate or remove the stale shareable_files entry",
                )
            )


def _validate_blocked_files(
    blocked_files: list[dict[str, Any]],
    strict: bool,
    blockers: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> None:
    for item in blocked_files:
        path = str(item.get("path") or "")
        reason = str(item.get("reason") or "")
        action = str(item.get("recommended_action") or "")
        if not path or not reason or not action:
            blockers.append(
                _issue(
                    code="blocked-file-not-explicit",
                    severity="blocker",
                    path=path,
                    message="blocked_files entries must include path, reason, and recommended_action.",
                    recommended_action="regenerate from the privacy validator so blocked evidence is explicit",
                )
            )
        elif strict:
            blockers.append(
                _issue(
                    code="blocked-files-present",
                    severity="blocker",
                    path=path,
                    message="blocked_files is non-empty in strict mode.",
                    recommended_action=action,
                )
            )
        else:
            warnings.append(
                _issue(
                    code="blocked-files-present",
                    severity="warn",
                    path=path,
                    message="blocked_files is non-empty; this is allowed only because each entry is explicit.",
                    recommended_action=action,
                )
            )


def _validate_recommended_paths(
    recommended_paths: list[str],
    shareable_files: list[dict[str, Any]],
    local_only_files: list[dict[str, Any]],
    blocked_files: list[dict[str, Any]],
    strict: bool,
    blockers: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> None:
    shareable_stage_paths = {
        _normalize_stage_path(str(item.get("git_stage_path") or item.get("path") or ""))
        for item in shareable_files
        if item.get("git_stage_path") or item.get("path")
    }
    local_stage_paths = {_normalize_stage_path(str(item.get("path") or "")) for item in local_only_files}
    blocked_stage_paths = {_normalize_stage_path(str(item.get("path") or "")) for item in blocked_files}

    for path in recommended_paths:
        normalized = _normalize_stage_path(path)
        if not normalized:
            blockers.append(
                _issue(
                    code="recommended-stage-path-empty",
                    severity="blocker",
                    message="recommended_git_stage_paths contains an empty path.",
                    recommended_action="remove empty stage path entries",
                )
            )
            continue
        if _is_raw_or_local_stage_path(normalized):
            blockers.append(
                _issue(
                    code="recommended-stage-path-raw",
                    severity="blocker",
                    path=normalized,
                    message="recommended_git_stage_paths contains raw/local QA evidence.",
                    recommended_action="remove raw evidence and stage only curated QA JSON manifests",
                )
            )
        if normalized in local_stage_paths or normalized.removeprefix("qa/") in local_stage_paths:
            blockers.append(
                _issue(
                    code="recommended-stage-path-local-only",
                    severity="blocker",
                    path=normalized,
                    message="recommended_git_stage_paths includes a local_only_files path.",
                    recommended_action="remove local-only evidence from recommended_git_stage_paths",
                )
            )
        if normalized in blocked_stage_paths or normalized.removeprefix("qa/") in blocked_stage_paths:
            blockers.append(
                _issue(
                    code="recommended-stage-path-blocked",
                    severity="blocker",
                    path=normalized,
                    message="recommended_git_stage_paths includes a blocked_files path.",
                    recommended_action="remove blocked evidence from recommended_git_stage_paths",
                )
            )
        if normalized not in shareable_stage_paths:
            issue = _issue(
                code="recommended-stage-path-not-shareable",
                severity="blocker" if strict else "warn",
                path=normalized,
                message="recommended_git_stage_paths contains a path not present in shareable_files.",
                recommended_action="regenerate the manifest so recommended paths derive from shareable_files",
            )
            (blockers if strict else warnings).append(issue)


def _release_alignment(
    release_stage_manifest: str | Path | dict[str, Any] | None,
    recommended_paths: list[str],
    local_only_files: list[dict[str, Any]],
    blocked_files: list[dict[str, Any]],
    strict: bool,
    blockers: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> dict[str, Any]:
    if not release_stage_manifest:
        return {"provided": False}
    release_manifest, release_path = _load_json_with_path(release_stage_manifest)
    qa_samples = _category_sample_paths(release_manifest, "qa-evidence")
    local_samples = _category_sample_paths(release_manifest, "local-qa-artifact")
    recommended = {_normalize_stage_path(path) for path in recommended_paths}
    local_only = {_normalize_stage_path(str(item.get("path") or "")) for item in local_only_files}
    blocked = {_normalize_stage_path(str(item.get("path") or "")) for item in blocked_files}

    unsafe_qa_samples: list[str] = []
    unknown_qa_samples: list[str] = []
    recommended_missing_from_release: list[str] = []
    recommended_marked_local: list[str] = []

    for sample in qa_samples:
        normalized = _normalize_stage_path(sample)
        if _is_raw_or_local_stage_path(normalized) or normalized in local_only or normalized.removeprefix("qa/") in local_only:
            unsafe_qa_samples.append(normalized)
        elif normalized in blocked or normalized.removeprefix("qa/") in blocked:
            unsafe_qa_samples.append(normalized)
        elif normalized not in recommended:
            unknown_qa_samples.append(normalized)

    for path in recommended:
        if qa_samples and path not in {_normalize_stage_path(sample) for sample in qa_samples}:
            recommended_missing_from_release.append(path)
        if path in {_normalize_stage_path(sample) for sample in local_samples}:
            recommended_marked_local.append(path)

    for path in unsafe_qa_samples:
        blockers.append(
            _issue(
                code="release-qa-evidence-unsafe",
                severity="blocker",
                path=path,
                message="release stage manifest qa-evidence includes raw/local/blocked evidence.",
                recommended_action="move this path to local-qa-artifact or remove it from release staging",
            )
        )
    for path in recommended_marked_local:
        blockers.append(
            _issue(
                code="release-marks-recommended-path-local",
                severity="blocker",
                path=path,
                message="shareable manifest recommends a path that release manifest marks local-qa-artifact.",
                recommended_action="regenerate one of the manifests so the path has one classification",
            )
        )
    for path in unknown_qa_samples:
        issue = _issue(
            code="release-qa-evidence-not-recommended",
            severity="blocker" if strict else "warn",
            path=path,
            message="release stage manifest qa-evidence includes a path absent from recommended_git_stage_paths.",
            recommended_action="add it through the shareable QA evidence exporter or remove it from qa-evidence",
        )
        (blockers if strict else warnings).append(issue)
    for path in recommended_missing_from_release:
        issue = _issue(
            code="recommended-path-missing-from-release-qa",
            severity="blocker" if strict else "warn",
            path=path,
            message="recommended_git_stage_paths includes a QA path not present in release manifest qa-evidence samples.",
            recommended_action="regenerate release stage manifest after exporting shareable QA evidence",
        )
        (blockers if strict else warnings).append(issue)

    return {
        "provided": True,
        "path": str(release_path) if release_path else "",
        "contract_version": release_manifest.get("contract_version", ""),
        "qa_evidence_paths": sorted({_normalize_stage_path(path) for path in qa_samples}),
        "local_qa_artifact_paths": sorted({_normalize_stage_path(path) for path in local_samples}),
        "unsafe_qa_evidence_paths": sorted(set(unsafe_qa_samples)),
        "qa_evidence_not_recommended": sorted(set(unknown_qa_samples)),
        "recommended_missing_from_release_qa": sorted(set(recommended_missing_from_release)),
        "recommended_marked_local": sorted(set(recommended_marked_local)),
    }


def _category_sample_paths(manifest: dict[str, Any], category: str) -> list[str]:
    category_value = manifest.get("categories", {}).get(category) if isinstance(manifest.get("categories"), dict) else {}
    samples = category_value.get("samples") if isinstance(category_value, dict) else []
    paths: list[str] = []
    if isinstance(samples, list):
        for sample in samples:
            if isinstance(sample, dict) and sample.get("path"):
                paths.append(str(sample["path"]))
            elif isinstance(sample, str):
                paths.append(sample)
    return paths


def _path_exists(qa_root: Path, rel: str) -> bool:
    candidates = []
    path = Path(rel)
    if path.is_absolute():
        candidates.append(path)
    candidates.append(qa_root / rel)
    if rel.startswith("qa/"):
        candidates.append(qa_root.parent / rel)
    return any(candidate.exists() for candidate in candidates)


def _is_raw_or_local_stage_path(path: str) -> bool:
    lower = path.lower().replace("\\", "/")
    return any(marker in lower for marker in RAW_PATH_MARKERS) or lower.endswith(RAW_SUFFIXES)


def _normalize_stage_path(path: str) -> str:
    value = path.replace("\\", "/").strip()
    if not value:
        return ""
    if value.startswith("./"):
        value = value[2:]
    if not value.startswith("qa/") and not value.startswith("/"):
        value = f"qa/{value}"
    return value


def _load_json_with_path(source: str | Path | dict[str, Any]) -> tuple[dict[str, Any], Path | None]:
    if isinstance(source, dict):
        return source, None
    path = Path(source)
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload, path


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in value if str(item).strip()] if isinstance(value, list) else []


def _issue(
    *,
    code: str,
    severity: str,
    message: str,
    recommended_action: str,
    path: str = "",
) -> dict[str, Any]:
    payload = {
        "code": code,
        "severity": severity,
        "message": message,
        "recommended_action": recommended_action,
    }
    if path:
        payload["path"] = path
    return payload


def _print_text_report(result: dict[str, Any]) -> None:
    print(f"{result['status']} strict={result['strict']}")
    for blocker in result["blockers"]:
        print(f"BLOCKER {blocker.get('path', '')}: {blocker['message']}")
    for warning in result["warnings"]:
        print(f"WARN {warning.get('path', '')}: {warning['message']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help=f"Shareable QA manifest, default: {DEFAULT_MANIFEST}")
    parser.add_argument("--release-stage-manifest", type=Path, help="Optional release stage manifest JSON")
    parser.add_argument("--strict", action="store_true", help="Treat warnings and blocked_files as blockers")
    parser.add_argument("--report-json", action="store_true", help="Emit structured JSON")
    args = parser.parse_args(argv)

    result = validate_shareable_qa_evidence_manifest(
        args.manifest,
        release_stage_manifest=args.release_stage_manifest,
        strict=args.strict,
    )
    if args.report_json:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        _print_text_report(result)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
