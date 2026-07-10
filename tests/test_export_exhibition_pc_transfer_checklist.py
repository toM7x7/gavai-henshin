from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = REPO_ROOT / "tools" / "export_exhibition_pc_transfer_checklist.py"


def _load_tool():
    spec = importlib.util.spec_from_file_location("export_exhibition_pc_transfer_checklist", TOOL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["export_exhibition_pc_transfer_checklist"] = module
    spec.loader.exec_module(module)
    return module


tool = _load_tool()


def _write(path: Path, content: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _create_transfer_fixture(root: Path, *, include_replay: bool = True) -> None:
    required_paths = [
        "README.md",
        ".env.demo.example",
        "tools/start_exhibition_local_stack.ps1",
        "tools/start_quest_adb_reverse.ps1",
        "tools/validate_service_deployment_contract.py",
        "tools/validate_exhibition_release_package.py",
        "docs/exhibition-pc-runbook-2026-05-04.md",
        "qa/exhibition_release_package_latest.json",
    ]
    for rel_path in required_paths:
        _write(root / rel_path)
    if include_replay:
        _write(root / "qa" / "replay" / "3601.replay-record.json", "{}")
        _write(root / "qa" / "replay" / "3601.summary.json", "{}")


def test_transfer_checklist_reports_ready_items_urls_and_manual_steps(tmp_path: Path) -> None:
    _create_transfer_fixture(tmp_path)

    result = tool.build_transfer_checklist(tmp_path)

    assert result["ok"] is True
    assert result["contract_version"] == "exhibition-pc-transfer-checklist.v1"
    assert result["missing_items"] == []
    assert {item["key"] for item in result["ready_items"]} == {item.key for item in tool.REQUIRED_ITEMS}
    assert result["urls"]["web_forge"] == "http://127.0.0.1:8010/viewer/armor-forge/"
    assert result["urls"]["quest_usb_template"].endswith("?newRoute=1&code=<CODE>")
    assert any("start_quest_adb_reverse.ps1" in step for step in result["usb_quest_steps"])
    assert any(".env files containing real provider secrets" in item for item in result["do_not_copy_items"])


def test_transfer_checklist_reports_missing_env_and_replay_qa_artifact(tmp_path: Path) -> None:
    _create_transfer_fixture(tmp_path, include_replay=False)
    (tmp_path / ".env.demo.example").unlink()

    result = tool.build_transfer_checklist(tmp_path)
    missing_by_key = {item["key"]: item for item in result["missing_items"]}

    assert result["ok"] is False
    assert result["status"] == "fail"
    assert missing_by_key["demo_env_template"]["path"] == ".env.demo.example"
    assert missing_by_key["replay_qa_artifact"]["matched_count"] == 0
    assert "qa/replay/*.replay-record.json" in missing_by_key["replay_qa_artifact"]["patterns"]


def test_cli_writes_json_checklist_and_reports_json_without_bom(tmp_path: Path) -> None:
    _create_transfer_fixture(tmp_path)
    out_path = tmp_path / "qa" / "transfer.json"

    completed = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--repo-root",
            str(tmp_path),
            "--out",
            str(out_path),
            "--format",
            "json",
            "--report-json",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    stdout_payload = json.loads(completed.stdout)
    file_bytes = out_path.read_bytes()
    file_payload = json.loads(file_bytes.decode("utf-8"))

    assert stdout_payload["ok"] is True
    assert stdout_payload["out"] == out_path.resolve().as_posix()
    assert file_payload["format"] == "json"
    assert file_payload["out"] == out_path.resolve().as_posix()
    assert not file_bytes.startswith(b"\xef\xbb\xbf")


def test_cli_writes_markdown_checklist(tmp_path: Path) -> None:
    _create_transfer_fixture(tmp_path)
    out_path = tmp_path / "qa" / "transfer.md"

    completed = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--repo-root",
            str(tmp_path),
            "--out",
            str(out_path),
            "--format",
            "markdown",
        ],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    markdown = out_path.read_text(encoding="utf-8")

    assert "[PASS]" in completed.stdout
    assert "# Exhibition PC Transfer Checklist" in markdown
    assert "## Ready Items" in markdown
    assert "## USB Quest Steps" in markdown
    assert "`quest_usb_template`" in markdown
    assert "Machine-local absolute paths" in markdown


def test_cli_exits_nonzero_when_required_items_are_missing(tmp_path: Path) -> None:
    _create_transfer_fixture(tmp_path, include_replay=False)
    (tmp_path / "tools" / "start_exhibition_local_stack.ps1").unlink()

    completed = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--repo-root",
            str(tmp_path),
            "--out",
            str(tmp_path / "qa" / "transfer.json"),
            "--report-json",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    result = json.loads(completed.stdout)

    assert completed.returncode == 1
    assert result["ok"] is False
    assert {item["key"] for item in result["missing_items"]} == {
        "local_stack_helper",
        "replay_qa_artifact",
    }
