from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "list_release_stage_candidates.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("list_release_stage_candidates", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["list_release_stage_candidates"] = module
    spec.loader.exec_module(module)
    return module


tool = _load_tool()


def _porcelain(*records: str) -> bytes:
    return ("\0".join(records) + "\0").encode("utf-8")


def test_parse_porcelain_z_handles_statuses_and_renames() -> None:
    entries = tool.parse_porcelain_z(
        _porcelain(
            " M .gitignore",
            "?? src/henshin/variant_selection.py",
            "!! .playwright-cli/page.png",
            "R  docs/new.md",
            "docs/old.md",
        )
    )

    assert [entry.status for entry in entries] == [" M", "??", "!!", "R "]
    assert entries[1].path == "src/henshin/variant_selection.py"
    assert entries[2].path == ".playwright-cli/page.png"
    assert entries[3].path == "docs/new.md"
    assert entries[3].old_path == "docs/old.md"


def test_classifies_release_buckets_with_generated_artifacts_taking_precedence() -> None:
    entries = tool.parse_porcelain_z(
        _porcelain(
            " M .gitignore",
            "?? .env.demo.example",
            "?? docs/exhibition-pc-runbook-2026-05-04.md",
            "!! .env",
            "!! node_modules/.package-lock.json",
            "!! .pytest_cache/v/cache/nodeids",
            " D sessions/.gitkeep",
            "?? .tmp-quest.err",
            "?? docs/archive/evidence-2026-05/root-runtime/.tmp-quest.out",
            " D .playwright-cli/page-2026-03-07T08-06-15-778Z.png",
            "?? viewer/assets/armor-parts/variant_catalog.json",
            "?? src/henshin/variant_selection.py",
            "?? schemas/replay-record.v0.2.schema.json",
            " M tests/.tmp/quest-api-live.err.log",
            "!! .playwright-cli/page.png",
            "?? qa/exhibition_release_package_latest.json",
            "?? qa/shareable-qa-evidence-latest.json",
            "?? qa/mocopi-evidence-package-latest.json",
            "?? qa/replay/replay-qa-3601.summary.json",
            "?? qa/replay/3601.replay-record.json",
            "?? qa/exhibition-pc-transfer-checklist-latest.md",
            "?? qa/runtime-package-3601.snapshot.json",
            "?? docs/modeler-handoff-2026-05-01.md",
            "?? docs/assets/hero-suit-surface-fit-concept.svg",
            "?? examples/1f7b1732-5e7e-45f6-bc9c-7f7f3bebfd3a.jpg",
            " D examples/レコーディング 2026-03-07 214750.mp4",
            " D examples/このサイトとは _ VTuber Museum Map.pdf",
            "?? examples/henshin_docs_bundle_v0_1/00_README.md",
            "?? blender/review_master.blend",
            "?? docs/hero-suit-reference-analysis-2026-04-30.md",
            "?? PROJECT_STRUCTURE.md",
        )
    )
    by_path = {item.path: item for item in tool.classify_entries(entries)}

    assert by_path[".gitignore"].category == "release-critical"
    assert by_path[".env.demo.example"].category == "release-critical"
    assert by_path["docs/exhibition-pc-runbook-2026-05-04.md"].category == "operator-docs"
    assert by_path[".env"].category == "local-only-root"
    assert by_path["node_modules/.package-lock.json"].category == "local-only-root"
    assert by_path[".pytest_cache/v/cache/nodeids"].category == "local-only-root"
    assert by_path["sessions/.gitkeep"].category == "local-only-root"
    assert by_path[".tmp-quest.err"].category == "generated-artifact"
    assert by_path["docs/archive/evidence-2026-05/root-runtime/.tmp-quest.out"].category == "generated-artifact"
    assert by_path[".playwright-cli/page-2026-03-07T08-06-15-778Z.png"].category == "deleted-tracked-artifact"
    assert by_path[".playwright-cli/page-2026-03-07T08-06-15-778Z.png"].tracked is True
    assert by_path["viewer/assets/armor-parts/variant_catalog.json"].category == "armor-assets"
    assert by_path["src/henshin/variant_selection.py"].category == "release-critical"
    assert by_path["schemas/replay-record.v0.2.schema.json"].category == "release-critical"
    assert by_path["tests/.tmp/quest-api-live.err.log"].category == "generated-artifact"
    assert by_path["tests/.tmp/quest-api-live.err.log"].tracked is True
    assert by_path[".playwright-cli/page.png"].category == "generated-artifact"
    assert by_path[".playwright-cli/page.png"].ignored is True
    assert by_path["qa/exhibition_release_package_latest.json"].category == "local-qa-artifact"
    assert by_path["qa/shareable-qa-evidence-latest.json"].category == "qa-evidence"
    assert by_path["qa/mocopi-evidence-package-latest.json"].category == "qa-evidence"
    assert by_path["qa/replay/replay-qa-3601.summary.json"].category == "local-qa-artifact"
    assert by_path["qa/replay/3601.replay-record.json"].category == "local-qa-artifact"
    assert by_path["qa/exhibition-pc-transfer-checklist-latest.md"].category == "local-qa-artifact"
    assert by_path["qa/runtime-package-3601.snapshot.json"].category == "local-qa-artifact"
    assert by_path["docs/modeler-handoff-2026-05-01.md"].category == "reference-docs"
    assert by_path["docs/assets/hero-suit-surface-fit-concept.svg"].category == "reference-artifact"
    assert by_path["examples/1f7b1732-5e7e-45f6-bc9c-7f7f3bebfd3a.jpg"].category == "user-feedback-media"
    assert by_path["examples/レコーディング 2026-03-07 214750.mp4"].category == "user-feedback-media"
    assert by_path["examples/このサイトとは _ VTuber Museum Map.pdf"].category == "user-feedback-media"
    assert by_path["examples/henshin_docs_bundle_v0_1/00_README.md"].category == "reference-artifact"
    assert by_path["blender/review_master.blend"].category == "local-workspace"
    assert by_path["docs/hero-suit-reference-analysis-2026-04-30.md"].category == "reference-docs"
    assert by_path["PROJECT_STRUCTURE.md"].category == "release-critical"


