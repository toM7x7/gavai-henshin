from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"
TOOL_PATH = TOOLS_DIR / "export_modeler_handoff_summary.py"
P1_MANIFEST = (
    REPO_ROOT
    / "docs"
    / "modeler-deliveries"
    / "p1-limb-three-line-variants-2026-05-03.order-manifest.json"
)
AUDIT_DOC = REPO_ROOT / "docs" / "modeler-triview-30variant-audit-table-2026-05-03.md"
WORKLIST_DOC = REPO_ROOT / "docs" / "modeler-30variant-triview-review-worklist-2026-05-04.md"


def _load_tool():
    if str(TOOLS_DIR) not in sys.path:
        sys.path.insert(0, str(TOOLS_DIR))
    spec = importlib.util.spec_from_file_location("export_modeler_handoff_summary", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["export_modeler_handoff_summary"] = module
    spec.loader.exec_module(module)
    return module


tool = _load_tool()


def test_export_handoff_summary_from_manifest_and_docs() -> None:
    summary = tool.export_handoff_summary(
        p1_manifest=P1_MANIFEST,
        audit_doc=AUDIT_DOC,
        worklist_doc=WORKLIST_DOC,
    )

    assert summary["contract_version"] == "modeler-handoff-summary.v1"
    assert set(tool.REQUIRED_SUMMARY_KEYS).issubset(summary)
    assert summary["source"]["rendering_or_blender_required"] is False
    assert summary["p1_order_status"]["order_item_count"] == 24
    assert summary["p1_order_status"]["blocked_asset_count"] == 24
    assert summary["p1_order_status"]["primary_stop_stage"] == "delivery"
    assert summary["triview_fidelity_status"]["fidelity_hold_count"] == 30
    assert summary["triview_fidelity_status"]["per_part_fix_request_count"] == 10
    assert summary["runtime_release_note"]["public_runtime_allowed"] is False
    assert "既存30variant" in summary["handoff_message_japanese"]


def test_modeler_action_queue_combines_p0_fixes_and_p1_order() -> None:
    summary = tool.export_handoff_summary(
        p1_manifest=P1_MANIFEST,
        audit_doc=AUDIT_DOC,
        worklist_doc=WORKLIST_DOC,
    )
    queue = summary["modeler_action_queue"]

    assert any(item["source"] == "p1_limb_order" and item["item_count"] == 24 for item in queue)
    assert any(item["source"] == "triview_fidelity_fix" and item["scope"] == "helmet" for item in queue)
    assert queue[0]["priority"] == "P0"
    p1_order = next(item for item in queue if item["source"] == "p1_limb_order")
    assert "upperarm/forearm/hand/thigh" in p1_order["scope"]
    assert p1_order["runtime_visibility"] == "not_public_until_separate_runtime_activation"
    assert len(p1_order["variant_keys"]) == 24


def test_can_load_saved_p1_packet_and_saved_fix_request(tmp_path: Path) -> None:
    p1_packet = tool.p1_order_exporter.export_order_packet(P1_MANIFEST)
    fix_request = tool.fix_request_exporter.export_fix_request(
        audit_doc=AUDIT_DOC,
        worklist_doc=WORKLIST_DOC,
    )
    p1_path = tmp_path / "p1-order-packet.json"
    fix_path = tmp_path / "modeler-fix-request.json"
    p1_path.write_text(json.dumps(p1_packet, ensure_ascii=False), encoding="utf-8")
    fix_path.write_text(json.dumps(fix_request, ensure_ascii=False), encoding="utf-8")

    summary = tool.export_handoff_summary(p1_packet_path=p1_path, fix_request_path=fix_path)

    assert summary["p1_order_status"]["order_item_count"] == 24
    assert summary["triview_fidelity_status"]["fidelity_hold_count"] == 30
    assert summary["acceptance_gate"][1]["gate"] == "p1_limb_order_delivery"


def test_can_load_saved_triview_packet_without_fix_request(tmp_path: Path) -> None:
    triview_packet = tool.fix_request_exporter.triview_packet.export_triview_audit_packet(
        audit_doc=AUDIT_DOC,
        worklist_doc=WORKLIST_DOC,
    )
    path = tmp_path / "triview-audit-packet.json"
    path.write_text(json.dumps(triview_packet, ensure_ascii=False), encoding="utf-8")

    summary = tool.export_handoff_summary(p1_manifest=P1_MANIFEST, triview_packet_path=path)

    assert summary["triview_fidelity_status"]["fidelity_hold_count"] == 30
    assert summary["modeler_action_queue"][0]["source"] == "triview_fidelity_fix"


def test_markdown_contains_required_handoff_sections() -> None:
    summary = tool.export_handoff_summary(
        p1_manifest=P1_MANIFEST,
        audit_doc=AUDIT_DOC,
        worklist_doc=WORKLIST_DOC,
    )

    markdown = tool.format_markdown(summary)

    assert markdown.startswith("# Modeler Handoff Summary")
    assert "## P1 Order Status" in markdown
    assert "## Triview Fidelity Status" in markdown
    assert "## Modeler Action Queue" in markdown
    assert "## Acceptance Gate" in markdown
    assert "## Runtime Release Note" in markdown
    assert "blocked_by_p1_order_and_triview_fidelity_hold" in markdown


def test_cli_writes_markdown_and_reports_json(tmp_path: Path, capsys) -> None:
    out_path = tmp_path / "docs" / "modeler-handoff-summary-latest.md"

    rc = tool.main(
        [
            "--p1-manifest",
            str(P1_MANIFEST),
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
    assert markdown.startswith("# Modeler Handoff Summary")
    assert stdout_summary["contract_version"] == "modeler-handoff-summary.v1"
    assert stdout_summary["p1_order_status"]["order_item_count"] == 24
    assert stdout_summary["triview_fidelity_status"]["fidelity_hold_count"] == 30
