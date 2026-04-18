param(
  [string]$LanIp,
  [string]$OutputDir = "config",
  [string]$PfxPassword = "quest-local",
  [string]$RootSubject = "CN=Gavai Quest Local Root CA",
  [string]$ServerSubjectPrefix = "CN=Gavai Quest LAN"
)

$ErrorActionPreference = "Stop"

if (-not $LanIp) {
  $defaultRoute = Get-NetRoute -DestinationPrefix "0.0.0.0/0" |
    Sort-Object RouteMetric, InterfaceMetric |
    Select-Object -First 1
  if (-not $defaultRoute) {
    throw "Could not detect the default network route. Pass -LanIp explicitly."
  }
  $LanIp = Get-NetIPAddress -AddressFamily IPv4 -InterfaceIndex $defaultRoute.InterfaceIndex |
    Where-Object { $_.IPAddress -notlike "127.*" -and $_.PrefixOrigin -ne "WellKnown" } |
    Select-Object -First 1 -ExpandProperty IPAddress
}

if (-not $LanIp) {
  throw "Could not detect a LAN IPv4 address. Pass -LanIp explicitly."
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
$rootCerPath = Join-Path $OutputDir "quest-lan-root-ca.cer"
$pfxPath = Join-Path $OutputDir "quest-lan.pfx"
Remove-Item -LiteralPath $rootCerPath, $pfxPath -Force -ErrorAction SilentlyContinue

$root = New-SelfSignedCertificate `
  -Type Custom `
  -Subject $RootSubject `
  -KeyAlgorithm RSA `
  -KeyLength 2048 `
  -HashAlgorithm SHA256 `
  -KeyExportPolicy Exportable `
  -CertStoreLocation "Cert:\CurrentUser\My" `
  -KeyUsage CertSign, CRLSign, DigitalSignature `
  -NotAfter (Get-Date).AddYears(3) `
  -TextExtension @("2.5.29.19={critical}{text}ca=TRUE&pathlength=0")

Export-Certificate -Cert $root -FilePath $rootCerPath | Out-Null
Import-Certificate -FilePath $rootCerPath -CertStoreLocation "Cert:\CurrentUser\Root" | Out-Null

$server = New-SelfSignedCertificate `
  -Type Custom `
  -Subject "$ServerSubjectPrefix $LanIp" `
  -Signer $root `
  -KeyAlgorithm RSA `
  -KeyLength 2048 `
  -HashAlgorithm SHA256 `
  -KeyExportPolicy Exportable `
  -CertStoreLocation "Cert:\CurrentUser\My" `
  -KeyUsage DigitalSignature, KeyEncipherment `
  -NotAfter (Get-Date).AddYears(2) `
  -TextExtension @(
    "2.5.29.17={text}IPAddress=$LanIp&DNS=localhost&IPAddress=127.0.0.1",
    "2.5.29.37={text}1.3.6.1.5.5.7.3.1"
  )

$password = ConvertTo-SecureString -String $PfxPassword -Force -AsPlainText
Export-PfxCertificate -Cert $server -FilePath $pfxPath -Password $password | Out-Null

Write-Output "LAN_IP=$LanIp"
Write-Output "ROOT_CA=$rootCerPath"
Write-Output "PFX=$pfxPath"
Write-Output "PFX_PASSWORD=$PfxPassword"
Write-Output "QUEST_URL=https://$LanIp`:5173/viewer/quest-iw-demo/"
