from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "tools" / "start_quest_adb_reverse.ps1"
PACKAGE_JSON = REPO_ROOT / "package.json"


def test_adb_reverse_script_can_launch_fresh_quest_browser_url() -> None:
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "[switch]$LaunchBrowser" in script
    assert "[switch]$CacheBust" in script
    assert "[int]$MocopiBodySimPort = 8021" in script
    assert "$questUrl = \"http://localhost:$QuestPort$QuestPath\"" in script
    assert "ToUnixTimeMilliseconds()" in script
    assert 'reverse "tcp:$MocopiBodySimPort" "tcp:$MocopiBodySimPort"' in script
    assert "Quest localhost:$MocopiBodySimPort -> PC localhost:$MocopiBodySimPort" in script
    assert "shell am start -a android.intent.action.VIEW -d \"$questUrl\"" in script


def test_adb_reverse_script_builds_code_url_before_cache_bust() -> None:
    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert script.index("if ($RecallCode)") < script.index("if ($CacheBust)")
    assert script.index("if ($CacheBust)") < script.index("$questUrl =")
    assert script.index("$questUrl =") < script.index("if ($LaunchBrowser)")


def test_package_exposes_launch_helper_for_exhibition_operators() -> None:
    package_json = PACKAGE_JSON.read_text(encoding="utf-8")

    assert "dev:quest:adb" in package_json
    assert "dev:quest:adb:launch" in package_json
    assert "-CacheBust -LaunchBrowser" in package_json


def test_adb_reverse_script_parses_in_powershell_when_available() -> None:
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
