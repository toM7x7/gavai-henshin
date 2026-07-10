from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"
TOOL_PATH = TOOLS_DIR / "export_modeler_delivery_package_index.py"
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
    spec = importlib.util.spec_from_file_location("export_modeler_delivery_package_index", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["export_modeler_delivery_package_index"] = module
    spec.loader.exec_module(module)
    return module


tool = _load_tool()


def test_export_delivery_package_index_has_required_sections() -> None:
    index = tool.export_delivery_package_index(
        p1_manifest=P1_MANIFEST,
        audit_doc=AUDIT_DOC,
        worklist_doc=WORKLIST_DOC,
    )

    assert index["contract_version"] == "modeler-delivery-package-index.v1"
    assert set(tool.REQUIRED_INDEX_KEYS).issubset(index)
    assert index["source"]["rendering_or_blender_required"] is False
    assert index["source"]["glb_geometry_inspection_required"] is False
    assert index["current_state_snapshot"]["p1_blocked_asset_count"] == 24
    assert index["current_state_snapshot"]["triview_fidelity_hold_count"] == 30
    assert len(index["documents_to_share"]) >= 6
    assert index["pre_github_reading_order"][0]["path"] == "docs/modeler-delivery-package-index-latest.md"
    assert {item["artifact"] for item in index["generated_packets"]} >= {
        "p1_order_packet",
        "triview_audit_packet",
        "modeler_fix_request",
        "modeler_handoff_summary",
        "modeler_delivery_package_index",
    }


def test_index_summarizes_current_blocked_model_delivery_state() -> None:
    index = tool.export_delivery_package_index(
        p1_manifest=P1_MANIFEST,
        audit_doc=AUDIT_DOC,
        worklist_doc=WORKLIST_DOC,
    )
    blocked = index["blocked_items"]
    runtime = index["runtime_release_note"]

    assert blocked["p1_order"]["blocked_asset_count"] == 24
    assert blocked["p1_order"]["order_item_count"] == 24
    assert blocked["p1_order"]["current_stop_stage_counts"]["delivery"] == 24
    assert blocked["p1_order"]["acceptance_label"] == "warn_now_block_p1"
    assert blocked["triview_fidelity"]["fidelity_hold_count"] == 30
    assert blocked["triview_fidelity"]["per_part_fix_request_count"] == 10
    assert runtime["canonical_base_runtime_release_can_proceed"] is True
    assert runtime["model_delivery_blocked"] is True
    assert runtime["public_runtime_allowed"] is False


def test_index_lists_handoff_validator_and_local_artifacts_not_to_share() -> None:
    index = tool.export_delivery_package_index(
        p1_manifest=P1_MANIFEST,
        audit_doc=AUDIT_DOC,
        worklist_doc=WORKLIST_DOC,
    )

    assert any("validate_modeler_handoff_summary.py" in item["command"] for item in index["validators_to_run"])
    assert any("validate_modeler_variant_order_manifest.py" in item["command"] for item in index["validators_to_run"])
    assert any(item["gate"] == "generate_package_index" for item in index["github_submission_preflight"])
    assert any(
        item["gate"] == "p1_strict_delivery_acceptance" and item["pass_before_github"] is False
        for item in index["github_submission_preflight"]
    )
    assert any(".claude/worktrees" in item["path"] for item in index["do_not_share_local_artifacts"])
    assert any("tests/.tmp" in item["path"] for item in index["do_not_share_local_artifacts"])
    assert all("blender" not in item["command"].lower() for item in index["generated_packets"])


def test_markdown_contains_package_index_sections() -> None:
    index = tool.export_delivery_package_index(
        p1_manifest=P1_MANIFEST,
        audit_doc=AUDIT_DOC,
        worklist_doc=WORKLIST_DOC,
    )

    markdown = tool.format_index(index, "markdown")

    assert markdown.startswith("# Modeler Delivery Package Index")
    assert "## Pre-GitHub Reading Order" in markdown
    assert "## Documents To Share" in markdown
    assert "## Generated Packets" in markdown
    assert "## Validators To Run" in markdown
    assert "## GitHub Submission Preflight" in markdown
    assert "## Blocked Items" in markdown
    assert "## Runtime Release Note" in markdown
    assert "## Do Not Share Local Artifacts" in markdown
    assert "modeler-delivery-package-index-latest.md" in markdown
    assert "validate_modeler_handoff_summary.py" in markdown
    assert "p1_strict_delivery_acceptance" in markdown


def test_cli_writes_markdown_and_reports_json(tmp_path: Path, capsys) -> None:
    out_path = tmp_path / "docs" / "modeler-delivery-package-index-latest.md"

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
    stdout_index = json.loads(captured.out)
    markdown = out_path.read_text(encoding="utf-8")

    assert rc == 0
    assert markdown.startswith("# Modeler Delivery Package Index")
    assert stdout_index["contract_version"] == "modeler-delivery-package-index.v1"
    assert stdout_index["blocked_items"]["p1_order"]["blocked_asset_count"] == 24
    assert stdout_index["blocked_items"]["triview_fidelity"]["fidelity_hold_count"] == 30
    assert stdout_index["github_submission_preflight"][0]["gate"] == "generate_package_index"
