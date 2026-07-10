"""List release stage candidates from git status without staging anything.

The tool is intentionally read-only. It shells out only to `git status` and
classifies each changed, untracked, or ignored path into the release cleanup
buckets used by the exhibition GitHub push plan.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


CONTRACT_VERSION = "release-stage-candidates.v7"
CATEGORIES = (
    "release-critical",
    "operator-docs",
    "armor-assets",
    "qa-evidence",
    "local-qa-artifact",
    "reference-docs",
    "reference-artifact",
    "user-feedback-media",
    "local-workspace",
    "local-only-root",
    "deleted-tracked-artifact",
    "generated-artifact",
    "ambiguous",
)
STAGE_CANDIDATE_CATEGORIES = (
    "release-critical",
    "operator-docs",
    "armor-assets",
)
MANUAL_REVIEW_CATEGORIES = (
    "qa-evidence",
    "reference-docs",
    "reference-artifact",
    "deleted-tracked-artifact",
    "ambiguous",
)
DO_NOT_STAGE_CATEGORIES = (
    "local-qa-artifact",
    "user-feedback-media",
    "local-workspace",
    "local-only-root",
    "generated-artifact",
)

GENERATED_PREFIXES = (
    ".playwright-cli/",
    ".playwright-mcp/",
    "docs/archive/evidence-",
    "output/",
    "qa/logs/",
    "tests/.tmp/",
)
GENERATED_DIR_NAMES = {"__pycache__", ".pytest_cache"}
GENERATED_ROOT_SUFFIXES = (
    ".log",
    ".err",
    ".out",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".yml",
    ".yaml",
)
GENERATED_QA_SUFFIXES = (
    ".log",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".yml",
    ".yaml",
)

ARMOR_ASSET_PREFIX = "viewer/assets/armor-parts/"

SHAREABLE_QA_EXACT = {
    "qa/shareable-qa-evidence-latest.json",
}
SHAREABLE_QA_NAME_MARKERS = {
    "shareable-qa-evidence",
    "mocopi-evidence-package",
}

OPERATOR_DOC_EXACT = {
    "docs/current-web-quest-check-guide.md",
    "docs/exhibition-github-cleanup-plan-2026-05-04.md",
    "docs/modeler-exhibition-readiness-risks-2026-05-04.md",
    "docs/modeler-fit-micro-adjustments-2026-05-04.md",
    "docs/modeler-triview-30variant-audit-table-2026-05-03.md",
    "docs/replay-record-contract.md",
    "docs/web-service-phase0-task-breakdown-2026-05-02.md",
}
OPERATOR_DOC_PREFIXES = (
    "docs/exhibition-",
    "docs/quest-",
    "docs/p1-limb-",
    "docs/modeler-deliveries/",
)

RELEASE_CRITICAL_EXACT = {
    ".env.demo.example",
    ".env.example",
    ".gitignore",
    "package-lock.json",
    "package.json",
    "PROJECT_STRUCTURE.md",
    "pyproject.toml",
    "README.md",
    "vite.quest.config.js",
    "examples/modeler_delivery_manifest.sample.json",
    "examples/quest-mocopi-motion-source.fixture.json",
    "examples/replay-record.sample.json",
    "examples/suitspec.sample.json",
}
RELEASE_CRITICAL_PREFIXES = (
    "schemas/",
    "src/henshin/",
    "tests/test_",
    "tools/",
    "viewer/armor-forge/",
    "viewer/quest-iw-demo/",
    "viewer/shared/",
)

REFERENCE_DOC_PREFIXES = (
    "docs/",
)
REFERENCE_ARTIFACT_PREFIXES = (
    "docs/_smoke_renders/",
    "docs/assets/",
    "examples/henshin_docs_bundle_",
    "examples/henshin_docs_gcp_bundle_",
)
REFERENCE_ARTIFACT_SUFFIXES = (
    ".zip",
)
USER_FEEDBACK_MEDIA_PREFIXES = (
    "examples/",
)
USER_FEEDBACK_MEDIA_SUFFIXES = (
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".mp4",
    ".pdf",
    ".txt",
)
LOCAL_WORKSPACE_PREFIXES = (
    ".claude/",
    "blender/",
)
LOCAL_ONLY_ROOT_EXACT = {
    ".env",
    "sessions/.gitkeep",
}
LOCAL_ONLY_ROOT_PREFIXES = (
    ".env.",
    ".pytest_cache/",
    ".venv/",
    "env/",
    "node_modules/",
    "sessions/",
    "venv/",
)
LOCAL_ONLY_ROOT_ALLOW_EXACT = {
    ".env.demo.example",
    ".env.example",
}


@dataclass(frozen=True)
class StatusEntry:
    status: str
    path: str
    old_path: str = ""


@dataclass(frozen=True)
class ClassifiedEntry:
    category: str
    path: str
    status: str
    tracked: bool
    ignored: bool
    reason: str
    recommended_action: str
    old_path: str = ""


def _posix(path: str) -> str:
    return path.replace("\\", "/").strip()


def _has_prefix(path: str, prefixes: Iterable[str]) -> bool:
    return any(path == prefix.rstrip("/") or path.startswith(prefix) for prefix in prefixes)


def _has_suffix(path: str, suffixes: Iterable[str]) -> bool:
    lowered = path.lower()
    return any(lowered.endswith(suffix) for suffix in suffixes)


def _is_deleted_status(status: str) -> bool:
    return "D" in status[:2]


def _is_local_only_root(path: str) -> bool:
    if path in LOCAL_ONLY_ROOT_ALLOW_EXACT:
        return False
    return path in LOCAL_ONLY_ROOT_EXACT or _has_prefix(path, LOCAL_ONLY_ROOT_PREFIXES)


def _is_generated_artifact(path: str, status: str) -> tuple[bool, str]:
    if status == "!!":
        return True, "ignored by git status; keep out of normal release staging"
    if _has_prefix(path, GENERATED_PREFIXES):
        return True, "local browser/smoke/QA output path"
    if any(part in GENERATED_DIR_NAMES for part in path.split("/")):
        return True, "python/test cache output"
    if path.startswith("qa/") and _has_suffix(path, GENERATED_QA_SUFFIXES):
        return True, "local QA screenshot/log output"
    if "/" not in path and (
        _has_suffix(path, GENERATED_ROOT_SUFFIXES)
        or path.startswith("armor-forge-japanese-ui-")
    ):
        return True, "root-level temporary screenshot/log"
    return False, ""


def _classify_qa_json(path: str) -> tuple[str, str, str] | None:
    if not path.startswith("qa/") or not path.endswith(".json"):
        return None
    name = path.rsplit("/", 1)[-1]
    if path in SHAREABLE_QA_EXACT or any(marker in name for marker in SHAREABLE_QA_NAME_MARKERS):
        return (
            "qa-evidence",
            "shareable QA evidence manifest; stage only if recommended by the shareable QA manifest",
            "manual-evidence-review",
        )
    return (
        "local-qa-artifact",
        "local/raw or privacy-unvalidated QA JSON evidence; keep out of normal release staging",
        "do-not-stage",
    )


def _classify_qa_doc(path: str) -> tuple[str, str, str] | None:
    if not path.startswith("qa/") or not path.endswith(".md"):
        return None
    return (
        "local-qa-artifact",
        "local/raw QA markdown evidence; keep out of normal release staging",
        "do-not-stage",
    )


def _is_deleted_tracked_artifact(path: str) -> bool:
    generated, _ = _is_generated_artifact(path, "??")
    if generated:
        return True
    if _classify_qa_json(path) is not None or _classify_qa_doc(path) is not None:
        return True
    return False


def classify_path(path: str, status: str) -> tuple[str, str, str]:
    """Return category, reason, and recommended action for a repo-relative path."""

    normalized = _posix(path)
    if _is_local_only_root(normalized):
        return (
            "local-only-root",
            "local-only root/cache/session path; keep out of normal release staging",
            "do-not-stage",
        )

    if _is_deleted_status(status) and _is_deleted_tracked_artifact(normalized):
        return (
            "deleted-tracked-artifact",
            "tracked generated/local artifact is deleted in the worktree; review as a cleanup-branch deletion",
            "stage-only-in-reviewed-cleanup-branch",
        )

    generated, generated_reason = _is_generated_artifact(normalized, status)
    if generated:
        return "generated-artifact", generated_reason, "do-not-stage"

    qa_json = _classify_qa_json(normalized)
    if qa_json is not None:
        return qa_json

    qa_doc = _classify_qa_doc(normalized)
    if qa_doc is not None:
        return qa_doc

    if normalized.startswith(ARMOR_ASSET_PREFIX):
        return "armor-assets", "armor catalog or GLB/modeler/preview/source asset", "stage-in-asset-commit"

    if normalized in OPERATOR_DOC_EXACT or _has_prefix(normalized, OPERATOR_DOC_PREFIXES):
        return "operator-docs", "operator/release handoff documentation", "stage-in-docs-commit"

    if normalized in RELEASE_CRITICAL_EXACT or _has_prefix(normalized, RELEASE_CRITICAL_PREFIXES):
        return "release-critical", "runtime, tool, schema, example, or test needed before push", "stage-candidate"

    if _has_prefix(normalized, LOCAL_WORKSPACE_PREFIXES):
        return "local-workspace", "local agent/modeling workspace; keep out of normal release staging", "do-not-stage"

    if _has_prefix(normalized, REFERENCE_ARTIFACT_PREFIXES) or (
        normalized.startswith("examples/") and _has_suffix(normalized, REFERENCE_ARTIFACT_SUFFIXES)
    ):
        return "reference-artifact", "reference visual/doc bundle artifact; stage only by explicit release-owner choice", "manual-reference-review"

    if _has_prefix(normalized, USER_FEEDBACK_MEDIA_PREFIXES) and _has_suffix(normalized, USER_FEEDBACK_MEDIA_SUFFIXES):
        return "user-feedback-media", "user-provided or screenshot media under examples; do not stage by default", "do-not-stage"

    if _has_prefix(normalized, REFERENCE_DOC_PREFIXES):
        return "reference-docs", "non-operator reference/planning documentation", "manual-doc-review"

    return "ambiguous", "not matched by release-critical/operator/assets/generated rules", "manual-review"


def parse_porcelain_z(data: bytes) -> list[StatusEntry]:
    """Parse `git status --porcelain=v1 -z` output."""

    parts = [part.decode("utf-8", errors="replace") for part in data.split(b"\0") if part]
    entries: list[StatusEntry] = []
    index = 0
    while index < len(parts):
        raw = parts[index]
        status = raw[:2]
        path = raw[3:] if len(raw) > 3 else ""
        old_path = ""
        if status and status[0] in {"R", "C"}:
            index += 1
            if index < len(parts):
                old_path = parts[index]
        if path:
            entries.append(StatusEntry(status=status, path=_posix(path), old_path=_posix(old_path)))
        index += 1
    return entries


def _read_git_status(repo_root: Path, *, include_ignored: bool) -> bytes:
    command = [
        "git",
        "-C",
        str(repo_root),
        "status",
        "--porcelain=v1",
        "-z",
        "--untracked-files=all",
    ]
    if include_ignored:
        command.append("--ignored")
    completed = subprocess.run(command, check=True, capture_output=True)
    return completed.stdout


def classify_entries(entries: Iterable[StatusEntry]) -> list[ClassifiedEntry]:
    classified: list[ClassifiedEntry] = []
    for entry in entries:
        category, reason, action = classify_path(entry.path, entry.status)
        classified.append(
            ClassifiedEntry(
                category=category,
                path=entry.path,
                status=entry.status,
                tracked=entry.status not in {"??", "!!"},
                ignored=entry.status == "!!",
                reason=reason,
                recommended_action=action,
                old_path=entry.old_path,
            )
        )
    return classified


def build_report(repo_root: Path, *, include_ignored: bool = True) -> dict[str, Any]:
    root = repo_root.resolve()
    entries = parse_porcelain_z(_read_git_status(root, include_ignored=include_ignored))
    classified = classify_entries(entries)
    categories = {category: [] for category in CATEGORIES}
    status_counts: dict[str, int] = {}
    for item in classified:
        categories[item.category].append(asdict(item))
        status_counts[item.status] = status_counts.get(item.status, 0) + 1

    category_counts = {category: len(categories[category]) for category in CATEGORIES}
    return {
        "contract_version": CONTRACT_VERSION,
        "repo_root": root.as_posix(),
        "read_only": True,
        "git_status": {
            "include_ignored": include_ignored,
            "command": [
                "git",
                "-C",
                root.as_posix(),
                "status",
                "--porcelain=v1",
                "-z",
                "--untracked-files=all",
                *(("--ignored",) if include_ignored else ()),
            ],
        },
        "counts": {
            "total": len(classified),
            "by_category": category_counts,
            "by_status": status_counts,
            "tracked_artifact_candidates": sum(
                1
                for item in classified
                if item.category == "generated-artifact" and item.tracked
            ),
            "deleted_tracked_artifacts": sum(
                1
                for item in classified
                if item.category == "deleted-tracked-artifact"
            ),
        },
        "categories": categories,
        "items": [asdict(item) for item in classified],
        "notes": [
            "This tool is read-only and never stages or commits files.",
            "Ignored generated artifacts are listed only when include_ignored is true.",
            "Tracked generated artifacts remain tracked; decide separately whether to git rm --cached them.",
        ],
    }


def build_summary_report(
    repo_root: Path,
    *,
    include_ignored: bool = True,
    sample_limit: int = 5,
) -> dict[str, Any]:
    report = build_report(repo_root, include_ignored=include_ignored)
    categories = report["categories"]
    samples = {
        category: categories[category][:sample_limit]
        for category in CATEGORIES
        if categories[category]
    }

    return {
        "contract_version": f"{CONTRACT_VERSION}.summary",
        "repo_root": report["repo_root"],
        "read_only": True,
        "summary": True,
        "sample_limit": sample_limit,
        "git_status": report["git_status"],
        "counts": report["counts"],
        "samples": samples,
        "suppressed": {
            category: max(0, len(categories[category]) - len(samples.get(category, [])))
            for category in CATEGORIES
        },
        "notes": [
            "Summary JSON suppresses full path lists for large ignored/generated artifact sets.",
            *report["notes"],
        ],
    }


def _print_text_report(report: dict[str, Any]) -> None:
    print(f"release stage candidates: {report['repo_root']}")
    print(f"total={report['counts']['total']} read_only={report['read_only']}")
    for category in CATEGORIES:
        print(f"{category}: {report['counts']['by_category'][category]}")
        for item in report["categories"][category]:
            old = f" <- {item['old_path']}" if item.get("old_path") else ""
            print(
                f"  {item['status']} {item['path']}{old} "
                f"[{item['recommended_action']}] {item['reason']}"
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."), help="Git worktree root")
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument("--json", "--report-json", dest="report_json", action="store_true", help="Emit full JSON")
    output_group.add_argument(
        "--summary-json",
        action="store_true",
        help="Emit counts and small samples without full path lists",
    )
    parser.add_argument("--no-ignored", action="store_true", help="Do not include ignored paths")
    parser.add_argument("--sample-limit", type=int, default=5, help="Sample paths per category for --summary-json")
    args = parser.parse_args(argv)

    if args.summary_json:
        report = build_summary_report(
            args.repo_root,
            include_ignored=not args.no_ignored,
            sample_limit=max(0, args.sample_limit),
        )
        json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    else:
        report = build_report(args.repo_root, include_ignored=not args.no_ignored)
    if args.report_json:
        json.dump(report, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    elif not args.summary_json:
        _print_text_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
