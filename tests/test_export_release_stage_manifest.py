from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"
TOOL_PATH = TOOLS_DIR / "export_release_stage_manifest.py"


def _load_tool():
    if str(TOOLS_DIR) not in sys.path:
        sys.path.insert(0, str(TOOLS_DIR))
    spec = importlib.util.spec_from_file_location("export_release_stage_manifest", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["export_release_stage_manifest"] = module
    spec.loader.exec_module(module)
    return module


tool = _load_tool()


def _summary() -> dict:
    return {
        "contract_version": "release-stage-candidates.v7.summary",
        "repo_root": "C:/repo",
        "read_only": True,
        "summary": True,
        "sample_limit": 2,
        "git_status": {"include_ignored": True},
        "counts": {
            "total": 18,
            "by_category": {
                "release-critical": 2,
                "operator-docs": 1,
                "armor-assets": 1,
                "qa-evidence": 1,
                "local-qa-artifact": 1,
                "reference-docs": 2,
                "reference-artifact": 1,
                "user-feedback-media": 1,
                "local-workspace": 1,
                "local-only-root": 1,
                "deleted-tracked-artifact": 1,
                "generated-artifact": 3,
                "ambiguous": 2,
            },
            "by_status": {"??": 8, " M": 2},
            "tracked_artifact_candidates": 1,
        },
        "samples": {
            "release-critical": [{"path": ".env.demo.example", "recommended_action": "stage-candidate"}],
            "qa-evidence": [{"path": "qa/shareable-qa-evidence-latest.json", "recommended_action": "manual-evidence-review"}],
            "generated-artifact": [{"path": "tests/.tmp/quest-api-live.err.log"}],
            "ambiguous": [{"path": "docs/random-note.md"}],
            "reference-docs": [{"path": "docs/modeler-handoff-2026-05-01.md"}],
            "reference-artifact": [{"path": "docs/assets/hero-suit-surface-fit-concept.svg"}],
            "user-feedback-media": [{"path": "examples/screenshot.png"}],
            "local-workspace": [{"path": "blender/review_master.blend"}],
            "local-only-root": [{"path": "node_modules/.package-lock.json"}],
            "deleted-tracked-artifact": [{"path": ".playwright-cli/page.png"}],
        },
        "suppressed": {
            "release-critical": 1,
            "operator-docs": 0,
            "armor-assets": 0,
            "qa-evidence": 0,
            "local-qa-artifact": 0,
            "reference-docs": 1,
            "reference-artifact": 0,
            "user-feedback-media": 0,
            "local-workspace": 0,
            "local-only-root": 0,
            "deleted-tracked-artifact": 0,
            "generated-artifact": 2,
            "ambiguous": 1,
        },
    }


def test_build_manifest_includes_category_actions_and_push_readiness() -> None:
    manifest = tool.build_manifest(_summary())

    assert manifest["contract_version"] == "release-stage-manifest.v5"
    assert manifest["read_only"] is True
    assert manifest["categories"]["release-critical"]["count"] == 2
    assert manifest["categories"]["release-critical"]["stage_policy"] == "stage-candidate"
    assert "shareable QA evidence" in manifest["categories"]["qa-evidence"]["recommended_action"]
    assert manifest["categories"]["local-qa-artifact"]["stage_policy"] == "do-not-stage"
    assert manifest["categories"]["reference-docs"]["stage_policy"] == "manual-doc-review"
    assert manifest["categories"]["reference-artifact"]["stage_policy"] == "manual-reference-review"
    assert manifest["categories"]["user-feedback-media"]["stage_policy"] == "do-not-stage"
    assert manifest["categories"]["local-workspace"]["stage_policy"] == "do-not-stage"
    assert manifest["categories"]["local-only-root"]["stage_policy"] == "do-not-stage"
    assert manifest["categories"]["deleted-tracked-artifact"]["stage_policy"] == "cleanup-deletion-review"
    assert manifest["categories"]["generated-artifact"]["stage_policy"] == "do-not-stage"
    assert manifest["categories"]["ambiguous"]["samples"][0]["path"] == "docs/random-note.md"
    assert manifest["stage_decision"]["stage_candidates"]["categories"] == [
        "release-critical",
        "operator-docs",
        "armor-assets",
    ]
    assert manifest["stage_decision"]["do_not_stage"]["categories"] == [
        "local-qa-artifact",
        "user-feedback-media",
        "local-workspace",
        "local-only-root",
        "generated-artifact",
    ]
    assert manifest["stage_decision"]["do_not_stage"]["count"] == 7

    readiness = manifest["push_readiness"]
    assert readiness["ready"] is False
    blocker_codes = {item["code"] for item in readiness["blockers"]}
    assert blocker_codes == {"ambiguous-changes-present", "tracked-generated-artifacts-present"}
    warning_codes = {item["code"] for item in readiness["warnings"]}
    assert "generated-artifacts-present" in warning_codes
    assert "qa-evidence-needs-explicit-approval" in warning_codes
    assert "local-qa-artifacts-present" in warning_codes
    assert "reference-docs-present" in warning_codes
    assert "reference-artifacts-present" in warning_codes
    assert "user-feedback-media-present" in warning_codes
    assert "local-workspace-present" in warning_codes
    assert "local-only-roots-present" in warning_codes
    assert "deleted-tracked-artifacts-present" in warning_codes
    assert "summary-suppressed-paths" in warning_codes


def test_cli_writes_manifest_and_can_report_json(monkeypatch, tmp_path: Path, capsys) -> None:
    calls: list[dict] = []

    def fake_summary(repo_root: Path, *, include_ignored: bool, sample_limit: int) -> dict:
        calls.append(
            {
                "repo_root": repo_root,
                "include_ignored": include_ignored,
                "sample_limit": sample_limit,
            }
        )
        payload = _summary()
        payload["repo_root"] = tmp_path.resolve().as_posix()
        payload["sample_limit"] = sample_limit
        return payload

    monkeypatch.setattr(tool.stage_candidates, "build_summary_report", fake_summary)

    rc = tool.main(
        [
            "--repo-root",
            str(tmp_path),
            "--out",
            "qa/release-stage-manifest-latest.json",
            "--sample-limit",
            "1",
            "--report-json",
        ]
    )
    captured = capsys.readouterr()
    stdout_payload = json.loads(captured.out)
    written_path = tmp_path / "qa" / "release-stage-manifest-latest.json"
    file_payload = json.loads(written_path.read_text(encoding="utf-8"))

    assert rc == 0
    assert calls == [{"repo_root": tmp_path, "include_ignored": True, "sample_limit": 1}]
    assert stdout_payload == file_payload
    assert file_payload["output_path"] == written_path.resolve().as_posix()
    assert file_payload["source"]["sample_limit"] == 1
    assert file_payload["push_readiness"]["blockers"][0]["severity"] == "blocker"
