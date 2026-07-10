"""Audit the dirty worktree before GitHub staging.

The tool is read-only. It inspects `git status --porcelain=v1 -z` and returns
machine-readable staging guidance so raw QA, logs, sessions, temp files, and
generated artifacts do not accidentally enter a GitHub push.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import list_release_stage_candidates as stage_candidates


CONTRACT_VERSION = "repo-readiness-audit.v1"

STAGE_GROUP_BY_CATEGORY = {
    "release-critical": "stage-candidate",
    "operator-docs": "stage-candidate",
    "armor-assets": "stage-candidate",
    "qa-evidence": "manual-review",
    "reference-docs": "manual-review",
    "reference-artifact": "manual-review",
    "ambiguous": "manual-review",
    "local-qa-artifact": "do-not-stage",
    "user-feedback-media": "do-not-stage",
    "local-workspace": "do-not-stage",
    "local-only-root": "do-not-stage",
    "deleted-tracked-artifact": "manual-review",
    "generated-artifact": "do-not-stage",
}

DO_NOT_STAGE_CATEGORIES = {
    "local-qa-artifact",
    "user-feedback-media",
    "local-workspace",
    "local-only-root",
    "generated-artifact",
}


@dataclass(frozen=True)
class AuditRule:
    rule_id: str
    globs: tuple[str, ...]
    reason: str
    recommended_stage_group: str
    recommended_action: str
    blocked: bool
    allow_globs: tuple[str, ...] = ()


AUDIT_RULES: tuple[AuditRule, ...] = (
    AuditRule(
        rule_id="local-env-secret",
        globs=(".env", ".env.*", "**/.env"),
        allow_globs=(".env.example", ".env.demo.example", "**/.env.example"),
        reason="local environment files may contain provider secrets or venue-only values",
        recommended_stage_group="do-not-stage",
        recommended_action="keep local; publish only reviewed example templates",
        blocked=True,
    ),
    AuditRule(
        rule_id="dependency-cache",
        globs=("node_modules/**", ".venv/**", "venv/**", "env/**"),
        reason="dependency caches are recreated by install commands and should not be pushed",
        recommended_stage_group="do-not-stage",
        recommended_action="keep out of GitHub; rely on package-lock and pyproject metadata",
        blocked=True,
    ),
    AuditRule(
        rule_id="browser-smoke-output",
        globs=(".playwright-cli/**", ".playwright-mcp/**", "output/playwright/**"),
        reason="browser automation dumps are local smoke evidence, not release inputs",
        recommended_stage_group="do-not-stage",
        recommended_action="leave unstaged; promote only curated evidence by name",
        blocked=True,
    ),
    AuditRule(
        rule_id="local-evidence-archive",
        globs=("docs/archive/evidence-2026-05/**",),
        reason="local exhibition evidence archive keeps raw screenshots, logs, and PoC bundles out of normal release staging",
        recommended_stage_group="do-not-stage",
        recommended_action="keep local or move to external cold storage; do not stage as source",
        blocked=True,
    ),
    AuditRule(
        rule_id="test-temp-output",
        globs=("tests/.tmp/**", "**/__pycache__/**", ".pytest_cache/**"),
        reason="test temp/cache output is generated and machine-local",
        recommended_stage_group="do-not-stage",
        recommended_action="leave unstaged; regenerate from tests when needed",
        blocked=True,
    ),
    AuditRule(
        rule_id="session-generated-output",
        globs=("sessions/**", "output/**"),
        reason="session and generated output folders contain local artifacts and provider outputs",
        recommended_stage_group="do-not-stage",
        recommended_action="keep local or archive outside the normal GitHub release",
        blocked=True,
    ),
    AuditRule(
        rule_id="build-output",
        globs=("dist/**", "build/**"),
        reason="build output is generated from source and should not be staged by default",
        recommended_stage_group="do-not-stage",
        recommended_action="rebuild from source in release/CI instead of pushing generated output",
        blocked=True,
    ),
    AuditRule(
        rule_id="raw-qa-log-or-media",
        globs=(
            "qa/logs/**",
            "qa/**/*.log",
            "qa/**/*.png",
            "qa/**/*.jpg",
            "qa/**/*.jpeg",
            "qa/**/*.webp",
            "qa/**/*.yml",
            "qa/**/*.yaml",
        ),
        reason="raw QA logs/screenshots may contain device, operator, local URL, or privacy-sensitive evidence",
        recommended_stage_group="do-not-stage",
        recommended_action="summarize through a shareable QA manifest instead of staging raw evidence",
        blocked=True,
    ),
    AuditRule(
        rule_id="shareable-qa-manifest",
        globs=(
            "qa/shareable-qa-evidence*.json",
            "qa/release-stage-manifest*.json",
            "qa/mocopi-evidence-package*.json",
        ),
        reason="curated QA manifest candidate; stage only after privacy/shareable validation",
        recommended_stage_group="manual-review",
        recommended_action="stage only if the release owner approves the manifest recommendation",
        blocked=False,
    ),
    AuditRule(
        rule_id="raw-qa-json",
        globs=("qa/*.json", "qa/replay/*.json", "qa/**/*.json", "qa/*.md", "qa/**/*.md"),
        allow_globs=(
            "qa/shareable-qa-evidence*.json",
            "qa/release-stage-manifest*.json",
            "qa/mocopi-evidence-package*.json",
        ),
        reason="raw or privacy-unvalidated QA JSON should not be pushed directly",
        recommended_stage_group="do-not-stage",
        recommended_action="promote through qa/shareable-qa-evidence-latest.json if sharing is required",
        blocked=True,
    ),
    AuditRule(
        rule_id="user-feedback-media",
        globs=(
            "examples/*.jpg",
            "examples/*.jpeg",
            "examples/*.png",
            "examples/*.webp",
            "examples/*.mp4",
            "examples/*.pdf",
            "examples/*.txt",
        ),
        reason="ad-hoc user screenshots, photos, videos, or messages are not release inputs by default",
        recommended_stage_group="do-not-stage",
        recommended_action="keep local unless a named artifact is explicitly approved",
        blocked=True,
    ),
    AuditRule(
        rule_id="reference-artifact",
        globs=("docs/_smoke_renders/**", "docs/assets/**", "examples/henshin_docs*_bundle*/**", "examples/henshin_docs*_bundle*.zip"),
        reason="reference visuals/doc bundles require explicit curation before staging",
        recommended_stage_group="manual-review",
        recommended_action="stage only named reference artifacts approved for the handoff",
        blocked=False,
    ),
    AuditRule(
        rule_id="local-workspace",
        globs=(".claude/**", "blender/**"),
        reason="local agent/modeling workspaces are not normal GitHub release inputs",
        recommended_stage_group="do-not-stage",
        recommended_action="keep local; copy only reviewed assets into release paths",
        blocked=True,
    ),
    AuditRule(
        rule_id="root-transient-output",
        globs=(
            "*.log",
            "*.err",
            "*.out",
            ".tmp*",
            "*.png",
            "*.jpg",
            "*.jpeg",
            "*.webp",
            "*.yml",
            "*.yaml",
            "armor-forge-japanese-ui-*.png",
        ),
        reason="root-level transient screenshots/logs are local review artifacts",
        recommended_stage_group="do-not-stage",
        recommended_action="leave unstaged; move only curated evidence into an approved manifest",
        blocked=True,
    ),
)


def _posix(path: str) -> str:
    return path.replace("\\", "/").strip()


def _glob_matches(path: str, pattern: str) -> bool:
    normalized = _posix(path)
    normalized_pattern = _posix(pattern)
    if normalized_pattern.endswith("/**"):
        prefix = normalized_pattern[:-3]
        if prefix.startswith("**/"):
            needle = f"/{prefix[3:].rstrip('/')}/"
            return normalized == prefix[3:].rstrip("/") or needle in f"/{normalized}/"
        return normalized == prefix.rstrip("/") or normalized.startswith(prefix)
    if "/" not in normalized_pattern:
        return "/" not in normalized and fnmatch.fnmatchcase(normalized, normalized_pattern)
    if normalized_pattern.startswith("**/") and fnmatch.fnmatchcase(normalized, normalized_pattern[3:]):
        return True
    if "**" not in normalized_pattern:
        parts = normalized.split("/")
        pattern_parts = normalized_pattern.split("/")
        return len(parts) == len(pattern_parts) and all(
            fnmatch.fnmatchcase(part, pattern_part)
            for part, pattern_part in zip(parts, pattern_parts)
        )
    return fnmatch.fnmatchcase(normalized, normalized_pattern)


def _first_rule(path: str) -> tuple[AuditRule | None, str]:
    normalized = _posix(path)
    for rule in AUDIT_RULES:
        if any(_glob_matches(normalized, allowed) for allowed in rule.allow_globs):
            continue
        for pattern in rule.globs:
            if _glob_matches(normalized, pattern):
                return rule, pattern
    return None, ""


def _stage_group(category: str, rule: AuditRule | None) -> str:
    if rule is not None:
        return rule.recommended_stage_group
    return STAGE_GROUP_BY_CATEGORY.get(category, "manual-review")


def _recommended_action(category: str, rule: AuditRule | None, fallback: str) -> str:
    if rule is not None:
        return rule.recommended_action
    if category == "release-critical":
        return "review and stage with runtime/release-critical changes"
    if category == "operator-docs":
        return "review and stage with operator documentation"
    if category == "armor-assets":
        return "review and stage with catalog-referenced armor assets"
    if category == "qa-evidence":
        return "manual evidence review before staging"
    if category == "deleted-tracked-artifact":
        return "stage only in a reviewed main-based cleanup branch"
    if category in DO_NOT_STAGE_CATEGORIES:
        return "do not stage for normal GitHub push"
    return fallback or "manual review"


def _is_blocked(category: str, rule: AuditRule | None) -> bool:
    if rule is not None:
        return rule.blocked
    return category in DO_NOT_STAGE_CATEGORIES


def _audit_item(classified: dict[str, Any]) -> dict[str, Any]:
    path = _posix(str(classified["path"]))
    category = str(classified["category"])
    if category == "deleted-tracked-artifact":
        rule, matched_glob = None, ""
    else:
        rule, matched_glob = _first_rule(path)
    blocked = _is_blocked(category, rule)
    stage_group = _stage_group(category, rule)
    reason = rule.reason if rule is not None else str(classified.get("reason") or "")

    return {
        "path": path,
        "status": str(classified.get("status") or ""),
        "category": category,
        "tracked": bool(classified.get("tracked")),
        "ignored": bool(classified.get("ignored")),
        "blocked": blocked,
        "rule_id": rule.rule_id if rule is not None else f"category:{category}",
        "matched_glob": matched_glob,
        "reason": reason,
        "recommended_stage_group": stage_group,
        "recommended_action": _recommended_action(
            category,
            rule,
            str(classified.get("recommended_action") or ""),
        ),
        "old_path": str(classified.get("old_path") or ""),
    }


def _bucket_counts(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(key) or "")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _sample_items(items: list[dict[str, Any]], *, sample_limit: int) -> list[dict[str, Any]]:
    return items[: max(0, sample_limit)]


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
    return {
        value: max(0, count - len(samples.get(value, [])))
        for value, count in counts.items()
    }


def build_audit(
    repo_root: Path,
    *,
    include_ignored: bool = True,
    sample_limit: int = 10,
    full: bool = False,
) -> dict[str, Any]:
    report = stage_candidates.build_report(repo_root, include_ignored=include_ignored)
    raw_items = [dict(item) for item in report.get("items", [])]
    items = [_audit_item(item) for item in raw_items]
    blocked_items = [item for item in items if item["blocked"]]
    tracked_blocked = [item for item in blocked_items if item["tracked"]]
    samples_by_stage_group = _grouped_samples(items, key="recommended_stage_group", sample_limit=sample_limit)
    samples_by_rule = _grouped_samples(items, key="rule_id", sample_limit=sample_limit)

    blocker_reasons = [
        {
            "code": "blocked-paths-present",
            "count": len(blocked_items),
            "reason": "Paths matching do-not-stage rules are present in the dirty worktree.",
            "recommended_action": "leave blocked paths unstaged; promote only curated manifests or approved artifacts",
        }
    ] if blocked_items else []
    if tracked_blocked:
        blocker_reasons.append(
            {
                "code": "tracked-blocked-paths-present",
                "count": len(tracked_blocked),
                "reason": "Some blocked generated/local paths are already tracked and can still be staged.",
                "recommended_action": "do not stage tracked blocked modifications; use a separately reviewed git rm --cached plan if cleanup is desired",
            }
        )

    payload: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "read_only": True,
        "ok": not blocked_items,
        "repo_root": report.get("repo_root", ""),
        "source": {
            "tool": "tools/list_release_stage_candidates.py",
            "contract_version": report.get("contract_version", ""),
            "git_status": report.get("git_status", {}),
        },
        "counts": {
            "total": len(items),
            "blocked": len(blocked_items),
            "tracked_blocked": len(tracked_blocked),
            "ignored": sum(1 for item in items if item["ignored"]),
            "by_category": _bucket_counts(items, "category"),
            "by_rule": _bucket_counts(items, "rule_id"),
            "by_status": _bucket_counts(items, "status"),
            "by_recommended_stage_group": _bucket_counts(items, "recommended_stage_group"),
        },
        "blocked": _sample_items(blocked_items, sample_limit=sample_limit),
        "blocked_suppressed": max(0, len(blocked_items) - sample_limit),
        "samples_by_stage_group": samples_by_stage_group,
        "samples_by_rule": samples_by_rule,
        "suppressed_by_stage_group": _suppressed_by_key(
            items,
            samples_by_stage_group,
            key="recommended_stage_group",
        ),
        "suppressed_by_rule": _suppressed_by_key(items, samples_by_rule, key="rule_id"),
        "push_readiness": {
            "ready": not blocked_items,
            "blockers": blocker_reasons,
            "stage_groups": {
                "stage-candidate": "Review and stage intentionally in release/runtime, docs, or asset commits.",
                "manual-review": "Do not stage automatically; promote individual paths only by explicit release-owner decision.",
                "do-not-stage": "Keep out of normal GitHub staging.",
            },
        },
        "glob_rules": [
            {
                "rule_id": rule.rule_id,
                "globs": list(rule.globs),
                "allow_globs": list(rule.allow_globs),
                "blocked": rule.blocked,
                "recommended_stage_group": rule.recommended_stage_group,
                "reason": rule.reason,
                "recommended_action": rule.recommended_action,
            }
            for rule in AUDIT_RULES
        ],
        "notes": [
            "This tool is read-only and never stages, removes, commits, or pushes files.",
            "Blocked means do not include in normal GitHub staging; it is not a cleanup command.",
            "Use --full-json only when the full path list is needed; ignored/generated trees can be large.",
        ],
    }
    if full:
        payload["items"] = items
    return payload


def _json_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."), help="Git worktree root")
    parser.add_argument("--sample-limit", type=int, default=10, help="Sample paths per group")
    parser.add_argument("--no-ignored", action="store_true", help="Do not include ignored paths")
    parser.add_argument("--full-json", action="store_true", help="Include every audited item in JSON")
    parser.add_argument("--fail-on-blocked", action="store_true", help="Exit 1 when blocked paths are present")
    parser.add_argument("--report-json", "--json", action="store_true", help="Print JSON audit report")
    args = parser.parse_args(argv)

    payload = build_audit(
        args.repo_root,
        include_ignored=not args.no_ignored,
        sample_limit=args.sample_limit,
        full=args.full_json,
    )
    if args.report_json or args.full_json:
        sys.stdout.write(_json_payload(payload))
    else:
        print(f"repo readiness: {payload['repo_root']}")
        print(f"ok={payload['ok']} blocked={payload['counts']['blocked']} total={payload['counts']['total']}")
        for group, count in payload["counts"]["by_recommended_stage_group"].items():
            print(f"{group}: {count}")

    if args.fail_on_blocked and not payload["ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
