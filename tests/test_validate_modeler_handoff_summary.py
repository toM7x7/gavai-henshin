from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "tools"
TOOL_PATH = TOOLS_DIR / "validate_modeler_handoff_summary.py"


def _load_tool():
    if str(TOOLS_DIR) not in sys.path:
        sys.path.insert(0, str(TOOLS_DIR))
    spec = importlib.util.spec_from_file_location("validate_modeler_handoff_summary", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["validate_modeler_handoff_summary"] = module
    spec.loader.exec_module(module)
    return module


tool = _load_tool()


def _summary() -> dict:
    return tool.handoff_exporter.export_handoff_summary()


def test_direct_generated_handoff_summary_passes_strict_validation() -> None:
    result = tool.validate_modeler_handoff_summary(strict=True)

    assert result["ok"], result["reasons"]
    assert result["status"] == "pass"
    assert result["source"]["generated_from_sources"] is True
    assert {check["check"] for check in result["checks"]} >= {
        "p1_shortage_24_explicit",
        "fidelity_hold_explicit",
        "runtime_model_delivery_distinction",
        "acceptance_gate_complete",
        "japanese_handoff_message_present",
    }


def test_json_handoff_file_passes_validation(tmp_path: Path) -> None:
    path = tmp_path / "modeler-handoff-summary.json"
    path.write_text(json.dumps(_summary(), ensure_ascii=False), encoding="utf-8")

    result = tool.validate_modeler_handoff_summary(path, strict=True)

    assert result["ok"], result["reasons"]
    assert result["source"]["kind"] == "json"
    assert result["source"]["path"].endswith("modeler-handoff-summary.json")


def test_markdown_handoff_file_passes_validation(tmp_path: Path) -> None:
    summary = _summary()
    path = tmp_path / "modeler-handoff-summary.md"
    path.write_text(tool.handoff_exporter.format_markdown(summary), encoding="utf-8")

    result = tool.validate_modeler_handoff_summary(path, strict=True)

    assert result["ok"], result["reasons"]
    assert result["source"]["kind"] == "markdown"


def test_missing_p1_24_count_fails() -> None:
    summary = copy.deepcopy(_summary())
    summary["p1_order_status"]["blocked_asset_count"] = 23

    result = tool.validate_modeler_handoff_summary(summary, strict=True)

    assert not result["ok"]
    assert any("24 order items and 24 blocked assets" in reason for reason in result["reasons"])


def test_runtime_model_delivery_distinction_is_required() -> None:
    summary = copy.deepcopy(_summary())
    summary["runtime_release_note"]["canonical_base_runtime_release_can_proceed"] = False
    summary["runtime_release_note"]["model_delivery_blocked"] = False

    result = tool.validate_modeler_handoff_summary(summary, strict=True)

    assert not result["ok"]
    assert any("runtime note must distinguish" in reason for reason in result["reasons"])


def test_markdown_without_japanese_message_fails(tmp_path: Path) -> None:
    summary = _summary()
    markdown = tool.handoff_exporter.format_markdown(summary).replace(
        summary["handoff_message_japanese"],
        "Modeler handoff message removed.",
    )
    path = tmp_path / "modeler-handoff-summary.md"
    path.write_text(markdown, encoding="utf-8")

    result = tool.validate_modeler_handoff_summary(path, strict=True)

    assert not result["ok"]
    assert any("Japanese handoff message" in reason for reason in result["reasons"])


def test_cli_reports_json_for_direct_generated_summary(capsys) -> None:
    rc = tool.main(["--strict", "--report-json"])
    captured = capsys.readouterr()
    result = json.loads(captured.out)

    assert rc == 0
    assert result["contract_version"] == "modeler-handoff-summary-validation.v1"
    assert result["ok"] is True
    assert result["status"] == "pass"
