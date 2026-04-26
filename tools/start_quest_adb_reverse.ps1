param(
  [int]$QuestPort = 5173,
  [int]$ApiPort = 8010,
  [string]$QuestPath = "/viewer/quest-iw-demo/?newRoute=1&mockTrigger=1&mic=1"
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

$devices = & $adb.Source devices
if (-not ($devices -match "`tdevice")) {
  Write-Error @"
No adb device is ready.

Connect the Quest by USB, accept the headset authorization prompt, then run:
  adb devices
"@
}

& $adb.Source reverse "tcp:$QuestPort" "tcp:$QuestPort" | Out-Null
& $adb.Source reverse "tcp:$ApiPort" "tcp:$ApiPort" | Out-Null

Write-Output "ADB reverse is active:"
Write-Output "  Quest localhost:$QuestPort -> PC localhost:$QuestPort"
Write-Output "  Quest localhost:$ApiPort -> PC localhost:$ApiPort"
Write-Output ""
Write-Output "Open this in Quest Browser:"
Write-Output "  http://localhost:$QuestPort$QuestPath"
