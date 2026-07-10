"""Validate the release stage manifest before GitHub push.

The checker is read-only. It cross-checks the stage manifest produced by
tools/export_release_stage_manifest.py against the exhibition package validator
report when one is provided.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import list_release_stage_candidates as stage_candidates


CONTRACT_VERSION = "release-stage-manifest-validation.v6"
EXPECTED_MANIFEST_CONTRACT_VERSION = "release-stage-manifest.v5"
DEFAULT_MANIFEST = Path("qa/release-stage-manifest-latest.json")
PACKAGE_UNTRACKED_SAMPLE_LIMIT = 20
REQUIRED_CATEGORIES = stage_candidates.CATEGORIES


def _decode_json_bytes(data: bytes) -> Any:
    for encoding in ("utf-8-sig", "utf-16", "utf-16-le", "utf-16-be"):
        try:
            return json.loads(data.decode(encoding))
        except UnicodeDecodeError:
            continue
    return json.loads(data.decode("utf-8", errors="replace"))


def _read_json(path_or_stdin: str | Path, *, stdin_text: str | None = None) -> Any:
    if str(path_or_stdin) == "-":
        return json.loads(sys.stdin.read() if stdin_text is None else stdin_text)
    return _decode_json_bytes(Path(path_or_stdin).read_bytes())


def _category(manifest: dict[str, Any], category: str) -> dict[str, Any]:
    value = manifest.get("categories", {}).get(category)
    return value if isinstance(value, dict) else {}


def _category_count(manifest: dict[str, Any], category: str) -> int:
    category_value = _category(manifest, category)
    if "count" in category_value:
        return int(category_value.get("count") or 0)
    return int(manifest.get("counts", {}).get("by_category", {}).get(category, 0) or 0)


def _issue(
    *,
    code: str,
    severity: str,
    message: str,
    category: str = "",
    count: int = 0,
    recommended_action: str = "",
) -> dict[str, Any]:
    return {
        "code": code,
        "severity": severity,
        "category": category,
        "count": count,
        "message": message,
        "recommended_action": recommended_action,
    }


def _sample_paths(paths: list[str], limit: int = PACKAGE_UNTRACKED_SAMPLE_LIMIT) -> list[str]:
    return paths[: max(0, limit)]


def _manifest_stage_policy(manifest: dict[str, Any], category: str) -> str:
    return str(_category(manifest, category).get("stage_policy") or "")


def _manifest_recommended_action(manifest: dict[str, Any], category: str) -> str:
    return str(_category(manifest, category).get("recommended_action") or "")


def _manifest_sample_paths(manifest: dict[str, Any], category: str) -> list[str]:
    return [
        entry["path"]
        for entry in _manifest_sample_entries(manifest, category)
        if entry.get("path")
    ]


def _manifest_sample_entries(manifest: dict[str, Any], category: str) -> list[dict[str, str]]:
    samples = _category(manifest, category).get("samples")
    if not isinstance(samples, list):
        return []
    entries: list[dict[str, str]] = []
    for sample in samples:
        if isinstance(sample, dict) and sample.get("path"):
            entries.append(
                {
                    "path": str(sample["path"]),
                    "status": str(sample.get("status") or "??"),
                }
            )
        elif isinstance(sample, str):
            entries.append({"path": sample, "status": "??"})
    return entries


def _stage_decision_categories(manifest: dict[str, Any], group_name: str) -> set[str]:
    stage_decision = manifest.get("stage_decision")
    if not isinstance(stage_decision, dict):
        return set()
    group = stage_decision.get(group_name)
    if not isinstance(group, dict):
        return set()
    categories = group.get("categories")
    if not isinstance(categories, list):
        return set()
    return {str(category) for category in categories}


def _action_says_do_not_stage(action: str) -> bool:
    lowered = action.strip().lower()
    return "do not stage" in lowered or "do-not-stage" in lowered


def _package_categories(entry: dict[str, Any]) -> list[str]:
    categories = entry.get("categories")
    if not isinstance(categories, list):
        return []
    return sorted(str(category) for category in categories)


def _group_add(groups: dict[str, dict[str, Any]], category: str, entry: dict[str, Any]) -> None:
    group = groups.setdefault(
        category,
        {
            "count": 0,
            "paths_sample": [],
            "package_categories": {},
            "recommended_action": entry["recommended_action"],
            "stage_policy": entry["stage_policy"],
        },
    )
    group["count"] += 1
    if len(group["paths_sample"]) < PACKAGE_UNTRACKED_SAMPLE_LIMIT:
        group["paths_sample"].append(entry["path"])
    for package_category in entry["package_categories"]:
        counts = group["package_categories"]
        counts[package_category] = counts.get(package_category, 0) + 1


def _package_untracked_alignment(manifest: dict[str, Any], package_report: dict[str, Any]) -> dict[str, Any]:
    raw_entries = package_report.get("untracked")
    entries = raw_entries if isinstance(raw_entries, list) else []
    detailed_entries: list[dict[str, Any]] = []
    recommended_stage_groups: dict[str, dict[str, Any]] = {}
    manual_review_groups: dict[str, dict[str, Any]] = {}

    for entry in entries:
        if not isinstance(entry, dict) or not entry.get("path"):
            continue
        path = str(entry["path"])
        category, reason, default_action = stage_candidates.classify_path(path, "??")
        stage_policy = _manifest_stage_policy(manifest, category) or default_action
        recommended_action = _manifest_recommended_action(manifest, category) or default_action
        detail = {
            "path": path,
            "package_categories": _package_categories(entry),
            "stage_category": category,
            "stage_policy": stage_policy,
            "recommended_action": recommended_action,
            "classifier_reason": reason,
            "package_reason": str(entry.get("reason") or ""),
        }
        detailed_entries.append(detail)
        if stage_policy == "stage-candidate" or category in {"release-critical", "operator-docs", "armor-assets"}:
            _group_add(recommended_stage_groups, category, detail)
        else:
            _group_add(manual_review_groups, category, detail)

    return {
        "required_untracked_count": int(package_report.get("untracked_count") or len(detailed_entries)),
        "tracked_candidate_count": int(package_report.get("tracked_candidate_count") or 0),
        "required_untracked_paths_sample": detailed_entries[:PACKAGE_UNTRACKED_SAMPLE_LIMIT],
        "recommended_stage_groups": recommended_stage_groups,
        "manual_review_groups": manual_review_groups,
        "sample_limit": PACKAGE_UNTRACKED_SAMPLE_LIMIT,
        "unsampled_required_untracked_count": max(0, len(detailed_entries) - PACKAGE_UNTRACKED_SAMPLE_LIMIT),
    }


def _qa_json_paths(repo_root: Path) -> list[str]:
    qa_root = repo_root / "qa"
    if not qa_root.is_dir():
        return []
    roots = [qa_root]
    replay_root = qa_root / "replay"
    if replay_root.is_dir():
        roots.append(replay_root)
    return sorted(
        {
            path.relative_to(repo_root).as_posix()
            for root in roots
            for path in root.glob("*.json")
            if path.is_file()
        }
    )


def _qa_json_paths_by_category(repo_root: Path) -> dict[str, list[str]]:
    grouped = {"qa-evidence": [], "local-qa-artifact": []}
    for path in _qa_json_paths(repo_root):
        category, _reason, _action = stage_candidates.classify_path(path, "??")
        if category in grouped:
            grouped[category].append(path)
    return grouped


def _push_readiness_blocker_codes(manifest: dict[str, Any]) -> set[str]:
    readiness = manifest.get("push_readiness") if isinstance(manifest.get("push_readiness"), dict) else {}
    blockers = readiness.get("blockers") if isinstance(readiness.get("blockers"), list) else []
    return {str(item.get("code")) for item in blockers if isinstance(item, dict)}


def _validate_stage_decision_contract(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    stage_decision = manifest.get("stage_decision")
    if not isinstance(stage_decision, dict):
        return [
            _issue(
                code="stage-decision-missing",
                severity="blocker",
                message="Manifest is missing the stage_decision machine-readable staging map.",
                recommended_action="regenerate the release stage manifest with the current exporter",
            )
        ]

    expected = {
        "stage_candidates": set(stage_candidates.STAGE_CANDIDATE_CATEGORIES),
        "manual_review": set(stage_candidates.MANUAL_REVIEW_CATEGORIES),
        "do_not_stage": set(stage_candidates.DO_NOT_STAGE_CATEGORIES),
    }
    for group_name, expected_categories in expected.items():
        actual = _stage_decision_categories(manifest, group_name)
        if actual != expected_categories:
            blockers.append(
                _issue(
                    code=f"stage-decision-{group_name}-categories-invalid",
                    severity="blocker",
                    message=f"stage_decision.{group_name}.categories does not match the classifier contract.",
                    category=group_name,
                    count=len(actual),
                    recommended_action="regenerate the release stage manifest with the current exporter",
                )
            )

    unsafe_stageable = (
        _stage_decision_categories(manifest, "stage_candidates")
        & set(stage_candidates.DO_NOT_STAGE_CATEGORIES)
    )
    if unsafe_stageable:
        blockers.append(
            _issue(
                code="stage-decision-unsafe-category-stageable",
                severity="blocker",
                category="stage_candidates",
                count=len(unsafe_stageable),
                message="stage_decision.stage_candidates includes do-not-stage categories.",
                recommended_action="regenerate the manifest before any GitHub staging",
            )
        )
    return blockers


def _validate_category_policy_contract(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    for category in stage_candidates.DO_NOT_STAGE_CATEGORIES:
        policy = _manifest_stage_policy(manifest, category)
        action = _manifest_recommended_action(manifest, category)
        if policy != "do-not-stage":
            blockers.append(
                _issue(
                    code=f"{category}-stage-policy-invalid",
                    severity="blocker",
                    category=category,
                    message=f"{category} must have stage_policy=do-not-stage.",
                    recommended_action="regenerate the manifest with the current exporter",
                )
            )
        if not _action_says_do_not_stage(action):
            blockers.append(
                _issue(
                    code=f"{category}-action-invalid",
                    severity="blocker",
                    category=category,
                    message=f"{category} recommended_action must explicitly say not to stage.",
                    recommended_action="regenerate the manifest with the current exporter",
                )
            )

    qa_policy = _manifest_stage_policy(manifest, "qa-evidence")
    qa_action = _manifest_recommended_action(manifest, "qa-evidence")
    if qa_policy == "stage-candidate":
        blockers.append(
            _issue(
                code="qa-evidence-stage-policy-too-broad",
                severity="blocker",
                category="qa-evidence",
                message="qa-evidence must not be a normal stage-candidate category.",
                recommended_action="regenerate the manifest so QA evidence stays manual/shareable-gated",
            )
        )
    if "shareable" not in qa_action.lower():
        blockers.append(
            _issue(
                code="qa-evidence-action-not-shareable-gated",
                severity="blocker",
                category="qa-evidence",
                message="qa-evidence recommended_action must reference the shareable QA gate.",
                recommended_action="regenerate the manifest with the current exporter",
            )
        )

    return blockers


def _validate_high_risk_sample_classification(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    expected_categories = (
        "qa-evidence",
        "local-qa-artifact",
        "generated-artifact",
        "user-feedback-media",
        "local-workspace",
    )
    for category in expected_categories:
        for sample in _manifest_sample_entries(manifest, category):
            path = sample["path"]
            actual_category, reason, _action = stage_candidates.classify_path(path, sample["status"])
            if actual_category != category:
                blockers.append(
                    _issue(
                        code=f"{category}-sample-classifier-mismatch",
                        severity="blocker",
                        category=category,
                        message=(
                            f"Manifest sample {path} is in {category}, but the current classifier "
                            f"maps it to {actual_category}: {reason}"
                        ),
                        recommended_action="regenerate the manifest before staging or fix the classifier rule",
                    )
                )
    return blockers


def _validate_manifest_structure(
    manifest: dict[str, Any],
    *,
    repo_root: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    categories = manifest.get("categories") if isinstance(manifest.get("categories"), dict) else {}
    counts = manifest.get("counts", {}).get("by_category", {}) if isinstance(manifest.get("counts"), dict) else {}

    if manifest.get("contract_version") != EXPECTED_MANIFEST_CONTRACT_VERSION:
        blockers.append(
            _issue(
                code="manifest-contract-version-stale",
                severity="blocker",
                message=(
                    f"Manifest contract_version must be {EXPECTED_MANIFEST_CONTRACT_VERSION} "
                    "for the current release stage validator."
                ),
                recommended_action="regenerate the release stage manifest with tools/export_release_stage_manifest.py",
            )
        )

    for category in REQUIRED_CATEGORIES:
        if category not in categories:
            blockers.append(
                _issue(
                    code=f"missing-category-{category}",
                    severity="blocker",
                    category=category,
                    message=f"Manifest is missing the {category} category.",
                    recommended_action="regenerate the release stage manifest with the current exporter",
                )
            )
        if category not in counts:
            blockers.append(
                _issue(
                    code=f"missing-count-{category}",
                    severity="blocker",
                    category=category,
                    message=f"Manifest counts.by_category is missing {category}.",
                    recommended_action="regenerate the release stage manifest with the current exporter",
                )
            )

    blockers.extend(_validate_stage_decision_contract(manifest))
    blockers.extend(_validate_category_policy_contract(manifest))
    blockers.extend(_validate_high_risk_sample_classification(manifest))

    release_critical_count = _category_count(manifest, "release-critical")
    if release_critical_count <= 0:
        blockers.append(
            _issue(
                code="release-critical-count-not-positive",
                severity="blocker",
                category="release-critical",
                count=release_critical_count,
                message="release-critical count must be explicitly greater than zero for a push review.",
                recommended_action="regenerate from the dirty worktree or confirm the release branch has no pending runtime candidates",
            )
        )

    ambiguous_count = _category_count(manifest, "ambiguous")
    if ambiguous_count:
        blocker_codes = _push_readiness_blocker_codes(manifest)
        if "ambiguous-changes-present" not in blocker_codes:
            blockers.append(
                _issue(
                    code="ambiguous-count-not-blocking",
                    severity="blocker",
                    category="ambiguous",
                    count=ambiguous_count,
                    message="Manifest has ambiguous paths but does not mark them as a push blocker.",
                    recommended_action="regenerate the manifest with the current exporter",
                )
            )
        blockers.append(
            _issue(
                code="ambiguous-changes-present",
                severity="blocker",
                category="ambiguous",
                count=ambiguous_count,
                message="Ambiguous paths must be resolved or explicitly left unstaged before GitHub push.",
                recommended_action="resolve ambiguous files by name before staging",
            )
        )

    generated = _category(manifest, "generated-artifact")
    generated_policy = str(generated.get("stage_policy") or "").strip().lower()
    generated_action = str(generated.get("recommended_action") or "").strip().lower()
    if generated_policy != "do-not-stage":
        blockers.append(
            _issue(
                code="generated-artifact-stage-policy-invalid",
                severity="blocker",
                category="generated-artifact",
                message="generated-artifact must have stage_policy=do-not-stage.",
                recommended_action="regenerate the manifest with the current exporter",
            )
        )
    if "do not stage" not in generated_action and "do-not-stage" not in generated_action:
        blockers.append(
            _issue(
                code="generated-artifact-action-invalid",
                severity="blocker",
                category="generated-artifact",
                message="generated-artifact recommended_action must explicitly say not to stage.",
                recommended_action="regenerate the manifest with the current exporter",
            )
        )

    qa_paths_by_category = _qa_json_paths_by_category(repo_root)
    curated_qa_paths = qa_paths_by_category["qa-evidence"]
    local_qa_paths = qa_paths_by_category["local-qa-artifact"]
    qa_count = _category_count(manifest, "qa-evidence")
    local_qa_count = _category_count(manifest, "local-qa-artifact")
    if "qa-evidence" in categories and curated_qa_paths and qa_count == 0:
        warnings.append(
            _issue(
                code="qa-json-present-but-no-qa-evidence-candidates",
                severity="warn",
                category="qa-evidence",
                count=len(curated_qa_paths),
                message="Shareable QA evidence manifest files exist locally, but the release stage manifest has no qa-evidence candidates.",
                recommended_action="regenerate the release stage manifest after exporting shareable QA evidence",
            )
        )
    if "local-qa-artifact" in categories and local_qa_paths and local_qa_count == 0:
        warnings.append(
            _issue(
                code="local-qa-json-present-but-no-local-artifact-candidates",
                severity="warn",
                category="local-qa-artifact",
                count=len(local_qa_paths),
                message="Raw or privacy-unvalidated QA JSON files exist locally, but the manifest has no local-qa-artifact candidates.",
                recommended_action="regenerate the stage manifest or keep these QA reports unstaged outside the release package",
            )
        )

    return blockers, warnings


def _validate_package_alignment(
    manifest: dict[str, Any],
    package_report: dict[str, Any],
    *,
    strict: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    alignment = _package_untracked_alignment(manifest, package_report)
    missing_count = int(package_report.get("missing_count") or 0)
    pattern_gap_count = int(package_report.get("pattern_gap_count") or 0)
    untracked_count = int(package_report.get("untracked_count") or 0)
    tracked_candidate_count = int(package_report.get("tracked_candidate_count") or 0)
    required_stage_count = sum(
        _category_count(manifest, category)
        for category in ("release-critical", "operator-docs", "armor-assets")
    )

    if missing_count:
        blockers.append(
            _issue(
                code="package-report-missing-required-files",
                severity="blocker",
                count=missing_count,
                message="Package validator reports missing required release files.",
                recommended_action="fix missing package inputs before staging",
            )
        )
    if pattern_gap_count:
        blockers.append(
            _issue(
                code="package-report-pattern-gaps",
                severity="blocker",
                count=pattern_gap_count,
                message="Package validator reports required glob/count gaps.",
                recommended_action="fix package asset/schema gaps before staging",
            )
        )
    if untracked_count:
        issue = _issue(
            code="package-report-untracked-required-files",
            severity="blocker",
            count=untracked_count,
            message="Package validator reports release-required files that exist but are not tracked by git.",
            recommended_action="stage the required files or intentionally produce a separately reviewed local snapshot",
        )
        issue.update(
            {
                "required_untracked_paths_sample": alignment["required_untracked_paths_sample"],
                "recommended_stage_groups": alignment["recommended_stage_groups"],
                "manual_review_groups": alignment["manual_review_groups"],
                "unsampled_required_untracked_count": alignment["unsampled_required_untracked_count"],
            }
        )
        blockers.append(issue)

    tolerance = max(25, int(max(tracked_candidate_count, 1) * 0.20))
    if untracked_count and required_stage_count + tolerance < untracked_count:
        issue = _issue(
            code="package-untracked-count-exceeds-manifest-stage-candidates",
            severity="blocker" if strict else "warn",
            count=untracked_count - required_stage_count,
            message=(
                "Package validator untracked_count is much larger than the manifest "
                "release-critical/operator-docs/armor-assets candidate total."
            ),
            recommended_action="regenerate both reports from the same worktree before push review",
        )
        (blockers if strict else warnings).append(issue)

    if tracked_candidate_count and required_stage_count > tracked_candidate_count + tolerance:
        issue = _issue(
            code="manifest-stage-candidates-exceed-package-tracked-candidates",
            severity="blocker" if strict else "warn",
            count=required_stage_count - tracked_candidate_count,
            message=(
                "Manifest required stage candidates are much larger than the package "
                "validator tracked_candidate_count."
            ),
            recommended_action="inspect whether docs/tools/tests outside package validator scope explain the difference",
        )
        (blockers if strict else warnings).append(issue)

    return blockers, warnings, alignment


def validate_manifest_payload(
    manifest: dict[str, Any] | None,
    *,
    repo_root: Path,
    manifest_path: str,
    package_report: dict[str, Any] | None = None,
    package_report_path: str = "",
    strict: bool = False,
) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    package_alignment: dict[str, Any] = {}
    qa_paths = _qa_json_paths(repo_root)
    qa_paths_by_category = _qa_json_paths_by_category(repo_root)

    if manifest is None:
        blockers.append(
            _issue(
                code="manifest-missing",
                severity="blocker",
                message=f"Release stage manifest was not found: {manifest_path}",
                recommended_action="run tools/export_release_stage_manifest.py --out qa/release-stage-manifest-latest.json",
            )
        )
        if qa_paths:
            blockers.append(
                _issue(
                    code="qa-evidence-present-without-stage-manifest",
                    severity="blocker",
                    category="qa-evidence",
                    count=len(qa_paths),
                    message="QA JSON evidence exists, but the release stage manifest has not been generated.",
                    recommended_action="generate the stage manifest before deciding whether to stage QA evidence",
                )
            )
        manifest_counts: dict[str, Any] = {}
    else:
        structure_blockers, structure_warnings = _validate_manifest_structure(manifest, repo_root=repo_root)
        blockers.extend(structure_blockers)
        warnings.extend(structure_warnings)
        manifest_counts = manifest.get("counts", {}) if isinstance(manifest.get("counts"), dict) else {}

    if manifest is not None and package_report is not None:
        package_blockers, package_warnings, package_alignment = _validate_package_alignment(
            manifest,
            package_report,
            strict=strict,
        )
        blockers.extend(package_blockers)
        warnings.extend(package_warnings)

    strict_warning_failure = bool(strict and warnings)
    ok = not blockers and not strict_warning_failure
    return {
        "contract_version": CONTRACT_VERSION,
        "read_only": True,
        "strict": strict,
        "ok": ok,
        "status": "fail" if blockers or strict_warning_failure else "warn" if warnings else "pass",
        "repo_root": repo_root.resolve().as_posix(),
        "inputs": {
            "manifest": manifest_path,
            "package_report": package_report_path,
            "package_report_loaded": package_report is not None,
        },
        "manifest_counts": manifest_counts,
        "package_report_counts": {
            "missing_count": package_report.get("missing_count") if package_report else None,
            "pattern_gap_count": package_report.get("pattern_gap_count") if package_report else None,
            "untracked_count": package_report.get("untracked_count") if package_report else None,
            "tracked_candidate_count": package_report.get("tracked_candidate_count") if package_report else None,
        },
        "package_manifest_alignment": package_alignment,
        "local_qa_json_count": len(qa_paths),
        "local_qa_json_samples": qa_paths[:5],
        "local_qa_json_by_category": {
            category: paths[:5]
            for category, paths in qa_paths_by_category.items()
        },
        "strict_warning_failure": strict_warning_failure,
        "blockers": blockers,
        "warnings": warnings,
        "notes": [
            "This checker is read-only and never stages, commits, or pushes files.",
            "A passing report means the manifests are internally consistent, not that the staged diff has been reviewed.",
        ],
    }


def _print_text_report(result: dict[str, Any]) -> None:
    print(f"[{result['status'].upper()}] release stage manifest: {result['inputs']['manifest']}")
    package_report = result["inputs"].get("package_report") or "not provided"
    print(f"package_report={package_report} strict={str(result['strict']).lower()}")
    for issue in result["blockers"]:
        print(f"  blocker {issue['code']}: {issue['message']}")
        if issue["code"] == "package-report-untracked-required-files":
            for group, detail in issue.get("recommended_stage_groups", {}).items():
                print(f"           stage {group}: {detail['count']} path(s)")
                for path in detail.get("paths_sample", [])[:5]:
                    print(f"             - {path}")
            for group, detail in issue.get("manual_review_groups", {}).items():
                print(f"           manual {group}: {detail['count']} path(s)")
                for path in detail.get("paths_sample", [])[:5]:
                    print(f"             - {path}")
    for issue in result["warnings"]:
        print(f"  warn    {issue['code']}: {issue['message']}")


def _load_optional_json(path_value: str | None, *, repo_root: Path) -> tuple[dict[str, Any] | None, str]:
    if not path_value:
        return None, ""
    path = Path(path_value)
    if not path.is_absolute():
        path = repo_root / path
    if not path.is_file():
        raise FileNotFoundError(path_value)
    payload = _read_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path_value} must contain a JSON object")
    return payload, path.as_posix()


def main(argv: list[str] | None = None, *, stdin_text: str | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."), help="Git worktree root")
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST.as_posix(), help="Manifest JSON path, or '-' for stdin")
    parser.add_argument("--package-report", help="Optional qa/exhibition_release_package_latest.json path")
    parser.add_argument("--report-json", action="store_true", help="Emit structured JSON")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as failure")
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    manifest: dict[str, Any] | None = None
    manifest_path = args.manifest
    if args.manifest == "-":
        payload = _read_json("-", stdin_text=stdin_text)
        if not isinstance(payload, dict):
            parser.error("--manifest - must contain a JSON object")
        manifest = payload
        manifest_path = "<stdin>"
    else:
        path = Path(args.manifest)
        if not path.is_absolute():
            path = repo_root / path
        if path.is_file():
            payload = _read_json(path)
            if not isinstance(payload, dict):
                parser.error(f"{args.manifest} must contain a JSON object")
            manifest = payload
            manifest_path = path.as_posix()

    try:
        package_report, package_report_path = _load_optional_json(args.package_report, repo_root=repo_root)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        result = validate_manifest_payload(
            manifest,
            repo_root=repo_root,
            manifest_path=manifest_path,
            strict=args.strict,
        )
        result["blockers"].append(
            _issue(
                code="package-report-unreadable",
                severity="blocker",
                message=f"Package report could not be loaded: {exc}",
                recommended_action="rerun tools/validate_exhibition_release_package.py --report-json",
            )
        )
        result["ok"] = False
        result["status"] = "fail"
    else:
        result = validate_manifest_payload(
            manifest,
            repo_root=repo_root,
            manifest_path=manifest_path,
            package_report=package_report,
            package_report_path=package_report_path,
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
