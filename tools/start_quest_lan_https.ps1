param(
  [string]$CertPath = "config\quest-lan.pem",
  [string]$KeyPath = "config\quest-lan-key.pem",
  [string]$PfxPath = "config\quest-lan.pfx",
  [string]$PfxPassword = "quest-local",
  [string]$HostAddress = "0.0.0.0",
  [int]$Port = 5173,
  [string]$ApiTarget = "http://127.0.0.1:8010"
)

$ErrorActionPreference = "Stop"

$cert = Resolve-Path -LiteralPath $CertPath -ErrorAction SilentlyContinue
$key = Resolve-Path -LiteralPath $KeyPath -ErrorAction SilentlyContinue
$pfx = Resolve-Path -LiteralPath $PfxPath -ErrorAction SilentlyContinue

if ((-not $cert -or -not $key) -and -not $pfx) {
  $defaultRoute = Get-NetRoute -DestinationPrefix "0.0.0.0/0" |
    Sort-Object RouteMetric, InterfaceMetric |
    Select-Object -First 1
  $lanIp = if ($defaultRoute) {
    Get-NetIPAddress -AddressFamily IPv4 -InterfaceIndex $defaultRoute.InterfaceIndex |
      Where-Object { $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -ne "WellKnown" } |
      Select-Object -First 1 -ExpandProperty IPAddress
  } else {
    Get-NetIPAddress -AddressFamily IPv4 |
      Where-Object { $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -ne "WellKnown" } |
      Select-Object -First 1 -ExpandProperty IPAddress
  }

  Write-Error @"
Quest LAN HTTPS certificate files were not found.

Expected:
  $CertPath
  $KeyPath
or:
  $PfxPath

Create a trusted local certificate first:
  .\tools\new_quest_lan_cert.ps1 -LanIp $lanIp

Then install/trust config\quest-lan-root-ca.cer on the Quest device, and run this script again.
"@
}

if ($pfx) {
  $env:QUEST_HTTPS_PFX = $pfx.Path
  $env:QUEST_HTTPS_PFX_PASSWORD = $PfxPassword
  Remove-Item Env:\QUEST_HTTPS_CERT -ErrorAction SilentlyContinue
  Remove-Item Env:\QUEST_HTTPS_KEY -ErrorAction SilentlyContinue
} else {
  $env:QUEST_HTTPS_CERT = $cert.Path
  $env:QUEST_HTTPS_KEY = $key.Path
  Remove-Item Env:\QUEST_HTTPS_PFX -ErrorAction SilentlyContinue
  Remove-Item Env:\QUEST_HTTPS_PFX_PASSWORD -ErrorAction SilentlyContinue
}
$env:QUEST_HOST = $HostAddress
$env:QUEST_PORT = [string]$Port
$env:QUEST_API_TARGET = $ApiTarget

npm run dev:quest -- --host $HostAddress --port $Port
