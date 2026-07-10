from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"
TOOL_PATH = TOOLS_DIR / "export_modeler_triview_audit_packet.py"
AUDIT_DOC = REPO_ROOT / "docs" / "modeler-triview-30variant-audit-table-2026-05-03.md"
WORKLIST_DOC = REPO_ROOT / "docs" / "modeler-30variant-triview-review-worklist-2026-05-04.md"


def _load_tool():
    if str(TOOLS_DIR) not in sys.path:
        sys.path.insert(0, str(TOOLS_DIR))
    spec = importlib.util.spec_from_file_location("export_modeler_triview_audit_packet", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["export_modeler_triview_audit_packet"] = module
    spec.loader.exec_module(module)
    return module


tool = _load_tool()


def test_export_packet_parses_30_hold_and_24_missing_p1_items() -> None:
    packet = tool.export_triview_audit_packet(audit_doc=AUDIT_DOC, worklist_doc=WORKLIST_DOC)

    assert packet["contract_version"] == "modeler-triview-audit-packet.v1"
    assert set(tool.REQUIRED_PACKET_KEYS).issubset(packet)
    assert packet["source"]["rendering_or_blender_required"] is False
    assert packet["review_status"]["decision"] == "technical_file_pass_fidelity_hold"
    assert packet["review_status"]["file_pass_but_fidelity_hold_count"] == 30
    assert packet["review_status"]["missing_p1_count"] == 24
    assert len(packet["fidelity_hold_items"]) == 30
    assert len(packet["per_part_findings"]) == 54
    assert packet["runtime_release_impact"]["public_runtime_allowed"] is False
    assert packet["runtime_release_impact"]["held_variant_count"] == 30


def test_hold_item_contains_modeler_fix_fields_and_priority() -> None:
    packet = tool.export_triview_audit_packet(audit_doc=AUDIT_DOC, worklist_doc=WORKLIST_DOC)
    helmet_rescue = next(
        item for item in packet["fidelity_hold_items"] if item["variant_key"] == "helmet:rescue_sleek"
    )

    assert helmet_rescue["part"] == "helmet"
    assert helmet_rescue["priority"] == "P0"
    assert helmet_rescue["line_id"] == "line_rescue_knight"
    assert helmet_rescue["file_gate"] == "file_pass"
    assert helmet_rescue["acceptance_label"] == "fidelity_hold"
    assert helmet_rescue["runtime_release_allowed"] is False
    assert "source_concept_ids" in helmet_rescue["sidecar_fields_required"]
    assert "helmet_closeup_front" in helmet_rescue["required_evidence"]
    assert "blue visor" in helmet_rescue["modeler_action"]


def test_missing_p1_rows_are_kept_out_of_fidelity_hold_items() -> None:
    packet = tool.export_triview_audit_packet(audit_doc=AUDIT_DOC, worklist_doc=WORKLIST_DOC)
    missing = [
        item for item in packet["per_part_findings"] if item["finding_type"] == "missing_p1"
    ]

    assert len(missing) == 24
    assert all(item["variant_key"] is None for item in missing)
    assert all(item["runtime_visibility"] == "not_available_until_p1_delivery" for item in missing)
    assert all(item["acceptance_label"] == "missing_p1_order_gap" for item in missing)
    assert {item["part"] for item in missing} == {
        "left_upperarm",
        "right_upperarm",
        "left_forearm",
        "right_forearm",
        "left_hand",
        "right_hand",
        "left_thigh",
        "right_thigh",
    }


def test_modeler_message_outline_and_recheck_steps_are_actionable() -> None:
    packet = tool.export_triview_audit_packet(audit_doc=AUDIT_DOC, worklist_doc=WORKLIST_DOC)

    outline = packet["modeler_fix_message_outline"]
    assert "30 delivered variants" in outline["opening"]
    assert len(outline["line_focus"]) == 3
    assert any("source_overlay_front.png" in item for item in outline["must_fix"])
    assert any("Add required review imagery" in item for item in outline["send_back_to_modeler"])
    assert packet["acceptance_recheck_steps"][0]["gate"] == "delivery_manifest"
    assert packet["acceptance_recheck_steps"][-1]["gate"] == "runtime_route_proof"


def test_cli_writes_out_and_reports_json(tmp_path: Path, capsys) -> None:
    out_path = tmp_path / "qa" / "modeler-triview-audit-latest.json"

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
    stdout_payload = json.loads(captured.out)
    file_payload = json.loads(out_path.read_text(encoding="utf-8"))

    assert rc == 0
    assert stdout_payload == file_payload
    assert file_payload["review_status"]["file_pass_but_fidelity_hold_count"] == 30
    assert file_payload["runtime_release_impact"]["runtime_block_label"] == (
        "runtime_release_blocked_by_fidelity_hold"
    )
