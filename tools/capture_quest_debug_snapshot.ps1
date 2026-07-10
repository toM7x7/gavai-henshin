param(
  [Parameter(Mandatory = $true)]
  [string]$Code,
  [switch]$QaCenterline,
  [switch]$Screencap,
  [string]$OutputRoot = "qa\logs",
  [string]$ApiUrl = "http://127.0.0.1:8010/api/quest-debug/latest",
  [string]$Timestamp = ""
)

$ErrorActionPreference = "Stop"

$normalizedCode = $Code.Trim().ToUpperInvariant()
if ($normalizedCode -notmatch "^[A-Z0-9]{4}$") {
  Write-Error "Code must be exactly 4 alphanumeric characters. Example: -Code 3601"
}

if (-not $Timestamp) {
  $Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
}

$snapshotDir = Join-Path $OutputRoot "quest-$normalizedCode-$Timestamp"
New-Item -ItemType Directory -Force -Path $snapshotDir | Out-Null

$devicesPath = Join-Path $snapshotDir "adb-devices.txt"
$reversePath = Join-Path $snapshotDir "adb-reverse.txt"
$debugPath = Join-Path $snapshotDir "quest-debug-latest.json"
$summaryPath = Join-Path $snapshotDir "operator-summary.txt"
$screencapPath = Join-Path $snapshotDir "screencap.png"

$adb = Get-Command adb -ErrorAction SilentlyContinue
if ($adb) {
  try {
    & $adb.Source devices -l 2>&1 | Set-Content -Encoding UTF8 $devicesPath
  } catch {
    "adb devices -l failed: $($_.Exception.Message)" | Set-Content -Encoding UTF8 $devicesPath
  }

  try {
    & $adb.Source reverse --list 2>&1 | Set-Content -Encoding UTF8 $reversePath
  } catch {
    "adb reverse --list failed: $($_.Exception.Message)" | Set-Content -Encoding UTF8 $reversePath
  }
} else {
  "adb was not found on PATH." | Set-Content -Encoding UTF8 $devicesPath
  "adb was not found on PATH." | Set-Content -Encoding UTF8 $reversePath
}

$latest = $null
$debugError = $null
try {
  $latest = Invoke-RestMethod -Uri $ApiUrl -Method Get
  $latest | ConvertTo-Json -Depth 32 | Set-Content -Encoding UTF8 $debugPath
} catch {
  $debugError = $_.Exception.Message
  [ordered]@{
    error = $debugError
    apiUrl = $ApiUrl
    capturedAt = (Get-Date).ToString("o")
  } | ConvertTo-Json -Depth 8 | Set-Content -Encoding UTF8 $debugPath
}

if ($Screencap) {
  if (-not $adb) {
    Write-Warning "Skipping screencap because adb was not found."
  } else {
    $cmd = "adb exec-out screencap -p > `"$screencapPath`""
    cmd /c $cmd
  }
}

$payload = $latest.record.payload
$href = $payload.query.href
$userAgent = $payload.query.userAgent
$actualCode = $payload.query.code
$xrSession = $payload.xr.session
$uxState = $payload.uxState
$centerlineQa = $payload.centerlineQa

$summary = [ordered]@{
  snapshotDir = $snapshotDir
  code = $normalizedCode
  qaCenterlineExpected = [bool]$QaCenterline
  apiUrl = $ApiUrl
  href = $href
  userAgent = $userAgent
  telemetryCode = $actualCode
  xrSession = $xrSession
  uxState = $uxState
  centerlineVerdict = $centerlineQa.verdict
  centerlineClassification = $centerlineQa.classification
  centerlineDisplayLine = $centerlineQa.displayLine
  apiError = $debugError
}

$summary.GetEnumerator() |
  ForEach-Object { "$($_.Key): $($_.Value)" } |
  Set-Content -Encoding UTF8 $summaryPath

Write-Output "Quest debug snapshot saved:"
Write-Output "  $snapshotDir"
Write-Output ""
Write-Output "Files:"
Write-Output "  adb-devices.txt"
Write-Output "  adb-reverse.txt"
Write-Output "  quest-debug-latest.json"
Write-Output "  operator-summary.txt"
if ($Screencap) {
  Write-Output "  screencap.png"
}

if ($debugError) {
  Write-Warning "Quest debug API capture failed: $debugError"
}
if ($QaCenterline -and -not $centerlineQa) {
  Write-Warning "QaCenterline was requested, but centerlineQa was not present in quest-debug-latest.json."
}
