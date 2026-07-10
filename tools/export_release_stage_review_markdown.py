"""Export a human-readable release stage review checklist as Markdown."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import export_release_stage_manifest as manifest_exporter
import validate_release_stage_manifest as manifest_validator


CONTRACT_VERSION = "release-stage-review-markdown.v2"
DEFAULT_MANIFEST = Path("qa/release-stage-manifest-latest.json")
DEFAULT_PACKAGE_REPORT = Path("qa/exhibition_release_package_latest.json")
DEFAULT_OUT = Path("docs/release-stage-review-latest.md")
STAGE_CATEGORIES = ("release-critical", "operator-docs", "armor-assets")
LOCAL_ONLY_CATEGORIES = (
    "local-qa-artifact",
    "reference-docs",
    "reference-artifact",
    "user-feedback-media",
    "local-workspace",
)


def _read_json(path: Path) -> dict[str, Any]:
    payload = manifest_validator._read_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def _category(manifest: dict[str, Any], category: str) -> dict[str, Any]:
    value = manifest.get("categories", {}).get(category)
    return value if isinstance(value, dict) else {}


def _category_count(manifest: dict[str, Any], category: str) -> int:
    value = _category(manifest, category).get("count")
    if value is not None:
        return int(value or 0)
    return int(manifest.get("counts", {}).get("by_category", {}).get(category, 0) or 0)


def _manifest_paths(manifest: dict[str, Any], category: str, *, limit: int = 10) -> list[str]:
    samples = _category(manifest, category).get("samples")
    if not isinstance(samples, list):
        return []
    paths: list[str] = []
    for item in samples:
        if isinstance(item, dict) and item.get("path"):
            paths.append(str(item["path"]))
        if len(paths) >= limit:
            break
    return paths


def _alignment_group(validation: dict[str, Any], category: str) -> dict[str, Any]:
    alignment = validation.get("package_manifest_alignment")
    if not isinstance(alignment, dict):
        return {}
    groups = alignment.get("recommended_stage_groups")
    if not isinstance(groups, dict):
        return {}
    value = groups.get(category)
    return value if isinstance(value, dict) else {}


def _manual_groups(validation: dict[str, Any]) -> dict[str, Any]:
    alignment = validation.get("package_manifest_alignment")
    if not isinstance(alignment, dict):
        return {}
    groups = alignment.get("manual_review_groups")
    return groups if isinstance(groups, dict) else {}


def _issue_codes(validation: dict[str, Any], key: str) -> list[str]:
    issues = validation.get(key)
    if not isinstance(issues, list):
        return []
    return [str(issue.get("code")) for issue in issues if isinstance(issue, dict) and issue.get("code")]


def _stage_decision_group(manifest: dict[str, Any], group_name: str) -> dict[str, Any]:
    stage_decision = manifest.get("stage_decision")
    if not isinstance(stage_decision, dict):
        return {}
    group = stage_decision.get(group_name)
    return group if isinstance(group, dict) else {}


def _bullet_paths(paths: list[str], *, indent: str = "- ") -> list[str]:
    return [f"{indent}`{path}`" for path in paths]


def _section_for_stage_summary(manifest: dict[str, Any]) -> list[str]:
    lines = [
        "## stage_summary",
        "",
        "Use this section as the mechanical split before manual `git add`.",
    ]
    for group_name, label in (
        ("stage_candidates", "Staging candidates"),
        ("manual_review", "Manual review"),
        ("do_not_stage", "Exclude from normal staging"),
    ):
        group = _stage_decision_group(manifest, group_name)
        categories = group.get("categories") if isinstance(group.get("categories"), list) else []
        lines.extend(
            [
                "",
                f"### {label}",
                f"- Count: `{int(group.get('count') or 0)}`",
                f"- Categories: `{', '.join(str(category) for category in categories)}`",
            ]
        )
    lines.append("")
    return lines


def _section_for_stage_category(manifest: dict[str, Any], validation: dict[str, Any], category: str) -> list[str]:
    category_payload = _category(manifest, category)
    group = _alignment_group(validation, category)
    lines = [
        f"## {category}",
        "",
        f"- Manifest count: `{_category_count(manifest, category)}`",
        f"- Stage policy: `{category_payload.get('stage_policy', '')}`",
        f"- Recommended action: {category_payload.get('recommended_action', '')}",
        f"- Required untracked package candidates: `{int(group.get('count') or 0)}`",
    ]
    package_categories = group.get("package_categories")
    if isinstance(package_categories, dict) and package_categories:
        joined = ", ".join(f"{name}={count}" for name, count in sorted(package_categories.items()))
        lines.append(f"- Package validator groups: `{joined}`")
    paths = [str(path) for path in group.get("paths_sample", []) if path] if group else []
    if not paths:
        paths = _manifest_paths(manifest, category)
    if paths:
        lines.extend(["", "Review sample paths:"])
        lines.extend(_bullet_paths(paths))
    lines.append("")
    return lines


def _section_for_qa(manifest: dict[str, Any]) -> list[str]:
    category = "qa-evidence"
    payload = _category(manifest, category)
    lines = [
        f"## {category}",
        "",
        f"- Manifest count: `{_category_count(manifest, category)}`",
        f"- Stage policy: `{payload.get('stage_policy', '')}`",
        f"- Recommended action: {payload.get('recommended_action', '')}",
        "- Stage only shareable QA manifests or paths explicitly recommended by `qa/shareable-qa-evidence-latest.json`.",
    ]
    paths = _manifest_paths(manifest, category)
    if paths:
        lines.extend(["", "Review sample paths:"])
        lines.extend(_bullet_paths(paths))
    lines.append("")
    return lines


def _section_for_local_only(manifest: dict[str, Any], validation: dict[str, Any]) -> list[str]:
    lines = [
        "## local-only",
        "",
        "These groups are not normal release staging inputs. Promote individual files only by explicit release-owner decision.",
    ]
    manual_groups = _manual_groups(validation)
    for category in LOCAL_ONLY_CATEGORIES:
        payload = _category(manifest, category)
        manual = manual_groups.get(category) if isinstance(manual_groups.get(category), dict) else {}
        count = _category_count(manifest, category)
        manual_count = int(manual.get("count") or 0) if manual else 0
        lines.extend(
            [
                "",
                f"### {category}",
                f"- Manifest count: `{count}`",
                f"- Manual required-untracked count: `{manual_count}`",
                f"- Stage policy: `{payload.get('stage_policy', '')}`",
                f"- Recommended action: {payload.get('recommended_action', '')}",
            ]
        )
        paths = [str(path) for path in manual.get("paths_sample", []) if path] if manual else []
        if not paths:
            paths = _manifest_paths(manifest, category, limit=5)
        if paths:
            lines.extend(_bullet_paths(paths))
    lines.append("")
    return lines


def _section_for_do_not_stage(manifest: dict[str, Any]) -> list[str]:
    generated = _category(manifest, "generated-artifact")
    lines = [
        "## do-not-stage",
        "",
        f"- generated-artifact count: `{_category_count(manifest, 'generated-artifact')}`",
        f"- generated-artifact policy: `{generated.get('stage_policy', '')}`",
        f"- generated-artifact action: {generated.get('recommended_action', '')}",
    ]
    patterns = manifest.get("do_not_stage")
    if isinstance(patterns, list) and patterns:
        lines.extend(["", "Keep these out of normal release staging:"])
        lines.extend(_bullet_paths([str(pattern) for pattern in patterns], indent="- "))
    paths = _manifest_paths(manifest, "generated-artifact", limit=8)
    if paths:
        lines.extend(["", "Generated sample paths:"])
        lines.extend(_bullet_paths(paths))
    lines.append("")
    return lines


def _section_for_final_commands() -> list[str]:
    return [
        "## final_commands",
        "",
        "Run these read-only/review commands before any manual staging:",
        "",
        "```powershell",
        "python tools\\list_release_stage_candidates.py --summary-json --sample-limit 20",
        "python tools\\export_release_stage_manifest.py --out qa\\release-stage-manifest-latest.json --sample-limit 20",
        "python tools\\validate_release_stage_manifest.py --manifest qa\\release-stage-manifest-latest.json --package-report qa\\exhibition_release_package_latest.json --report-json",
        "python tools\\export_release_stage_review_markdown.py --out docs\\release-stage-review-latest.md --report-json",
        "git status --short",
        "git diff --check -- tools docs tests",
        "git diff --cached --stat",
        "git diff --cached --name-status",
        "```",
        "",
    ]


def render_markdown(manifest: dict[str, Any], validation: dict[str, Any]) -> str:
    blockers = _issue_codes(validation, "blockers")
    warnings = _issue_codes(validation, "warnings")
    lines = [
        "# Release Stage Review",
        "",
        "- Read-only review output. This file does not stage, commit, or push.",
        f"- Manifest contract: `{manifest.get('contract_version', '')}`",
        f"- Validation contract: `{validation.get('contract_version', '')}`",
        f"- Validation status: `{validation.get('status', 'unknown')}`",
        f"- Validation ok: `{str(bool(validation.get('ok'))).lower()}`",
        f"- Blockers: `{', '.join(blockers) if blockers else 'none'}`",
        f"- Warnings: `{', '.join(warnings) if warnings else 'none'}`",
        "",
    ]
    lines.extend(_section_for_stage_summary(manifest))
    for category in STAGE_CATEGORIES:
        lines.extend(_section_for_stage_category(manifest, validation, category))
    lines.extend(_section_for_qa(manifest))
    lines.extend(_section_for_local_only(manifest, validation))
    lines.extend(_section_for_do_not_stage(manifest))
    lines.extend(_section_for_final_commands())
    return "\n".join(lines).rstrip() + "\n"


def _load_or_generate_manifest(repo_root: Path, manifest_path: Path, sample_limit: int) -> tuple[dict[str, Any], str]:
    path = _resolve(repo_root, manifest_path)
    if path.is_file():
        return _read_json(path), path.as_posix()
    return manifest_exporter.export_manifest(repo_root, sample_limit=sample_limit), "<generated>"


def _load_or_generate_validation(
    repo_root: Path,
    manifest: dict[str, Any],
    manifest_source: str,
    validation_report_path: Path | None,
    package_report_path: Path | None,
) -> tuple[dict[str, Any], str]:
    if validation_report_path is not None:
        path = _resolve(repo_root, validation_report_path)
        if path.is_file():
            return _read_json(path), path.as_posix()
    package_report = None
    package_source = ""
    if package_report_path is not None:
        package_path = _resolve(repo_root, package_report_path)
        if package_path.is_file():
            package_report = _read_json(package_path)
            package_source = package_path.as_posix()
    return (
        manifest_validator.validate_manifest_payload(
            manifest,
            repo_root=repo_root,
            manifest_path=manifest_source,
            package_report=package_report,
            package_report_path=package_source,
        ),
        "<generated>",
    )


def build_review(
    repo_root: Path,
    *,
    manifest_path: Path = DEFAULT_MANIFEST,
    validation_report_path: Path | None = None,
    package_report_path: Path | None = DEFAULT_PACKAGE_REPORT,
    sample_limit: int = 20,
) -> dict[str, Any]:
    root = repo_root.resolve()
    manifest, manifest_source = _load_or_generate_manifest(root, manifest_path, sample_limit)
    validation, validation_source = _load_or_generate_validation(
        root,
        manifest,
        manifest_source,
        validation_report_path,
        package_report_path,
    )
    markdown = render_markdown(manifest, validation)
    return {
        "contract_version": CONTRACT_VERSION,
        "read_only": True,
        "repo_root": root.as_posix(),
        "inputs": {
            "manifest": manifest_source,
            "validation_report": validation_source,
            "package_report": validation.get("inputs", {}).get("package_report", "")
            if isinstance(validation.get("inputs"), dict)
            else "",
        },
        "validation_status": validation.get("status", "unknown"),
        "validation_ok": bool(validation.get("ok")),
        "blockers": _issue_codes(validation, "blockers"),
        "warnings": _issue_codes(validation, "warnings"),
        "section_counts": {
            category: _category_count(manifest, category)
            for category in (
                "release-critical",
                "operator-docs",
                "armor-assets",
                "qa-evidence",
                "local-qa-artifact",
                "reference-docs",
                "reference-artifact",
                "user-feedback-media",
                "local-workspace",
                "generated-artifact",
                "ambiguous",
            )
        },
        "recommended_stage_groups": validation.get("package_manifest_alignment", {}).get("recommended_stage_groups", {})
        if isinstance(validation.get("package_manifest_alignment"), dict)
        else {},
        "manual_review_groups": validation.get("package_manifest_alignment", {}).get("manual_review_groups", {})
        if isinstance(validation.get("package_manifest_alignment"), dict)
        else {},
        "markdown": markdown,
    }


def _json_payload(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."), help="Git worktree root")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="Release stage manifest JSON")
    parser.add_argument("--validation-report", type=Path, help="Optional validate_release_stage_manifest JSON")
    parser.add_argument("--package-report", type=Path, default=DEFAULT_PACKAGE_REPORT, help="Optional package validator JSON")
    parser.add_argument("--sample-limit", type=int, default=20, help="Sample paths per generated manifest category")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="Write Markdown review to this path")
    parser.add_argument("--report-json", action="store_true", help="Print JSON metadata to stdout")
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    review = build_review(
        repo_root,
        manifest_path=args.manifest,
        validation_report_path=args.validation_report,
        package_report_path=args.package_report,
        sample_limit=args.sample_limit,
    )
    out_path = _resolve(repo_root, args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(review["markdown"], encoding="utf-8")
    review["output_path"] = out_path.resolve().as_posix()

    if args.report_json:
        payload = {key: value for key, value in review.items() if key != "markdown"}
        sys.stdout.write(_json_payload(payload))
    else:
        sys.stdout.write(f"Wrote {out_path.as_posix()}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
