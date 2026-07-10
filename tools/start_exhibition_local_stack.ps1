param(
  [int]$ApiPort = 8010,
  [int]$QuestPort = 5173,
  [int]$MocopiBodySimPort = 8021,
  [int]$MocopiUdpPort = 12351,
  [string]$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string]$EnvFile = ".env.demo.example",
  [string]$RecallCode = "",
  [switch]$LaunchQuest,
  [switch]$SkipAdbReverse,
  [switch]$SkipSmoke,
  [switch]$RequireAdbReverseSmoke,
  [switch]$EnableMocopiBodySim,
  [switch]$NoCacheBust,
  [int]$StartupTimeoutSec = 45,
  [string]$ReportDir = "qa"
)

$ErrorActionPreference = "Stop"

function ConvertTo-PowerShellLiteral {
  param([string]$Value)

  return "'" + ($Value -replace "'", "''") + "'"
}

function Test-PortListening {
  param([int]$Port)

  $client = [System.Net.Sockets.TcpClient]::new()
  try {
    $async = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
    if (-not $async.AsyncWaitHandle.WaitOne(500, $false)) {
      return $false
    }
    $client.EndConnect($async)
    return $true
  } catch {
    return $false
  } finally {
    $client.Close()
  }
}

function Wait-PortListening {
  param(
    [int]$Port,
    [int]$TimeoutSec
  )

  $deadline = (Get-Date).AddSeconds($TimeoutSec)
  do {
    if (Test-PortListening -Port $Port) {
      return $true
    }
    Start-Sleep -Milliseconds 500
  } while ((Get-Date) -lt $deadline)

  return $false
}

function Assert-CommandAvailable {
  param([string]$Name)

  $command = Get-Command $Name -ErrorAction SilentlyContinue
  if (-not $command) {
    throw "$Name was not found on PATH."
  }
}

function Write-Utf8NoBom {
  param(
    [string]$Path,
    [string]$Text
  )

  $directory = Split-Path -Parent $Path
  if ($directory) {
    New-Item -ItemType Directory -Force -Path $directory | Out-Null
  }

  $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
  [System.IO.File]::WriteAllText($Path, $Text, $utf8NoBom)
}

function Start-BackgroundCommand {
  param(
    [string]$Name,
    [string]$Command,
    [string]$StdoutPath,
    [string]$StderrPath
  )

  Write-Output "Starting $Name..."
  Write-Output "  stdout: $StdoutPath"
  Write-Output "  stderr: $StderrPath"
  return Start-Process `
    -FilePath "powershell" `
    -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", $Command) `
    -WorkingDirectory $RepoRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput $StdoutPath `
    -RedirectStandardError $StderrPath `
    -PassThru
}

function Invoke-ReportCommand {
  param(
    [string]$Name,
    [string]$Command,
    [string[]]$Arguments,
    [string]$OutputPath
  )

  Write-Output "Running $Name..."
  $output = & $Command @Arguments 2>&1
  $exitCode = $LASTEXITCODE
  $text = ($output | Out-String).TrimEnd()
  if ($text.Length -gt 0) {
    Write-Utf8NoBom -Path $OutputPath -Text ($text + "`n")
  } else {
    Write-Utf8NoBom -Path $OutputPath -Text ""
  }

  if ($exitCode -ne 0) {
    throw "$Name failed with exit code $exitCode. See $OutputPath"
  }

  Write-Output "  report: $OutputPath"
}

$RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
Set-Location -LiteralPath $RepoRoot

Assert-CommandAvailable -Name "python"
Assert-CommandAvailable -Name "npm"

$apiBaseUrl = "http://127.0.0.1:$ApiPort"
$questBaseUrlForPc = "http://127.0.0.1:$QuestPort"
$questBaseUrlForHeadset = "http://localhost:$QuestPort"
$mocopiBodySimLatestForHeadset = "http://localhost:$MocopiBodySimPort/body-sim/latest"
$questPath = "/viewer/quest-iw-demo/?newRoute=1"
if ($EnableMocopiBodySim) {
  $encodedLatest = [System.Uri]::EscapeDataString($mocopiBodySimLatestForHeadset)
  $questPath = "$questPath&mocopiLive=1&bodySimLatest=$encodedLatest"
}
if ($RecallCode) {
  $normalizedRecallCode = $RecallCode.Trim().ToUpperInvariant()
  if ($normalizedRecallCode -notmatch "^[A-Z0-9]{4}$") {
    throw "RecallCode must be exactly 4 alphanumeric characters. Example: -RecallCode 3601"
  }
  $questPath = "$questPath&code=$normalizedRecallCode"
}

