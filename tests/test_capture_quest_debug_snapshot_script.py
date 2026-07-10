from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "tools" / "capture_quest_debug_snapshot.ps1"


def test_capture_script_exposes_operator_parameters() -> None:
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "[string]$Code" in script
    assert "[switch]$QaCenterline" in script
    assert "[switch]$Screencap" in script
    assert '[string]$OutputRoot = "qa\\logs"' in script
    assert '[string]$ApiUrl = "http://127.0.0.1:8010/api/quest-debug/latest"' in script


def test_capture_script_writes_required_snapshot_files() -> None:
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert '"quest-$normalizedCode-$Timestamp"' in script
    assert '"adb-devices.txt"' in script
    assert '"adb-reverse.txt"' in script
    assert '"quest-debug-latest.json"' in script
    assert '"screencap.png"' in script
    assert "Invoke-RestMethod -Uri $ApiUrl -Method Get" in script
    assert "ConvertTo-Json -Depth 32" in script


def test_capture_script_records_centerline_summary() -> None:
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "centerlineVerdict = $centerlineQa.verdict" in script
    assert "centerlineClassification = $centerlineQa.classification" in script
    assert "centerlineDisplayLine = $centerlineQa.displayLine" in script
    assert "QaCenterline was requested, but centerlineQa was not present" in script


def test_capture_script_parses_in_powershell_when_available() -> None:
    powershell = shutil.which("powershell") or shutil.which("pwsh")
    if not powershell:
        pytest.skip("PowerShell is not available on this host")

    command = (
        "$null = [scriptblock]::Create((Get-Content "
        f"-LiteralPath '{SCRIPT_PATH}' -Raw)); 'ok'"
    )
    result = subprocess.run(
        [powershell, "-NoProfile", "-Command", command],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().endswith("ok")
