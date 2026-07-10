from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"
TOOL_PATH = TOOLS_DIR / "export_release_stage_review_markdown.py"


def _load_tool():
    if str(TOOLS_DIR) not in sys.path:
        sys.path.insert(0, str(TOOLS_DIR))
    spec = importlib.util.spec_from_file_location("export_release_stage_review_markdown", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["export_release_stage_review_markdown"] = module
    spec.loader.exec_module(module)
    return module


tool = _load_tool()


def _category(
    count: int,
    *,
    stage_policy: str = "stage-candidate",
    recommended_action: str = "review and stage",
    samples: list[dict] | None = None,
) -> dict:
    return {
        "count": count,
        "samples": samples or [],
        "sample_count": len(samples or []),
        "suppressed": 0,
        "stage_policy": stage_policy,
        "recommended_action": recommended_action,
    }


def _manifest() -> dict:
    categories = {
        "release-critical": _category(2, samples=[{"path": ".env.demo.example"}]),
        "operator-docs": _category(1, recommended_action="stage required operator docs"),
        "armor-assets": _category(3, recommended_action="stage armor assets"),
        "qa-evidence": _category(
            1,
            stage_policy="manual-evidence-review",
            recommended_action="stage only shareable QA evidence manifests",
            samples=[{"path": "qa/shareable-qa-evidence-latest.json"}],
        ),
        "local-qa-artifact": _category(
            1,
            stage_policy="do-not-stage",
            recommended_action="do not stage local/raw QA evidence",
            samples=[{"path": "qa/runtime-package-3601.snapshot.json"}],
        ),
        "reference-docs": _category(1, stage_policy="manual-doc-review", recommended_action="stage only promoted docs"),
        "reference-artifact": _category(
            1,
            stage_policy="manual-reference-review",
            recommended_action="stage only curated reference artifacts",
        ),
        "user-feedback-media": _category(1, stage_policy="do-not-stage", recommended_action="do not stage user media"),
        "local-workspace": _category(1, stage_policy="do-not-stage", recommended_action="do not stage local workspace"),
        "generated-artifact": _category(
            5,
            stage_policy="do-not-stage",
            recommended_action="do not stage for the normal GitHub release",
            samples=[{"path": "tests/.tmp/quest-api-live.err.log"}],
        ),
        "ambiguous": _category(0, stage_policy="manual-review", recommended_action="manual review"),
    }
    return {
        "contract_version": "release-stage-manifest.v5",
        "read_only": True,
        "repo_root": "C:/repo",
        "counts": {"by_category": {name: value["count"] for name, value in categories.items()}},
        "categories": categories,
        "stage_decision": {
            "stage_candidates": {
                "categories": ["release-critical", "operator-docs", "armor-assets"],
                "count": 6,
                "by_category": {},
            },
            "manual_review": {
                "categories": ["qa-evidence", "reference-docs", "reference-artifact", "ambiguous"],
                "count": 3,
                "by_category": {},
            },
            "do_not_stage": {
                "categories": ["local-qa-artifact", "user-feedback-media", "local-workspace", "generated-artifact"],
                "count": 8,
                "by_category": {},
            },
        },
        "do_not_stage": ["tests/.tmp/**", "qa/logs/**", "blender/**"],
    }


def _validation() -> dict:
    return {
        "contract_version": "release-stage-manifest-validation.v6",
        "read_only": True,
        "ok": False,
        "status": "fail",
        "inputs": {
            "manifest": "qa/release-stage-manifest-latest.json",
            "package_report": "qa/exhibition_release_package_latest.json",
            "package_report_loaded": True,
        },
        "package_manifest_alignment": {
            "recommended_stage_groups": {
                "release-critical": {
                    "count": 1,
                    "paths_sample": [".env.demo.example"],
                    "package_categories": {"runtime": 1},
                    "recommended_action": "review and stage in the runtime/release-critical commit",
                    "stage_policy": "stage-candidate",
                },
                "operator-docs": {
                    "count": 1,
                    "paths_sample": ["docs/exhibition-pc-runbook-2026-05-04.md"],
                    "package_categories": {"operator_docs": 1},
                    "recommended_action": "stage required runbook, checklist, and handoff docs",
                    "stage_policy": "stage-candidate",
                },
                "armor-assets": {
                    "count": 1,
                    "paths_sample": ["viewer/assets/armor-parts/helmet/helmet.glb"],
                    "package_categories": {"armor": 1},
                    "recommended_action": "stage catalog-referenced armor assets",
                    "stage_policy": "stage-candidate",
                },
            },
            "manual_review_groups": {
                "reference-docs": {
                    "count": 1,
                    "paths_sample": ["docs/modeler-handoff-2026-05-01.md"],
                    "package_categories": {"operator_docs": 1},
                    "recommended_action": "stage only promoted docs",
                    "stage_policy": "manual-doc-review",
                }
            },
        },
        "blockers": [{"code": "package-report-untracked-required-files"}],
        "warnings": [{"code": "reference-docs-present"}],
    }


def test_render_markdown_includes_required_review_sections() -> None:
    markdown = tool.render_markdown(_manifest(), _validation())

    for heading in (
        "## release-critical",
        "## stage_summary",
        "## operator-docs",
        "## armor-assets",
        "## qa-evidence",
        "## local-only",
        "## do-not-stage",
        "## final_commands",
    ):
        assert heading in markdown
    assert "`docs/exhibition-pc-runbook-2026-05-04.md`" in markdown
    assert "`viewer/assets/armor-parts/helmet/helmet.glb`" in markdown
    assert "python tools\\export_release_stage_review_markdown.py" in markdown


def test_cli_writes_markdown_and_reports_json(tmp_path: Path, capsys) -> None:
    manifest_path = tmp_path / "qa" / "release-stage-manifest-latest.json"
    validation_path = tmp_path / "qa" / "release-stage-validation-latest.json"
    out_path = tmp_path / "docs" / "release-stage-review-latest.md"
    manifest_path.parent.mkdir()
    validation_path.write_text(json.dumps(_validation()), encoding="utf-8")
    manifest_path.write_text(json.dumps(_manifest()), encoding="utf-8")

    rc = tool.main(
        [
            "--repo-root",
            str(tmp_path),
            "--manifest",
            "qa/release-stage-manifest-latest.json",
            "--validation-report",
            "qa/release-stage-validation-latest.json",
            "--out",
            "docs/release-stage-review-latest.md",
            "--report-json",
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    markdown = out_path.read_text(encoding="utf-8")

    assert rc == 0
    assert payload["contract_version"] == "release-stage-review-markdown.v2"
    assert payload["output_path"] == out_path.resolve().as_posix()
    assert payload["validation_status"] == "fail"
    assert payload["section_counts"]["release-critical"] == 2
    assert payload["recommended_stage_groups"]["release-critical"]["paths_sample"] == [".env.demo.example"]
    assert "## stage_summary" in markdown
    assert "## final_commands" in markdown
    assert "git diff --cached --name-status" in markdown
