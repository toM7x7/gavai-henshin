"""Audit repository structure cleanup candidates without mutating files.

The tool scans the filesystem, not the Git index. It reports missing required
root files, top-level transient/local entries, and exhibition archive candidates
so cleanup work can be planned mechanically before any staging or deletion.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


CONTRACT_VERSION = "project-structure-cleanup-audit.v2"

REQUIRED_ROOT_FILES = (
    ".env.example",
    ".gitignore",
    "LICENSE",
    "PROJECT_STRUCTURE.md",
    "README.md",
    "package-lock.json",
    "package.json",
    "pyproject.toml",
)

APPROVED_ROOT_DIRS = (
    ".github",
    "config",
    "docs",
    "examples",
    "infra",
    "qa",
    "schemas",
    "src",
    "tests",
    "tools",
    "viewer",
)

APPROVED_ROOT_FILES = (
    ".dockerignore",
    ".env.demo.example",
    ".gitattributes",
    "CONTRIBUTING.md",
    "Dockerfile",
    "Lore Bible.md",
    "blueprint.md",
    "vite.quest.config.js",
)


@dataclass(frozen=True)
class StructureRule:
    rule_id: str
    patterns: tuple[str, ...]
    category: str
    reason: str
    recommended_action: str
    blocked: bool


@dataclass(frozen=True)
class LocalOnlyRoot:
    path: str
    kind: str
    rule_id: str
    reason: str
    recommended_action: str


LOCAL_ONLY_ROOTS: tuple[LocalOnlyRoot, ...] = (
    LocalOnlyRoot(
        path=".env",
        kind="file",
        rule_id="local-only-root-env",
        reason="root .env can contain local secrets or venue-specific values",
        recommended_action="keep local; publish only reviewed env examples",
    ),
    LocalOnlyRoot(
        path="node_modules",
        kind="dir",
        rule_id="local-only-root-node-modules",
        reason="Node dependency cache is recreated from package-lock.json",
        recommended_action="keep ignored/local; do not stage",
    ),
    LocalOnlyRoot(
        path=".pytest_cache",
        kind="dir",
        rule_id="local-only-root-pytest-cache",
        reason="pytest cache is machine-local generated state",
        recommended_action="remove locally or keep ignored; regenerate from pytest",
    ),
    LocalOnlyRoot(
        path="sessions/.gitkeep",
        kind="file",
        rule_id="local-only-root-session-placeholder",
        reason="sessions is a local runtime output root; the placeholder should not make session output releasable",
        recommended_action="review whether the cleanup branch should keep or remove the placeholder",
    ),
)


TOP_LEVEL_RULES: tuple[StructureRule, ...] = (
    StructureRule(
        rule_id="root-local-env",
        patterns=(".env", ".env.*"),
        category="top-level-local-only-file",
        reason="local env files can contain provider secrets or venue-specific values",
        recommended_action="keep local; publish only reviewed example env templates",
        blocked=True,
    ),
    StructureRule(
        rule_id="root-temp-log",
        patterns=("*.log", "*.err", "*.out", ".tmp*", "armor-forge-japanese-ui-*.png"),
        category="top-level-transient-file",
        reason="root-level logs, temp outputs, and smoke screenshots are generated review artifacts",
        recommended_action="remove locally or move curated evidence into an approved QA/archive path",
        blocked=True,
    ),
    StructureRule(
        rule_id="browser-smoke-output-dir",
        patterns=(".playwright-cli", ".playwright-mcp"),
        category="top-level-transient-dir",
        reason="browser automation outputs are local smoke evidence",
        recommended_action="remove locally; regenerate from browser smoke checks when needed",
        blocked=True,
    ),
    StructureRule(
        rule_id="python-test-cache-dir",
        patterns=(".pytest_cache",),
        category="top-level-local-only-dir",
        reason="pytest cache is machine-local generated state",
        recommended_action="remove locally; regenerate from pytest",
        blocked=True,
    ),
    StructureRule(
        rule_id="dependency-cache-dir",
        patterns=("node_modules", ".venv", "venv", "env"),
        category="top-level-local-only-dir",
        reason="dependency caches are recreated by install commands",
        recommended_action="remove locally or keep ignored; do not stage",
        blocked=True,
    ),
    StructureRule(
        rule_id="build-output-dir",
        patterns=("dist", "build"),
        category="top-level-transient-dir",
        reason="build output is generated from source",
        recommended_action="remove locally; rebuild in CI or release packaging",
        blocked=True,
    ),
    StructureRule(
        rule_id="generated-runtime-output-dir",
        patterns=("output", "sessions"),
        category="top-level-local-only-dir",
        reason="runtime/session outputs contain local generated artifacts",
        recommended_action="archive externally if needed; keep out of normal repo root",
        blocked=True,
    ),
    StructureRule(
        rule_id="local-workspace-dir",
        patterns=(".claude", "blender"),
        category="top-level-local-workspace-dir",
        reason="agent/modeling workspaces are not normal source layout",
        recommended_action="keep local; promote only reviewed assets into approved repo paths",
        blocked=True,
    ),
)

ARCHIVE_RULES: tuple[StructureRule, ...] = (
    StructureRule(
        rule_id="exhibition-doc",
        patterns=("docs/exhibition-*.md", "docs/*exhibition*.md"),
        category="exhibition-archive-candidate",
        reason="exhibition planning/runbook document should be reviewed as an archive candidate",
        recommended_action="move to an exhibition archive package or keep only if actively maintained",
        blocked=False,
    ),
    StructureRule(
        rule_id="quest-doc",
        patterns=("docs/quest-*.md",),
        category="exhibition-archive-candidate",
        reason="Quest rehearsal/operator document should be reviewed as an archive candidate",
        recommended_action="move dated rehearsal notes to an exhibition archive when no longer active",
        blocked=False,
    ),
    StructureRule(
        rule_id="modeler-handoff-doc",
        patterns=("docs/modeler-*.md",),
        category="exhibition-archive-candidate",
        reason="modeler handoff/review document may be time-bound delivery evidence",
        recommended_action="archive dated handoff evidence unless it is the current source of truth",
        blocked=False,
    ),
    StructureRule(
        rule_id="release-cleanup-doc",
        patterns=(
            "docs/release-stage-*.md",
            "docs/repo-cleanup-github-readiness-*.md",
            "docs/two-week-execution-schedule-*.md",
        ),
        category="exhibition-archive-candidate",
        reason="release cleanup/status document may belong in the exhibition archive set",
        recommended_action="archive after release readiness work is complete",
        blocked=False,
    ),
    StructureRule(
        rule_id="qa-evidence-artifact",
        patterns=("qa/*.json", "qa/**/*.json", "qa/*.md", "qa/**/*.md"),
        category="exhibition-archive-candidate",
        reason="QA evidence should be curated before it is retained in the repo",
        recommended_action="keep only validated shareable manifests; archive raw evidence externally",
        blocked=False,
    ),
    StructureRule(
        rule_id="reference-doc-bundle",
        patterns=("examples/henshin_docs*_bundle*.zip", "examples/henshin_docs*_bundle*/**"),
        category="exhibition-archive-candidate",
        reason="generated documentation bundles are archive artifacts, not active source",
        recommended_action="archive externally or keep only a named approved release bundle",
        blocked=False,
    ),
    StructureRule(
        rule_id="reference-visual-artifact",
        patterns=("docs/assets/**", "docs/_smoke_renders/**"),
        category="exhibition-archive-candidate",
        reason="reference visuals and smoke renders need explicit curation",
        recommended_action="archive stale visuals; keep only assets referenced by active docs",
        blocked=False,
    ),
)


def _posix(path: str | Path) -> str:
    return str(path).replace("\\", "/").strip()


def _matches(path: str, pattern: str) -> bool:
    normalized = _posix(path)
    normalized_pattern = _posix(pattern)
    if normalized_pattern.endswith("/**"):
        prefix = normalized_pattern[:-3]
        if fnmatch.fnmatchcase(normalized, normalized_pattern):
            return True
        return normalized == prefix.rstrip("/") or normalized.startswith(prefix)
    return fnmatch.fnmatchcase(normalized, normalized_pattern)


def _first_rule(path: str, rules: Iterable[StructureRule]) -> tuple[StructureRule | None, str]:
    normalized = _posix(path)
    for rule in rules:
        for pattern in rule.patterns:
            if _matches(normalized, pattern):
                return rule, pattern
    return None, ""


def _root_item(path: Path, repo_root: Path) -> dict[str, Any]:
    relative = _posix(path.relative_to(repo_root))
    name = path.name
    kind = "dir" if path.is_dir() else "file"

    if kind == "dir" and name in APPROVED_ROOT_DIRS:
        category = "approved-root-dir"
        reason = "approved top-level source or project-support directory"
        recommended_action = "keep"
        rule_id = "approved-root-dir"
        matched_pattern = ""
        blocked = False
    elif kind == "file" and name in REQUIRED_ROOT_FILES:
        category = "required-root-file"
        reason = "required top-level project metadata or documentation"
        recommended_action = "keep"
        rule_id = "required-root-file"
        matched_pattern = ""
        blocked = False
    elif kind == "file" and name in APPROVED_ROOT_FILES:
        category = "approved-root-file"
        reason = "approved top-level support file"
        recommended_action = "keep"
        rule_id = "approved-root-file"
        matched_pattern = ""
        blocked = False
    else:
        rule, matched_pattern = _first_rule(name, TOP_LEVEL_RULES)
        if rule is not None:
            category = rule.category
            reason = rule.reason
            recommended_action = rule.recommended_action
            rule_id = rule.rule_id
            blocked = rule.blocked
        else:
            category = f"unknown-root-{kind}"
            reason = "top-level entry is not in the approved structure or cleanup rules"
            recommended_action = "manual-review"
            rule_id = category
            blocked = False

    return {
        "path": relative,
        "kind": kind,
        "category": category,
        "rule_id": rule_id,
        "matched_pattern": matched_pattern,
        "blocked": blocked,
        "reason": reason,
        "recommended_action": recommended_action,
    }


def _archive_item(path: Path, repo_root: Path) -> dict[str, Any] | None:
    relative = _posix(path.relative_to(repo_root))
    rule, matched_pattern = _first_rule(relative, ARCHIVE_RULES)
    if rule is None:
        return None
    return {
        "path": relative,
        "kind": "dir" if path.is_dir() else "file",
        "category": rule.category,
        "rule_id": rule.rule_id,
        "matched_pattern": matched_pattern,
        "blocked": rule.blocked,
        "reason": rule.reason,
        "recommended_action": rule.recommended_action,
    }


def _local_only_root_item(root: Path, rule: LocalOnlyRoot) -> dict[str, Any] | None:
    path = root / rule.path
    if rule.kind == "dir" and not path.is_dir():
        return None
    if rule.kind == "file" and not path.is_file():
        return None
    return {
        "path": _posix(rule.path),
        "kind": rule.kind,
        "category": "local-only-root",
        "rule_id": rule.rule_id,
        "matched_pattern": _posix(rule.path),
        "blocked": True,
        "reason": rule.reason,
        "recommended_action": rule.recommended_action,
    }


def _local_only_roots(root: Path) -> list[dict[str, Any]]:
    return [
        item
        for item in (_local_only_root_item(root, rule) for rule in LOCAL_ONLY_ROOTS)
        if item is not None
    ]


def _iter_archive_scan_paths(repo_root: Path) -> Iterable[Path]:
    for root_name in ("docs", "qa", "examples"):
        root = repo_root / root_name
        if not root.exists():
            continue
        for path in sorted(root.rglob("*"), key=lambda item: _posix(item.relative_to(repo_root))):
            if path.is_file():
                yield path


def _bucket_counts(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(key) or "")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _grouped_samples(items: list[dict[str, Any]], *, key: str, sample_limit: int) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        value = str(item.get(key) or "")
        bucket = groups.setdefault(value, [])
        if len(bucket) < sample_limit:
            bucket.append(item)
    return dict(sorted(groups.items()))


def _suppressed_by_key(items: list[dict[str, Any]], samples: dict[str, list[dict[str, Any]]], *, key: str) -> dict[str, int]:
    counts = _bucket_counts(items, key)
    return {value: max(0, count - len(samples.get(value, []))) for value, count in counts.items()}


def build_audit(repo_root: Path, *, sample_limit: int = 10, full: bool = False) -> dict[str, Any]:
    root = repo_root.resolve()
    root_entries = [
        _root_item(path, root)
        for path in sorted(root.iterdir(), key=lambda item: item.name.lower())
        if path.name != ".git"
    ]
    archive_candidates = [
        item
        for item in (_archive_item(path, root) for path in _iter_archive_scan_paths(root))
        if item is not None
    ]
    local_only_roots = _local_only_roots(root)
    missing_required = [
        {
            "path": name,
            "kind": "file",
            "category": "missing-required-root-file",
            "rule_id": "missing-required-root-file",
            "blocked": True,
            "reason": "required top-level project file is missing",
            "recommended_action": "restore or intentionally replace before cleanup is complete",
        }
        for name in REQUIRED_ROOT_FILES
        if not (root / name).is_file()
    ]
    blocked_root_items = [item for item in root_entries if item["blocked"]]
    cleanup_findings = [*missing_required, *blocked_root_items]
    root_samples = _grouped_samples(root_entries, key="category", sample_limit=sample_limit)
    archive_samples = _grouped_samples(archive_candidates, key="rule_id", sample_limit=sample_limit)

    payload: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "repo_root": root.as_posix(),
        "read_only": True,
        "ok": not cleanup_findings,
        "sample_limit": sample_limit,
        "counts": {
            "root_entries": len(root_entries),
            "missing_required": len(missing_required),
            "blocked_top_level": len(blocked_root_items),
            "local_only_roots": len(local_only_roots),
            "archive_candidates": len(archive_candidates),
            "by_root_category": _bucket_counts(root_entries, "category"),
            "by_local_only_root_rule": _bucket_counts(local_only_roots, "rule_id"),
            "by_archive_rule": _bucket_counts(archive_candidates, "rule_id"),
        },
        "local_only_roots": local_only_roots[:sample_limit],
        "local_only_roots_suppressed": max(0, len(local_only_roots) - sample_limit),
        "missing_required": missing_required[:sample_limit],
        "missing_required_suppressed": max(0, len(missing_required) - sample_limit),
        "blocked_top_level": blocked_root_items[:sample_limit],
        "blocked_top_level_suppressed": max(0, len(blocked_root_items) - sample_limit),
        "samples_by_root_category": root_samples,
        "suppressed_by_root_category": _suppressed_by_key(root_entries, root_samples, key="category"),
        "samples_by_archive_rule": archive_samples,
        "suppressed_by_archive_rule": _suppressed_by_key(archive_candidates, archive_samples, key="rule_id"),
        "rules": {
            "required_root_files": list(REQUIRED_ROOT_FILES),
            "approved_root_dirs": list(APPROVED_ROOT_DIRS),
            "approved_root_files": list(APPROVED_ROOT_FILES),
            "local_only_roots": [
                {
                    "path": rule.path,
                    "kind": rule.kind,
                    "rule_id": rule.rule_id,
                    "reason": rule.reason,
                    "recommended_action": rule.recommended_action,
                }
                for rule in LOCAL_ONLY_ROOTS
            ],
            "top_level_rules": [
                {
                    "rule_id": rule.rule_id,
                    "patterns": list(rule.patterns),
                    "category": rule.category,
                    "blocked": rule.blocked,
                    "reason": rule.reason,
                    "recommended_action": rule.recommended_action,
                }
                for rule in TOP_LEVEL_RULES
            ],
            "archive_rules": [
                {
                    "rule_id": rule.rule_id,
                    "patterns": list(rule.patterns),
                    "category": rule.category,
                    "blocked": rule.blocked,
                    "reason": rule.reason,
                    "recommended_action": rule.recommended_action,
                }
                for rule in ARCHIVE_RULES
            ],
        },
        "notes": [
            "This tool is read-only and never stages, removes, moves, or edits files.",
            "Blocked top-level findings are cleanup candidates, not deletion commands.",
            "Archive candidates are review queues for exhibition-era evidence and docs.",
        ],
    }
    if full:
        payload["root_items"] = root_entries
        payload["archive_candidates"] = archive_candidates
    return payload


def _json_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."), help="Git worktree root")
    parser.add_argument("--sample-limit", type=int, default=10, help="Sample paths per group")
    parser.add_argument("--full-json", action="store_true", help="Include every root item and archive candidate")
    parser.add_argument("--report-json", "--json", action="store_true", help="Print JSON audit report")
    parser.add_argument("--fail-on-findings", action="store_true", help="Exit 1 when missing required or blocked root entries exist")
    args = parser.parse_args(argv)

    payload = build_audit(args.repo_root, sample_limit=max(0, args.sample_limit), full=args.full_json)
    if args.report_json or args.full_json:
        sys.stdout.write(_json_payload(payload))
    else:
        print(f"project structure cleanup: {payload['repo_root']}")
        print(
            "ok={ok} missing_required={missing} blocked_top_level={blocked} archive_candidates={archive}".format(
                ok=payload["ok"],
                missing=payload["counts"]["missing_required"],
                blocked=payload["counts"]["blocked_top_level"],
                archive=payload["counts"]["archive_candidates"],
            )
        )
        for category, count in payload["counts"]["by_root_category"].items():
            print(f"{category}: {count}")

    if args.fail_on_findings and not payload["ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
