from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "audit_project_structure_cleanup.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("audit_project_structure_cleanup", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["audit_project_structure_cleanup"] = module
    spec.loader.exec_module(module)
    return module


tool = _load_tool()


def _write(path: Path, text: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_required_root_files(root: Path, *, omit: set[str] | None = None) -> None:
    omitted = omit or set()
    for name in tool.REQUIRED_ROOT_FILES:
        if name not in omitted:
            _write(root / name, f"{name}\n")


def test_build_audit_detects_required_files_and_top_level_cleanup_candidates(tmp_path: Path) -> None:
    _write_required_root_files(tmp_path, omit={"package-lock.json"})
    for dirname in ("src", "tests", "tools", "viewer", "docs", "examples", "qa", "node_modules", "output", ".pytest_cache", "blender"):
        (tmp_path / dirname).mkdir()
    _write(tmp_path / ".env", "SECRET=value\n")
    _write(tmp_path / "sessions" / ".gitkeep")
    _write(tmp_path / ".tmp-quest.err", "local error\n")
    _write(tmp_path / "armor-forge-japanese-ui-1273.png", "not really png\n")
    _write(tmp_path / "scratchpad.md", "manual review\n")

    payload = tool.build_audit(tmp_path, sample_limit=20, full=True)
    root_by_path = {item["path"]: item for item in payload["root_items"]}

    assert payload["contract_version"] == "project-structure-cleanup-audit.v2"
    assert payload["read_only"] is True
    assert payload["ok"] is False
    assert payload["counts"]["missing_required"] == 1
    assert payload["missing_required"][0]["path"] == "package-lock.json"
    assert root_by_path[".env"]["rule_id"] == "root-local-env"
    assert root_by_path[".env"]["category"] == "top-level-local-only-file"
    assert root_by_path[".tmp-quest.err"]["rule_id"] == "root-temp-log"
    assert root_by_path["armor-forge-japanese-ui-1273.png"]["rule_id"] == "root-temp-log"
    assert root_by_path["node_modules"]["rule_id"] == "dependency-cache-dir"
    assert root_by_path["output"]["rule_id"] == "generated-runtime-output-dir"
    assert root_by_path["blender"]["rule_id"] == "local-workspace-dir"
    assert root_by_path["scratchpad.md"]["category"] == "unknown-root-file"
    assert payload["counts"]["local_only_roots"] == 4
    assert {item["path"] for item in payload["local_only_roots"]} == {
        ".env",
        ".pytest_cache",
        "node_modules",
        "sessions/.gitkeep",
    }


def test_build_audit_reports_exhibition_archive_candidates_without_blocking_ok(tmp_path: Path) -> None:
    _write_required_root_files(tmp_path)
    _write(tmp_path / "docs" / "exhibition-pc-runbook-2026-05-04.md")
    _write(tmp_path / "docs" / "quest-usb-adb-reverse-checklist-2026-05-04.md")
    _write(tmp_path / "docs" / "modeler-handoff-2026-05-01.md")
    _write(tmp_path / "docs" / "assets" / "flow.png")
    _write(tmp_path / "qa" / "replay" / "3601.replay-record.json", "{}\n")
    _write(tmp_path / "examples" / "henshin_docs_bundle_v0_1.zip", "zip\n")
    _write(tmp_path / "examples" / "henshin_docs_bundle_v0_1" / "00_README.md")

    payload = tool.build_audit(tmp_path, sample_limit=10, full=True)
    by_path = {item["path"]: item for item in payload["archive_candidates"]}

    assert payload["ok"] is True
    assert payload["counts"]["blocked_top_level"] == 0
    assert payload["counts"]["archive_candidates"] == 7
    assert by_path["docs/exhibition-pc-runbook-2026-05-04.md"]["rule_id"] == "exhibition-doc"
    assert by_path["docs/quest-usb-adb-reverse-checklist-2026-05-04.md"]["rule_id"] == "quest-doc"
    assert by_path["docs/modeler-handoff-2026-05-01.md"]["rule_id"] == "modeler-handoff-doc"
    assert by_path["docs/assets/flow.png"]["rule_id"] == "reference-visual-artifact"
    assert by_path["qa/replay/3601.replay-record.json"]["rule_id"] == "qa-evidence-artifact"
    assert by_path["examples/henshin_docs_bundle_v0_1.zip"]["rule_id"] == "reference-doc-bundle"
    assert by_path["examples/henshin_docs_bundle_v0_1/00_README.md"]["rule_id"] == "reference-doc-bundle"


def test_cli_full_json_can_fail_on_cleanup_findings(tmp_path: Path, capsys) -> None:
    _write_required_root_files(tmp_path)
    _write(tmp_path / ".tmp-dashboard.out", "local output\n")

    rc = tool.main(["--repo-root", str(tmp_path), "--full-json", "--fail-on-findings"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert rc == 1
    assert payload["ok"] is False
    assert payload["counts"]["blocked_top_level"] == 1
    assert payload["root_items"][0]["path"] == ".env.example"
