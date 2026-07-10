from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "tools" / "start_exhibition_local_stack.ps1"


def _script() -> str:
    return SCRIPT_PATH.read_text(encoding="utf-8")


def test_stack_script_exposes_operator_parameters_and_fixed_ports() -> None:
    script = _script()

    assert "[int]$ApiPort = 8010" in script
    assert "[int]$QuestPort = 5173" in script
    assert "[int]$MocopiBodySimPort = 8021" in script
    assert "[int]$MocopiUdpPort = 12351" in script
    assert '[string]$EnvFile = ".env.demo.example"' in script
    assert "[switch]$LaunchQuest" in script
    assert "[switch]$SkipAdbReverse" in script
    assert "[switch]$RequireAdbReverseSmoke" in script
    assert "[switch]$EnableMocopiBodySim" in script
    assert '$questBaseUrlForHeadset = "http://localhost:$QuestPort"' in script
    assert '$mocopiBodySimLatestForHeadset = "http://localhost:$MocopiBodySimPort/body-sim/latest"' in script
    assert '$questPath = "$questPath&mocopiLive=1&bodySimLatest=$encodedLatest"' in script


def test_stack_script_starts_or_reuses_api_and_quest_without_destructive_kills() -> None:
    script = _script()

    assert "Test-PortListening" in script
    assert "Wait-PortListening" in script
    assert "Start-BackgroundCommand" in script
    assert "Start-Process" in script
    assert "-WindowStyle Hidden" in script
    assert "serve-dashboard --port $ApiPort --root" in script
    assert "npm run dev:quest -- --host 0.0.0.0 --port $QuestPort" in script
    assert "serve_mocopi_body_sim_latest.py --bind-host 0.0.0.0 --udp-port $MocopiUdpPort --http-host 127.0.0.1 --http-port $MocopiBodySimPort" in script
    assert "Port $ApiPort is already listening; reusing existing Web/API server." in script
    assert "Port $QuestPort is already listening; reusing existing Quest Vite server." in script
    assert "Port $MocopiBodySimPort is already listening; reusing existing mocopi body-sim/latest adapter." in script

    forbidden_tokens = [
        "Stop-Process",
        "taskkill",
        "kill-server",
        "Remove-Item Env:",
        "Get-Process | Stop",
    ]
    for token in forbidden_tokens:
        assert token not in script


def test_stack_script_runs_contract_adb_reverse_launch_and_smoke_checks() -> None:
    script = _script()

    assert "validate_service_deployment_contract.py" in script
    assert '"--mode", "local"' in script
    assert '"--web-base-url", $apiBaseUrl' in script
    assert '"--api-base-url", $apiBaseUrl' in script
    assert '"--quest-base-url", $questBaseUrlForHeadset' in script
    assert "start_quest_adb_reverse.ps1" in script
    assert '"-MocopiBodySimPort", "$MocopiBodySimPort"' in script
    assert '"-QuestPath", $questPath' in script
    assert '$adbReverseArgs += "-CacheBust"' in script
    assert '$adbReverseArgs += "-LaunchBrowser"' in script
    assert "exhibition_smoke_check.py" in script
    assert '$smokeArgs += "--forge"' in script
    assert '$smokeArgs += "--require-adb-reverse"' in script


def test_stack_script_writes_reports_as_utf8_without_bom() -> None:
    script = _script()

    assert "Write-Utf8NoBom" in script
    assert "[System.Text.UTF8Encoding]::new($false)" in script
    assert "service_deployment_contract_local.json" in script
    assert "exhibition_smoke_check.json" in script
    assert "mocopi-body-sim.stdout.log" in script
    assert '("local-stack-" + (Get-Date -Format "yyyyMMdd-HHmmss"))' in script


def test_stack_script_parses_in_powershell_when_available() -> None:
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
