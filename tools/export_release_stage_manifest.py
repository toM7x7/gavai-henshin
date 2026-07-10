"""Export a machine-readable release staging manifest without staging files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import list_release_stage_candidates as stage_candidates


CONTRACT_VERSION = "release-stage-manifest.v5"

CATEGORY_RECOMMENDED_ACTIONS = {
    "release-critical": "review and stage in the runtime/release-critical commit",
    "operator-docs": "stage required runbook, checklist, and handoff docs after runtime/assets",
    "armor-assets": "stage catalog-referenced armor assets in a dedicated asset commit",
    "qa-evidence": "stage only shareable QA evidence manifests recommended by the privacy/shareable validator",
    "local-qa-artifact": "do not stage raw or privacy-unvalidated QA evidence; promote through the shareable QA manifest if needed",
    "reference-docs": "stage only docs promoted by the release owner; not required for clone runtime",
    "reference-artifact": "stage only curated reference artifacts; keep screenshots/bundles out by default",
    "user-feedback-media": "do not stage user photos/screenshots by default",
    "local-workspace": "do not stage local agent/modeling workspace files",
    "local-only-root": "do not stage local dependency caches, secret env files, pytest cache, or session placeholders",
    "deleted-tracked-artifact": "stage only in a reviewed main-based cleanup branch after confirming the tracked path is generated/local-only",
    "ambiguous": "resolve manually before push; stage only with an explicit release-owner reason",
    "generated-artifact": "do not stage for the normal GitHub release",
}

CATEGORY_STAGE_POLICY = {
    "release-critical": "stage-candidate",
    "operator-docs": "stage-candidate",
    "armor-assets": "stage-candidate",
    "qa-evidence": "manual-evidence-review",
    "local-qa-artifact": "do-not-stage",
    "reference-docs": "manual-doc-review",
    "reference-artifact": "manual-reference-review",
    "user-feedback-media": "do-not-stage",
    "local-workspace": "do-not-stage",
    "local-only-root": "do-not-stage",
    "deleted-tracked-artifact": "cleanup-deletion-review",
    "ambiguous": "manual-review",
    "generated-artifact": "do-not-stage",
}


def _category_count(summary: dict[str, Any], category: str) -> int:
    return int(summary.get("counts", {}).get("by_category", {}).get(category, 0))


def _category_samples(summary: dict[str, Any], category: str) -> list[dict[str, Any]]:
    samples = summary.get("samples", {}).get(category, [])
    return samples if isinstance(samples, list) else []


def _category_suppressed(summary: dict[str, Any], category: str) -> int:
    return int(summary.get("suppressed", {}).get(category, 0))


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


def _build_blockers(summary: dict[str, Any]) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    ambiguous_count = _category_count(summary, "ambiguous")
    if ambiguous_count:
        blockers.append(
            _issue(
                code="ambiguous-changes-present",
                severity="blocker",
                category="ambiguous",
                count=ambiguous_count,
                message="Ambiguous paths must be resolved or explicitly left unstaged before GitHub push.",
                recommended_action=CATEGORY_RECOMMENDED_ACTIONS["ambiguous"],
            )
        )

    tracked_artifacts = int(summary.get("counts", {}).get("tracked_artifact_candidates", 0))
    if tracked_artifacts:
        blockers.append(
            _issue(
                code="tracked-generated-artifacts-present",
                severity="blocker",
                category="generated-artifact",
                count=tracked_artifacts,
                message="Tracked generated artifacts can still be staged despite ignore rules.",
                recommended_action="leave them unstaged or handle with a separately reviewed cleanup plan",
            )
        )

    return blockers


def _build_warnings(summary: dict[str, Any]) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    generated_count = _category_count(summary, "generated-artifact")
    if generated_count:
        warnings.append(
            _issue(
                code="generated-artifacts-present",
                severity="warn",
                category="generated-artifact",
                count=generated_count,
                message="Generated artifacts are present in the worktree report and should stay out of release staging.",
                recommended_action=CATEGORY_RECOMMENDED_ACTIONS["generated-artifact"],
            )
        )

    qa_evidence_count = _category_count(summary, "qa-evidence")
    if qa_evidence_count:
        warnings.append(
            _issue(
                code="qa-evidence-needs-explicit-approval",
                severity="warn",
                category="qa-evidence",
                count=qa_evidence_count,
                message="QA evidence is not runtime input; stage only shareable QA manifests recommended by the privacy/shareable validator.",
                recommended_action=CATEGORY_RECOMMENDED_ACTIONS["qa-evidence"],
            )
        )

    local_qa_count = _category_count(summary, "local-qa-artifact")
    if local_qa_count:
        warnings.append(
            _issue(
                code="local-qa-artifacts-present",
                severity="warn",
                category="local-qa-artifact",
                count=local_qa_count,
                message="Raw or privacy-unvalidated QA JSON evidence is present and should stay out of normal release staging.",
                recommended_action=CATEGORY_RECOMMENDED_ACTIONS["local-qa-artifact"],
            )
        )

    for category, code, message in (
        (
            "reference-docs",
            "reference-docs-present",
            "Reference/planning docs are present; stage only those promoted into the handoff.",
        ),
        (
            "reference-artifact",
            "reference-artifacts-present",
            "Reference artifacts are present and are not required clone/runtime inputs.",
        ),
        (
            "user-feedback-media",
            "user-feedback-media-present",
            "User feedback media/screenshots are present and should stay out of normal release staging.",
        ),
        (
            "local-workspace",
            "local-workspace-present",
            "Local workspace files are present and should stay out of release staging.",
        ),
        (
            "local-only-root",
            "local-only-roots-present",
            "Local-only root/cache/session paths are present and should stay out of normal release staging.",
        ),
        (
            "deleted-tracked-artifact",
            "deleted-tracked-artifacts-present",
            "Tracked generated/local artifacts are deleted; stage only as an intentional cleanup-branch deletion.",
        ),
    ):
        count = _category_count(summary, category)
        if count:
            warnings.append(
                _issue(
                    code=code,
                    severity="warn",
                    category=category,
                    count=count,
                    message=message,
                    recommended_action=CATEGORY_RECOMMENDED_ACTIONS[category],
                )
            )

    suppressed = {
        category: _category_suppressed(summary, category)
        for category in stage_candidates.CATEGORIES
        if _category_suppressed(summary, category)
    }
    if suppressed:
        warnings.append(
            {
                "code": "summary-suppressed-paths",
                "severity": "warn",
                "category": "",
                "count": sum(suppressed.values()),
                "message": "The manifest contains samples only; inspect --report-json or the candidate tool when exact paths are needed.",
                "recommended_action": "rerun with a larger --sample-limit or inspect tools/list_release_stage_candidates.py --json",
                "suppressed_by_category": suppressed,
            }
        )

    return warnings


def _decision_bucket(
    categories: dict[str, dict[str, Any]],
    category_names: tuple[str, ...],
    *,
    description: str,
) -> dict[str, Any]:
    by_category = {
        category: {
            "count": categories[category]["count"],
            "sample_count": categories[category]["sample_count"],
            "suppressed": categories[category]["suppressed"],
            "stage_policy": categories[category]["stage_policy"],
            "recommended_action": categories[category]["recommended_action"],
            "samples": categories[category]["samples"],
        }
        for category in category_names
    }
    return {
        "description": description,
        "categories": list(category_names),
        "count": sum(item["count"] for item in by_category.values()),
        "by_category": by_category,
    }


def _build_stage_decision(categories: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "stage_candidates": _decision_bucket(
            categories,
            stage_candidates.STAGE_CANDIDATE_CATEGORIES,
            description="Normal release stage candidates. Review by group, then stage manually.",
        ),
        "manual_review": _decision_bucket(
            categories,
            stage_candidates.MANUAL_REVIEW_CATEGORIES,
            description="Not automatic stage inputs. Promote individual paths only by explicit release-owner decision.",
        ),
        "do_not_stage": _decision_bucket(
            categories,
            stage_candidates.DO_NOT_STAGE_CATEGORIES,
            description="Local, generated, privacy-unvalidated, or workspace-only files that must stay out of normal GitHub staging.",
        ),
    }


def build_manifest(summary: dict[str, Any]) -> dict[str, Any]:
    categories = {
        category: {
            "count": _category_count(summary, category),
            "samples": _category_samples(summary, category),
            "sample_count": len(_category_samples(summary, category)),
            "suppressed": _category_suppressed(summary, category),
            "recommended_action": CATEGORY_RECOMMENDED_ACTIONS[category],
            "stage_policy": CATEGORY_STAGE_POLICY[category],
        }
        for category in stage_candidates.CATEGORIES
    }
    stage_decision = _build_stage_decision(categories)
    blockers = _build_blockers(summary)
    warnings = _build_warnings(summary)

    return {
        "contract_version": CONTRACT_VERSION,
        "read_only": True,
        "repo_root": summary.get("repo_root", ""),
        "source": {
            "tool": "tools/list_release_stage_candidates.py",
            "contract_version": summary.get("contract_version", ""),
            "summary": bool(summary.get("summary", False)),
            "sample_limit": summary.get("sample_limit"),
            "git_status": summary.get("git_status", {}),
        },
        "counts": summary.get("counts", {}),
        "categories": categories,
        "stage_decision": stage_decision,
        "push_readiness": {
            "ready": not blockers,
            "blockers": blockers,
            "warnings": warnings,
        },
        "recommended_stage_units": [
            "release-hygiene",
            "runtime-contract",
            "armor-assets",
            "operator-docs",
            "qa-evidence-only-if-approved",
            "reference-docs-only-if-promoted",
        ],
        "do_not_stage": [
            ".playwright-cli/**",
            ".playwright-mcp/**",
            "tests/.tmp/**",
            "output/**",
            "qa/logs/**",
            "qa/*.json except qa/shareable-qa-evidence-latest.json and shareable manifest recommended paths",
            "qa/replay/*.json",
            "qa/replay/*.replay-record.json",
            "qa/*runtime-package*.snapshot.json",
            "qa/*replay-record*.demo.json",
            "qa/exhibition_release_package_latest.json",
            "qa/model-quality-acceptance-latest.json",
            "qa/release-stage-validation-latest.json",
            "qa/replay/*.summary.json",
            "examples/*.jpg",
            "examples/*.png",
            "examples/henshin_docs*_bundle*/**",
            "docs/_smoke_renders/**",
            ".claude/**",
            "blender/**",
            "transient server logs",
            "local QA screenshots",
        ],
        "notes": [
            "This manifest is read-only and never stages, commits, or pushes files.",
            "stage_decision is the mechanical pre-push map: stage_candidates may be reviewed for staging, manual_review needs explicit promotion, and do_not_stage must stay unstaged.",
            "Use blockers as pre-push decisions, not as automatic cleanup commands.",
            "Use samples for review triage; rerun with a higher --sample-limit for more paths.",
        ],
    }


def export_manifest(
    repo_root: Path,
    *,
    include_ignored: bool = True,
    sample_limit: int = 5,
) -> dict[str, Any]:
    summary = stage_candidates.build_summary_report(
        repo_root,
        include_ignored=include_ignored,
        sample_limit=max(0, sample_limit),
    )
    return build_manifest(summary)


def _json_payload(manifest: dict[str, Any]) -> str:
    return json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"


def _resolve_out_path(repo_root: Path, out_path: Path) -> Path:
    return out_path if out_path.is_absolute() else repo_root.resolve() / out_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."), help="Git worktree root")
    parser.add_argument("--out", type=Path, help="Write JSON manifest to this path")
    parser.add_argument("--sample-limit", type=int, default=5, help="Sample paths per category")
    parser.add_argument("--report-json", action="store_true", help="Print the JSON manifest to stdout")
    parser.add_argument("--no-ignored", action="store_true", help="Do not include ignored paths in the source summary")
    args = parser.parse_args(argv)

    manifest = export_manifest(
        args.repo_root,
        include_ignored=not args.no_ignored,
        sample_limit=args.sample_limit,
    )

    if args.out:
        output_path = _resolve_out_path(args.repo_root, args.out)
        manifest["output_path"] = output_path.resolve().as_posix()
        payload = _json_payload(manifest)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload, encoding="utf-8")
    else:
        payload = _json_payload(manifest)

    if args.report_json or not args.out:
        sys.stdout.write(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
