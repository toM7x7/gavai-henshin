from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "validate_release_stage_manifest.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("validate_release_stage_manifest", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["validate_release_stage_manifest"] = module
    spec.loader.exec_module(module)
    return module


tool = _load_tool()


def _category(count: int, *, stage_policy: str, recommended_action: str) -> dict:
    return {
        "count": count,
        "samples": [],
        "sample_count": 0,
        "suppressed": 0,
        "stage_policy": stage_policy,
        "recommended_action": recommended_action,
    }


def _manifest(
    *,
    release_critical: int = 1,
    operator_docs: int = 1,
    armor_assets: int = 1,
    qa_evidence: int = 0,
    local_qa_artifact: int = 0,
    reference_docs: int = 0,
    reference_artifact: int = 0,
    user_feedback_media: int = 0,
    local_workspace: int = 0,
    local_only_root: int = 0,
    deleted_tracked_artifact: int = 0,
    ambiguous: int = 0,
    generated_artifact: int = 0,
    generated_policy: str = "do-not-stage",
    generated_action: str = "do not stage for the normal GitHub release",
) -> dict:
    counts = {
        "release-critical": release_critical,
        "operator-docs": operator_docs,
        "armor-assets": armor_assets,
        "qa-evidence": qa_evidence,
        "local-qa-artifact": local_qa_artifact,
        "reference-docs": reference_docs,
        "reference-artifact": reference_artifact,
        "user-feedback-media": user_feedback_media,
        "local-workspace": local_workspace,
        "local-only-root": local_only_root,
        "deleted-tracked-artifact": deleted_tracked_artifact,
        "ambiguous": ambiguous,
        "generated-artifact": generated_artifact,
    }
    blockers = []
    if ambiguous:
        blockers.append({"code": "ambiguous-changes-present", "category": "ambiguous"})
    return {
        "contract_version": "release-stage-manifest.v5",
        "read_only": True,
        "repo_root": "C:/repo",
        "counts": {"total": sum(counts.values()), "by_category": counts, "tracked_artifact_candidates": 0},
        "categories": {
            "release-critical": _category(release_critical, stage_policy="stage-candidate", recommended_action="stage"),
            "operator-docs": _category(operator_docs, stage_policy="stage-candidate", recommended_action="stage"),
            "armor-assets": _category(armor_assets, stage_policy="stage-candidate", recommended_action="stage"),
            "qa-evidence": _category(
                qa_evidence,
                stage_policy="manual-evidence-review",
                recommended_action="stage only shareable QA evidence manifests",
            ),
            "local-qa-artifact": _category(
                local_qa_artifact,
                stage_policy="do-not-stage",
                recommended_action="do not stage local/raw QA evidence",
            ),
            "reference-docs": _category(
                reference_docs,
                stage_policy="manual-doc-review",
                recommended_action="stage only promoted reference docs",
            ),
            "reference-artifact": _category(
                reference_artifact,
                stage_policy="manual-reference-review",
                recommended_action="stage only curated reference artifacts",
            ),
            "user-feedback-media": _category(
                user_feedback_media,
                stage_policy="do-not-stage",
                recommended_action="do not stage user media",
            ),
            "local-workspace": _category(
                local_workspace,
                stage_policy="do-not-stage",
                recommended_action="do not stage local workspace files",
            ),
            "local-only-root": _category(
                local_only_root,
                stage_policy="do-not-stage",
                recommended_action="do not stage local-only root files",
            ),
            "deleted-tracked-artifact": _category(
                deleted_tracked_artifact,
                stage_policy="manual-review",
                recommended_action="commit the tracked deletion in a dedicated cleanup commit",
            ),
            "ambiguous": _category(ambiguous, stage_policy="manual-review", recommended_action="manual review"),
            "generated-artifact": _category(
                generated_artifact,
                stage_policy=generated_policy,
                recommended_action=generated_action,
            ),
        },
        "stage_decision": {
            "stage_candidates": {
                "categories": ["release-critical", "operator-docs", "armor-assets"],
                "count": release_critical + operator_docs + armor_assets,
                "by_category": {},
            },
            "manual_review": {
                "categories": [
                    "qa-evidence",
                    "reference-docs",
                    "reference-artifact",
                    "deleted-tracked-artifact",
                    "ambiguous",
                ],
                "count": qa_evidence + reference_docs + reference_artifact + deleted_tracked_artifact + ambiguous,
                "by_category": {},
            },
            "do_not_stage": {
                "categories": [
                    "local-qa-artifact",
                    "user-feedback-media",
                    "local-workspace",
                    "local-only-root",
                    "generated-artifact",
                ],
                "count": local_qa_artifact + user_feedback_media + local_workspace + local_only_root + generated_artifact,
                "by_category": {},
            },
        },
        "push_readiness": {"ready": not blockers, "blockers": blockers, "warnings": []},
    }


