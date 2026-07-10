param(
  [int]$QuestPort = 5173,
  [int]$ApiPort = 8010,
  [int]$MocopiBodySimPort = 8021,
  [string]$QuestPath = "/viewer/quest-iw-demo/?newRoute=1",
  [string]$RecallCode = "",
  [switch]$LaunchBrowser,
  [switch]$CacheBust
)

$ErrorActionPreference = "Stop"

$adb = Get-Command adb -ErrorAction SilentlyContinue
if (-not $adb) {
  Write-Error @"
adb was not found on PATH.

Install Android Platform Tools or Meta Quest Developer Hub, enable Developer Mode on the Quest,
connect the headset by USB, then run this script again.
"@
}

$devices = & $adb.Source devices -l
$readyDevices = $devices | Where-Object { $_ -match "^\S+\s+device\s" }
$unauthorizedDevices = $devices | Where-Object { $_ -match "^\S+\s+unauthorized\s" }
$offlineDevices = $devices | Where-Object { $_ -match "^\S+\s+offline\s" }

if ($unauthorizedDevices) {
  Write-Error @"
Quest is connected but adb is unauthorized.

Put on the headset and accept the "Allow USB debugging?" prompt. If possible, select
"Always allow from this computer". Then run:
  adb devices -l

If the prompt does not appear, unplug/replug USB and restart adb:
  adb kill-server
  adb start-server
  adb devices -l

Current adb devices -l output:
$($devices -join "`n")
"@
}

if ($offlineDevices) {
  Write-Error @"
Quest is connected but adb reports it as offline.

Unplug/replug USB, wake the headset, then run:
  adb devices -l

Current adb devices -l output:
$($devices -join "`n")
"@
}

if (-not $readyDevices) {
  Write-Error @"
No adb device is ready.

Connect the Quest by USB, accept the headset authorization prompt, then run:
  adb devices -l

Expected state:
  <device_id>    device ...

Current adb devices -l output:
$($devices -join "`n")
"@
}

if ($RecallCode) {
  $normalizedRecallCode = $RecallCode.Trim().ToUpperInvariant()
  if ($normalizedRecallCode -notmatch "^[A-Z0-9]{4}$") {
    Write-Error "RecallCode must be exactly 4 alphanumeric characters. Example: -RecallCode 3601"
  }
  if ($QuestPath -notmatch "([?&])code=") {
    $separator = if ($QuestPath.Contains("?")) { "&" } else { "?" }
    $QuestPath = "$QuestPath${separator}code=$normalizedRecallCode"
  }
}

if ($CacheBust) {
  $stamp = [DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()
  $separator = if ($QuestPath.Contains("?")) { "&" } else { "?" }
  $QuestPath = "$QuestPath${separator}t=$stamp"
}

& $adb.Source reverse "tcp:$QuestPort" "tcp:$QuestPort" | Out-Null
& $adb.Source reverse "tcp:$ApiPort" "tcp:$ApiPort" | Out-Null
& $adb.Source reverse "tcp:$MocopiBodySimPort" "tcp:$MocopiBodySimPort" | Out-Null

$questUrl = "http://localhost:$QuestPort$QuestPath"

Write-Output "ADB reverse is active:"
Write-Output "  Quest localhost:$QuestPort -> PC localhost:$QuestPort"
Write-Output "  Quest localhost:$ApiPort -> PC localhost:$ApiPort"
Write-Output "  Quest localhost:$MocopiBodySimPort -> PC localhost:$MocopiBodySimPort"
Write-Output ""
Write-Output "Open this in Quest Browser:"
Write-Output "  $questUrl"

if ($LaunchBrowser) {
  Write-Output ""
  Write-Output "Launching Quest Browser with adb intent:"
  Write-Output "  $questUrl"
  & $adb.Source shell am start -a android.intent.action.VIEW -d "$questUrl"
}