$reportRoot = if ([System.IO.Path]::IsPathRooted($ReportDir)) {
  $ReportDir
} else {
  Join-Path $RepoRoot $ReportDir
}
$runReportDir = Join-Path $reportRoot ("local-stack-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
New-Item -ItemType Directory -Force -Path $runReportDir | Out-Null

$envFilePath = if ([System.IO.Path]::IsPathRooted($EnvFile)) {
  $EnvFile
} else {
  Join-Path $RepoRoot $EnvFile
}
if (-not (Test-Path -LiteralPath $envFilePath)) {
  throw "Env file was not found: $envFilePath"
}

$apiStarted = $false
$questStarted = $false
$mocopiBodySimStarted = $false
$apiProcess = $null
$questProcess = $null
$mocopiBodySimProcess = $null

if (Test-PortListening -Port $ApiPort) {
  Write-Warning "Port $ApiPort is already listening; reusing existing Web/API server."
} else {
  $apiStdout = Join-Path $runReportDir "api.stdout.log"
  $apiStderr = Join-Path $runReportDir "api.stderr.log"
  $srcPath = Join-Path $RepoRoot "src"
  $apiCommand = @(
    ('$env:PYTHONPATH = ' + (ConvertTo-PowerShellLiteral $srcPath)),
    ("python tools/run_henshin.py serve-dashboard --port $ApiPort --root " + (ConvertTo-PowerShellLiteral $RepoRoot))
  ) -join "; "
  $apiProcess = Start-BackgroundCommand -Name "Web/API server on $ApiPort" -Command $apiCommand -StdoutPath $apiStdout -StderrPath $apiStderr
  $apiStarted = $true
  if (-not (Wait-PortListening -Port $ApiPort -TimeoutSec $StartupTimeoutSec)) {
    if ($apiProcess.HasExited) {
      throw "Web/API server exited before listening on $ApiPort. See $apiStderr"
    }
    throw "Web/API server did not listen on $ApiPort within $StartupTimeoutSec seconds. See $apiStderr"
  }
}

if (Test-PortListening -Port $QuestPort) {
  Write-Warning "Port $QuestPort is already listening; reusing existing Quest Vite server."
} else {
  $questStdout = Join-Path $runReportDir "quest-vite.stdout.log"
  $questStderr = Join-Path $runReportDir "quest-vite.stderr.log"
  $questCommand = @(
    ('$env:QUEST_API_TARGET = ' + (ConvertTo-PowerShellLiteral $apiBaseUrl)),
    ('$env:QUEST_PORT = ' + (ConvertTo-PowerShellLiteral "$QuestPort")),
    ("npm run dev:quest -- --host 0.0.0.0 --port $QuestPort")
  ) -join "; "
  $questProcess = Start-BackgroundCommand -Name "Quest Vite server on $QuestPort" -Command $questCommand -StdoutPath $questStdout -StderrPath $questStderr
  $questStarted = $true
  if (-not (Wait-PortListening -Port $QuestPort -TimeoutSec $StartupTimeoutSec)) {
    if ($questProcess.HasExited) {
      throw "Quest Vite server exited before listening on $QuestPort. See $questStderr"
    }
    throw "Quest Vite server did not listen on $QuestPort within $StartupTimeoutSec seconds. See $questStderr"
  }
}

if ($EnableMocopiBodySim) {
  if (Test-PortListening -Port $MocopiBodySimPort) {
    Write-Warning "Port $MocopiBodySimPort is already listening; reusing existing mocopi body-sim/latest adapter."
  } else {
    $mocopiStdout = Join-Path $runReportDir "mocopi-body-sim.stdout.log"
    $mocopiStderr = Join-Path $runReportDir "mocopi-body-sim.stderr.log"
    $mocopiCommand = "python tools/serve_mocopi_body_sim_latest.py --bind-host 0.0.0.0 --udp-port $MocopiUdpPort --http-host 127.0.0.1 --http-port $MocopiBodySimPort"
    $mocopiBodySimProcess = Start-BackgroundCommand -Name "mocopi body-sim/latest adapter on $MocopiBodySimPort" -Command $mocopiCommand -StdoutPath $mocopiStdout -StderrPath $mocopiStderr
    $mocopiBodySimStarted = $true
    if (-not (Wait-PortListening -Port $MocopiBodySimPort -TimeoutSec $StartupTimeoutSec)) {
      if ($mocopiBodySimProcess.HasExited) {
        throw "mocopi body-sim/latest adapter exited before listening on $MocopiBodySimPort. See $mocopiStderr"
      }
      throw "mocopi body-sim/latest adapter did not listen on $MocopiBodySimPort within $StartupTimeoutSec seconds. See $mocopiStderr"
    }
  }
}

$contractReport = Join-Path $runReportDir "service_deployment_contract_local.json"
$contractArgs = @(
  "tools/validate_service_deployment_contract.py",
  "--mode", "local",
  "--web-base-url", $apiBaseUrl,
  "--api-base-url", $apiBaseUrl,
  "--quest-base-url", $questBaseUrlForHeadset,
  "--env-file", $envFilePath,
  "--report-json"
)
Invoke-ReportCommand -Name "service deployment contract local check" -Command "python" -Arguments $contractArgs -OutputPath $contractReport

if ($SkipAdbReverse) {
  Write-Warning "Skipping adb reverse. Quest Browser will not see PC localhost unless another path is configured."
  if ($LaunchQuest) {
    Write-Warning "-LaunchQuest was requested but -SkipAdbReverse is set; Quest URL will not be launched."
  }
} else {
  $adbReverseScript = Join-Path $RepoRoot "tools/start_quest_adb_reverse.ps1"
  $adbReverseArgs = @(
    "-QuestPort", "$QuestPort",
    "-ApiPort", "$ApiPort",
    "-MocopiBodySimPort", "$MocopiBodySimPort",
    "-QuestPath", $questPath
  )
  if ($RecallCode) {
    $adbReverseArgs += @("-RecallCode", $RecallCode)
  }
  if (-not $NoCacheBust) {
    $adbReverseArgs += "-CacheBust"
  }
  if ($LaunchQuest) {
    $adbReverseArgs += "-LaunchBrowser"
  }
  & $adbReverseScript @adbReverseArgs
}

if ($SkipSmoke) {
  Write-Warning "Skipping exhibition smoke check."
} else {
  $smokeReport = Join-Path $runReportDir "exhibition_smoke_check.json"
  $smokeArgs = @(
    "tools/exhibition_smoke_check.py",
    "--api-base", $apiBaseUrl,
    "--quest-base", $questBaseUrlForPc,
    "--timeout", "15"
  )
  if ($RecallCode) {
    $smokeArgs += @("--code", $RecallCode)
  } else {
    $smokeArgs += "--forge"
  }
  if ($RequireAdbReverseSmoke) {
    if ($SkipAdbReverse) {
      Write-Warning "-RequireAdbReverseSmoke ignored because -SkipAdbReverse is set."
    } else {
      $smokeArgs += "--require-adb-reverse"
    }
  }
  Invoke-ReportCommand -Name "exhibition smoke check" -Command "python" -Arguments $smokeArgs -OutputPath $smokeReport
}

Write-Output ""
Write-Output "Exhibition local stack is ready."
Write-Output "  Web Forge: $apiBaseUrl/viewer/armor-forge/"
Write-Output "  API health: $apiBaseUrl/api/health"
Write-Output "  Quest PC check: $questBaseUrlForPc/viewer/quest-iw-demo/?newRoute=1"
Write-Output "  Quest USB headset URL: $questBaseUrlForHeadset$questPath"
if ($EnableMocopiBodySim) {
  Write-Output "  mocopi send target: PC IPv4, UDP $MocopiUdpPort"
  Write-Output "  mocopi latest: http://127.0.0.1:$MocopiBodySimPort/body-sim/latest"
}
Write-Output "  Report dir: $runReportDir"
Write-Output "  API started by this script: $apiStarted"
Write-Output "  Quest Vite started by this script: $questStarted"
Write-Output "  mocopi body-sim adapter started by this script: $mocopiBodySimStarted"