def test_validate_manifest_payload_passes_minimal_manifest(tmp_path: Path) -> None:
    result = tool.validate_manifest_payload(
        _manifest(),
        repo_root=tmp_path,
        manifest_path="manifest.json",
    )

    assert result["ok"] is True
    assert result["status"] == "pass"
    assert result["blockers"] == []


def test_validate_manifest_payload_reports_manifest_contract_blockers(tmp_path: Path) -> None:
    manifest = _manifest(
        release_critical=0,
        ambiguous=2,
        generated_policy="stage-candidate",
        generated_action="stage in release commit",
    )
    manifest["categories"].pop("qa-evidence")
    manifest["counts"]["by_category"].pop("qa-evidence")
    manifest["push_readiness"]["blockers"] = []
    manifest["stage_decision"].pop("manual_review")

    result = tool.validate_manifest_payload(
        manifest,
        repo_root=tmp_path,
        manifest_path="manifest.json",
    )
    codes = {issue["code"] for issue in result["blockers"]}

    assert result["ok"] is False
    assert "missing-category-qa-evidence" in codes
    assert "missing-count-qa-evidence" in codes
    assert "release-critical-count-not-positive" in codes
    assert "ambiguous-count-not-blocking" in codes
    assert "ambiguous-changes-present" in codes
    assert "generated-artifact-stage-policy-invalid" in codes
    assert "generated-artifact-action-invalid" in codes
    assert "stage-decision-manual_review-categories-invalid" in codes


def test_validate_manifest_blocks_do_not_stage_policy_drift(tmp_path: Path) -> None:
    manifest = _manifest(local_qa_artifact=1, user_feedback_media=1)
    manifest["categories"]["local-qa-artifact"]["stage_policy"] = "stage-candidate"
    manifest["categories"]["user-feedback-media"]["recommended_action"] = "stage user screenshots"

    result = tool.validate_manifest_payload(
        manifest,
        repo_root=tmp_path,
        manifest_path="manifest.json",
    )
    codes = {issue["code"] for issue in result["blockers"]}

    assert "local-qa-artifact-stage-policy-invalid" in codes
    assert "user-feedback-media-action-invalid" in codes


def test_validate_manifest_blocks_raw_qa_sample_in_qa_evidence(tmp_path: Path) -> None:
    manifest = _manifest(qa_evidence=1, local_qa_artifact=1)
    manifest["categories"]["qa-evidence"]["samples"] = [
        {"path": "qa/exhibition_release_package_latest.json", "status": "??"}
    ]

    result = tool.validate_manifest_payload(
        manifest,
        repo_root=tmp_path,
        manifest_path="manifest.json",
    )
    codes = {issue["code"] for issue in result["blockers"]}

    assert "qa-evidence-sample-classifier-mismatch" in codes


def test_package_report_alignment_detects_required_untracked_and_mismatch(tmp_path: Path) -> None:
    package_report = {
        "missing_count": 0,
        "pattern_gap_count": 0,
        "untracked_count": 120,
        "tracked_candidate_count": 100,
        "untracked": [
            {
                "path": ".env.demo.example",
                "categories": ["runtime"],
                "reason": "critical release-package file exists but is not tracked by git",
            },
            {
                "path": "docs/exhibition-pc-runbook-2026-05-04.md",
                "categories": ["operator_docs"],
                "reason": "critical release-package file exists but is not tracked by git",
            },
            {
                "path": "viewer/assets/armor-parts/helmet/helmet.glb",
                "categories": ["armor"],
                "reason": "critical release-package file exists but is not tracked by git",
            },
            {
                "path": "docs/modeler-handoff-2026-05-01.md",
                "categories": ["operator_docs"],
                "reason": "critical release-package file exists but is not tracked by git",
            },
        ],
    }
    result = tool.validate_manifest_payload(
        _manifest(release_critical=5, operator_docs=5, armor_assets=5),
        repo_root=tmp_path,
        manifest_path="manifest.json",
        package_report=package_report,
        package_report_path="package.json",
    )
    blocker_codes = {issue["code"] for issue in result["blockers"]}
    warning_codes = {issue["code"] for issue in result["warnings"]}
    blocker = next(issue for issue in result["blockers"] if issue["code"] == "package-report-untracked-required-files")
    alignment = result["package_manifest_alignment"]

    assert "package-report-untracked-required-files" in blocker_codes
    assert "package-untracked-count-exceeds-manifest-stage-candidates" in warning_codes
    assert alignment["required_untracked_count"] == 120
    assert alignment["recommended_stage_groups"]["release-critical"]["paths_sample"] == [".env.demo.example"]
    assert alignment["recommended_stage_groups"]["operator-docs"]["paths_sample"] == [
        "docs/exhibition-pc-runbook-2026-05-04.md"
    ]
    assert alignment["recommended_stage_groups"]["armor-assets"]["paths_sample"] == [
        "viewer/assets/armor-parts/helmet/helmet.glb"
    ]
    assert alignment["manual_review_groups"]["reference-docs"]["paths_sample"] == [
        "docs/modeler-handoff-2026-05-01.md"
    ]
    assert blocker["required_untracked_paths_sample"][0]["stage_category"] == "release-critical"
    assert blocker["recommended_stage_groups"] == alignment["recommended_stage_groups"]


