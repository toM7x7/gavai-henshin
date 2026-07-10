from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"
TOOL_PATH = TOOLS_DIR / "export_modeler_fix_request.py"
AUDIT_DOC = REPO_ROOT / "docs" / "modeler-triview-30variant-audit-table-2026-05-03.md"
WORKLIST_DOC = REPO_ROOT / "docs" / "modeler-30variant-triview-review-worklist-2026-05-04.md"


def _load_tool():
    if str(TOOLS_DIR) not in sys.path:
        sys.path.insert(0, str(TOOLS_DIR))
    spec = importlib.util.spec_from_file_location("export_modeler_fix_request", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["export_modeler_fix_request"] = module
    spec.loader.exec_module(module)
    return module


tool = _load_tool()


def test_export_fix_request_from_docs_has_required_sections() -> None:
    summary = tool.export_fix_request(audit_doc=AUDIT_DOC, worklist_doc=WORKLIST_DOC)

    assert summary["contract_version"] == "modeler-fix-request.v1"
    assert set(tool.REQUIRED_SUMMARY_KEYS).issubset(summary)
    assert summary["source"]["rendering_or_blender_required"] is False
    assert len(summary["fidelity_hold_items"]) == 30
    assert summary["review_status"]["missing_p1_count"] == 24
    assert len(summary["per_part_fix_requests"]) == 10
    assert summary["runtime_release_impact"]["public_runtime_allowed"] is False
    assert any(
        blocker["code"] == "sidecar-provenance-incomplete"
        for blocker in summary["modeler_delivery_blockers"]
    )


def test_per_part_fix_request_groups_variants_and_actions() -> None:
    summary = tool.export_fix_request(audit_doc=AUDIT_DOC, worklist_doc=WORKLIST_DOC)
    helmet = next(item for item in summary["per_part_fix_requests"] if item["part"] == "helmet")

    assert helmet["priority"] == "P0"
    assert helmet["variant_count"] == 3
    assert "helmet:rescue_sleek" in helmet["variant_keys"]
    rescue = next(item for item in helmet["line_requests"] if item["line_id"] == "line_rescue_knight")
    assert rescue["variant_key"] == "helmet:rescue_sleek"
    assert "blue visor" in rescue["requested_fix"]
    assert "source_overlay_front" in rescue["required_evidence"]
    assert "source_concept_ids" in rescue["sidecar_fields_required"]
    assert helmet["acceptance"]["public_runtime_allowed"] is False


def test_markdown_contains_modeler_request_and_recheck_table() -> None:
    summary = tool.export_fix_request(audit_doc=AUDIT_DOC, worklist_doc=WORKLIST_DOC)

    markdown = tool.format_markdown(summary)

    assert markdown.startswith("# Modeler 30variant Fix Request")
    assert "## Modeler Delivery Blockers" in markdown
    assert "## Per-Part Fix Requests" in markdown
    assert "### helmet" in markdown
    assert "`helmet:rescue_sleek`" in markdown
    assert "## Acceptance Recheck Steps" in markdown
    assert "runtime_release_blocked_by_fidelity_hold" in markdown


def test_can_load_saved_triview_audit_packet_json(tmp_path: Path) -> None:
    packet = tool.triview_packet.export_triview_audit_packet(
        audit_doc=AUDIT_DOC,
        worklist_doc=WORKLIST_DOC,
    )
    packet_path = tmp_path / "modeler-triview-audit-latest.json"
    packet_path.write_text(json.dumps(packet, ensure_ascii=False), encoding="utf-8")

    summary = tool.export_fix_request(packet_path=packet_path)

    assert summary["review_status"]["file_pass_but_fidelity_hold_count"] == 30
    assert summary["per_part_fix_requests"][0]["part"] == "helmet"


def test_cli_writes_markdown_and_reports_json(tmp_path: Path, capsys) -> None:
    out_path = tmp_path / "docs" / "modeler-fix-request-latest.md"

    rc = tool.main(
        [
            "--audit-doc",
            str(AUDIT_DOC),
            "--worklist-doc",
            str(WORKLIST_DOC),
            "--out",
            str(out_path),
            "--report-json",
        ]
    )
    captured = capsys.readouterr()
    stdout_summary = json.loads(captured.out)
    markdown = out_path.read_text(encoding="utf-8")

    assert rc == 0
    assert markdown.startswith("# Modeler 30variant Fix Request")
    assert stdout_summary["contract_version"] == "modeler-fix-request.v1"
    assert stdout_summary["review_status"]["file_pass_but_fidelity_hold_count"] == 30
    assert stdout_summary["modeler_message"]["blocker_count"] == 4