def test_json_report_groups_counts_and_is_read_only(monkeypatch, tmp_path: Path, capsys) -> None:
    def fake_read_git_status(repo_root: Path, *, include_ignored: bool) -> bytes:
        assert repo_root == tmp_path.resolve()
        assert include_ignored is True
        return _porcelain(
            " M .gitignore",
            "?? docs/exhibition-pc-runbook-2026-05-04.md",
            "?? viewer/assets/armor-parts/variant_catalog.json",
            "!! tests/.tmp/smoke.png",
        )

    monkeypatch.setattr(tool, "_read_git_status", fake_read_git_status)

    rc = tool.main(["--repo-root", str(tmp_path), "--json"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert rc == 0
    assert payload["contract_version"] == "release-stage-candidates.v7"
    assert payload["read_only"] is True
    assert "--untracked-files=all" in payload["git_status"]["command"]
    assert payload["counts"]["by_category"]["release-critical"] == 1
    assert payload["counts"]["by_category"]["operator-docs"] == 1
    assert payload["counts"]["by_category"]["armor-assets"] == 1
    assert payload["counts"]["by_category"]["qa-evidence"] == 0
    assert payload["counts"]["by_category"]["local-qa-artifact"] == 0
    assert payload["counts"]["by_category"]["reference-docs"] == 0
    assert payload["counts"]["by_category"]["reference-artifact"] == 0
    assert payload["counts"]["by_category"]["user-feedback-media"] == 0
    assert payload["counts"]["by_category"]["local-workspace"] == 0
    assert payload["counts"]["by_category"]["local-only-root"] == 0
    assert payload["counts"]["by_category"]["deleted-tracked-artifact"] == 0
    assert payload["counts"]["by_category"]["generated-artifact"] == 1
    assert payload["categories"]["generated-artifact"][0]["recommended_action"] == "do-not-stage"
    assert payload["notes"][0].startswith("This tool is read-only")


def test_summary_json_suppresses_large_ignored_lists(monkeypatch, tmp_path: Path, capsys) -> None:
    def fake_read_git_status(repo_root: Path, *, include_ignored: bool) -> bytes:
        assert repo_root == tmp_path.resolve()
        assert include_ignored is True
        return _porcelain(
            "!! .playwright-cli/one.png",
            "!! .playwright-cli/two.png",
            "!! .playwright-cli/three.png",
            "!! node_modules/.package-lock.json",
            "?? qa/shareable-qa-evidence-latest.json",
            "?? qa/runtime-package-3601.snapshot.json",
        )

    monkeypatch.setattr(tool, "_read_git_status", fake_read_git_status)

    rc = tool.main(["--repo-root", str(tmp_path), "--summary-json", "--sample-limit", "1"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert rc == 0
    assert payload["summary"] is True
    assert "items" not in payload
    assert "categories" not in payload
    assert payload["counts"]["by_category"]["generated-artifact"] == 3
    assert payload["counts"]["by_category"]["local-only-root"] == 1
    assert payload["counts"]["by_category"]["qa-evidence"] == 1
    assert payload["counts"]["by_category"]["local-qa-artifact"] == 1
    assert payload["counts"]["by_category"]["reference-docs"] == 0
    assert len(payload["samples"]["generated-artifact"]) == 1
    assert payload["suppressed"]["generated-artifact"] == 2
    assert payload["samples"]["local-only-root"][0]["path"] == "node_modules/.package-lock.json"
    assert payload["samples"]["qa-evidence"][0]["path"] == "qa/shareable-qa-evidence-latest.json"
    assert payload["samples"]["local-qa-artifact"][0]["path"] == "qa/runtime-package-3601.snapshot.json"
