from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"
TOOL_PATH = TOOLS_DIR / "export_p1_modeler_order_packet.py"
MANIFEST_PATH = (
    REPO_ROOT
    / "docs"
    / "modeler-deliveries"
    / "p1-limb-three-line-variants-2026-05-03.order-manifest.json"
)


def _load_tool():
    if str(TOOLS_DIR) not in sys.path:
        sys.path.insert(0, str(TOOLS_DIR))
    spec = importlib.util.spec_from_file_location("export_p1_modeler_order_packet", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["export_p1_modeler_order_packet"] = module
    spec.loader.exec_module(module)
    return module


tool = _load_tool()


def test_export_order_packet_from_manifest_contains_required_sections() -> None:
    packet = tool.export_order_packet(MANIFEST_PATH)

    assert packet["contract_version"] == "p1-modeler-order-packet.v1"
    assert set(tool.REQUIRED_TOP_LEVEL_KEYS).issubset(packet)
    assert packet["summary"]["order_item_count"] == 24
    assert packet["summary"]["p1_blocked_asset_count"] == 24
    assert packet["blocked_by_stage"]["delivery"]["count"] == 24
    assert packet["blocked_by_stage"]["catalog_registration"]["count"] == 0
    assert packet["runtime_activation_policy"]["runtime_activation_allowed"] is False
    assert packet["runtime_activation_policy"]["requires_separate_change"] is True

    first = packet["order_items"][0]
    assert first["order_item_id"] == "P1-LIMB-RK-UPPERARM-LEFT"
    assert first["variant_key"] == "left_upperarm:rescue_upperarm_stream"
    assert first["current_stop_stage"] == "delivery"
    assert first["statuses"]["catalog_registration"] == "missing"
    assert first["required_files"]["glb"].endswith(
        "left_upperarm/variants/rescue_upperarm_stream/left_upperarm__rescue_upperarm_stream.glb"
    )
    assert "shoulder" in first["acceptance_focus"]
    assert "front" in packet["acceptance_checks"]["review_packet"]["required_views"]


def test_packet_can_be_built_from_validator_report_json_file(tmp_path: Path) -> None:
    validator_report = tool.order_validator.validate_order_manifest(MANIFEST_PATH)
    report_path = tmp_path / "validator-report.json"
    report_path.write_text(json.dumps(validator_report, ensure_ascii=False), encoding="utf-8")

    packet = tool.export_order_packet(report_path)

    assert packet["source"]["missing_matrix_contract"] == "p1-limb-missing-matrix.v1"
    assert packet["summary"]["order_item_count"] == 24
    assert packet["blocked_by_stage"]["delivery"]["items"][0]["variant_key"].startswith("left_upperarm:")


def test_markdown_and_csv_formatters_are_modeler_readable() -> None:
    packet = tool.export_order_packet(MANIFEST_PATH)

    markdown = tool.format_packet(packet, "markdown")
    csv_payload = tool.format_packet(packet, "csv")

    assert markdown.startswith("# P1 Modeler Order Packet")
    assert "| `delivery` | 24 |" in markdown
    assert "P1-LIMB-RK-UPPERARM-LEFT" in markdown
    assert csv_payload.splitlines()[0].startswith("order_item_id,variant_key,line_id")
    assert "P1-LIMB-RK-UPPERARM-LEFT,left_upperarm:rescue_upperarm_stream" in csv_payload


def test_cli_writes_requested_format_and_can_report_json(tmp_path: Path, capsys) -> None:
    out_path = tmp_path / "p1-order-packet.md"

    rc = tool.main(
        [
            "--manifest",
            str(MANIFEST_PATH),
            "--out",
            str(out_path),
            "--format",
            "markdown",
            "--report-json",
        ]
    )
    captured = capsys.readouterr()
    stdout_payload = json.loads(captured.out)

    assert rc == 0
    assert out_path.read_text(encoding="utf-8").startswith("# P1 Modeler Order Packet")
    assert stdout_payload["contract_version"] == "p1-modeler-order-packet.v1"
    assert stdout_payload["summary"]["order_item_count"] == 24