def test_missing_manifest_reports_existing_qa_json(tmp_path: Path) -> None:
    qa_dir = tmp_path / "qa"
    qa_dir.mkdir()
    (qa_dir / "exhibition_release_package_latest.json").write_text("{}", encoding="utf-8")

    result = tool.validate_manifest_payload(
        None,
        repo_root=tmp_path,
        manifest_path="qa/release-stage-manifest-latest.json",
    )
    codes = {issue["code"] for issue in result["blockers"]}

    assert result["ok"] is False
    assert "manifest-missing" in codes
    assert "qa-evidence-present-without-stage-manifest" in codes
    assert result["local_qa_json_count"] == 1


def test_curated_qa_json_warning_requires_curated_candidate(tmp_path: Path) -> None:
    qa_dir = tmp_path / "qa"
    qa_dir.mkdir()
    (qa_dir / "shareable-qa-evidence-latest.json").write_text("{}", encoding="utf-8")

    result = tool.validate_manifest_payload(
        _manifest(qa_evidence=0),
        repo_root=tmp_path,
        manifest_path="manifest.json",
    )
    warning_codes = {issue["code"] for issue in result["warnings"]}

    assert "qa-json-present-but-no-qa-evidence-candidates" in warning_codes
    assert result["local_qa_json_by_category"]["qa-evidence"] == ["qa/shareable-qa-evidence-latest.json"]


def test_local_raw_qa_json_without_curated_evidence_does_not_warn_when_classified(tmp_path: Path) -> None:
    qa_dir = tmp_path / "qa"
    qa_dir.mkdir()
    (qa_dir / "runtime-package-3601.snapshot.json").write_text("{}", encoding="utf-8")

    result = tool.validate_manifest_payload(
        _manifest(qa_evidence=0, local_qa_artifact=1),
        repo_root=tmp_path,
        manifest_path="manifest.json",
    )
    warning_codes = {issue["code"] for issue in result["warnings"]}

    assert "qa-json-present-but-no-qa-evidence-candidates" not in warning_codes
    assert "local-qa-json-present-but-no-local-artifact-candidates" not in warning_codes
    assert result["local_qa_json_by_category"]["local-qa-artifact"] == ["qa/runtime-package-3601.snapshot.json"]


def test_cli_reads_utf16_package_report_and_reports_json(tmp_path: Path, capsys) -> None:
    manifest_path = tmp_path / "manifest.json"
    package_path = tmp_path / "package.json"
    manifest_path.write_text(json.dumps(_manifest()), encoding="utf-8")
    package_path.write_text(
        json.dumps(
            {
                "missing_count": 0,
                "pattern_gap_count": 0,
                "untracked_count": 2,
                "tracked_candidate_count": 10,
                "untracked": [
                    {
                        "path": ".env.demo.example",
                        "categories": ["runtime"],
                        "reason": "critical release-package file exists but is not tracked by git",
                    }
                ],
            }
        ),
        encoding="utf-16",
    )

    rc = tool.main(
        [
            "--repo-root",
            str(tmp_path),
            "--manifest",
            str(manifest_path),
            "--package-report",
            str(package_path),
            "--report-json",
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert rc == 1
    assert payload["inputs"]["package_report_loaded"] is True
    assert payload["package_report_counts"]["untracked_count"] == 2
    assert payload["blockers"][0]["code"] == "package-report-untracked-required-files"
    assert payload["blockers"][0]["recommended_stage_groups"]["release-critical"]["paths_sample"] == [
        ".env.demo.example"
    ]


def test_cli_accepts_manifest_from_stdin(tmp_path: Path, capsys) -> None:
    rc = tool.main(
        ["--repo-root", str(tmp_path), "--manifest", "-", "--report-json"],
        stdin_text=json.dumps(_manifest()),
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert rc == 0
    assert payload["inputs"]["manifest"] == "<stdin>"
    assert payload["ok"] is True
