#Requires -Version 5.1
[CmdletBinding()]
param(
  [string]$Target = $env:USERPROFILE,
  [string]$Python,
  [int]$Timeout = 90,
  [switch]$WithReport,
  [switch]$WhatIfOnly
)

$ErrorActionPreference = 'Stop'
$HookRoot = (Resolve-Path $PSScriptRoot).Path.Replace('\', '/')

function Resolve-Python {
  param([string]$Explicit)
  if ($Explicit) {
    if (-not (Test-Path -LiteralPath $Explicit)) { throw "Python not found at '$Explicit'." }
    return (Resolve-Path $Explicit).Path.Replace('\', '/')
  }
  $cmd = Get-Command python.exe -ErrorAction SilentlyContinue
  if ($cmd) { return $cmd.Source.Replace('\', '/') }
  $py = Get-Command py.exe -ErrorAction SilentlyContinue
  if ($py) {
    $found = & $py.Source -3 -c "import sys; print(sys.executable)" 2>$null
    if ($LASTEXITCODE -eq 0 -and $found) { return $found.Trim().Replace('\', '/') }
  }
  throw "No Python 3 on PATH. Pass -Python 'C:/Python314/python.exe'."
}

function Get-Settings {
  param([string]$Path)
  if (Test-Path -LiteralPath $Path) {
    $raw = Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    if ($raw.Trim()) { return $raw | ConvertFrom-Json }
  }
  return [pscustomobject]@{}
}

function Set-Prop {
  param($Object, [string]$Name, $Value)
  if ($Object.PSObject.Properties.Name -contains $Name) { $Object.$Name = $Value }
  else { $Object | Add-Member -NotePropertyName $Name -NotePropertyValue $Value }
}

$PythonPath = Resolve-Python -Explicit $Python
$SettingsPath = Join-Path $Target '.claude\settings.json'
$Settings = Get-Settings -Path $SettingsPath

$stopEntry = [pscustomobject]@{
  hooks = @(
    [pscustomobject]@{
      type    = 'command'
      command = "$PythonPath -u $HookRoot/check-stop.py"
      timeout = $Timeout
      env     = [pscustomobject]@{
        HOME         = $Target.Replace('\', '/')
        STOP_HOLDOUT = '0'
      }
    }
  )
}

if ($Settings.PSObject.Properties.Name -notcontains 'hooks' -or $null -eq $Settings.hooks) {
  Set-Prop -Object $Settings -Name 'hooks' -Value ([pscustomobject]@{})
}
Set-Prop -Object $Settings.hooks -Name 'Stop' -Value @($stopEntry)

if ($WithReport) {
  $reportEntry = [pscustomobject]@{
    hooks = @(
      [pscustomobject]@{
        type    = 'command'
        command = "$PythonPath -u $HookRoot/judge-report.py --brief"
        timeout = 20
      }
    )
  }
  Set-Prop -Object $Settings.hooks -Name 'SessionStart' -Value @($reportEntry)
}

$json = $Settings | ConvertTo-Json -Depth 32

if ($WhatIfOnly) {
  Write-Host "Would write $SettingsPath" -ForegroundColor Yellow
  Write-Output $json
  return
}

$dir = Split-Path -Parent $SettingsPath
if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
if (Test-Path -LiteralPath $SettingsPath) {
  Copy-Item -LiteralPath $SettingsPath -Destination "$SettingsPath.bak" -Force
}
Set-Content -LiteralPath $SettingsPath -Value $json -Encoding UTF8

Write-Host "Stop hook wired -> $HookRoot/check-stop.py" -ForegroundColor Green
Write-Host "Python          -> $PythonPath"
Write-Host "Settings        -> $SettingsPath (backup at $SettingsPath.bak)"
if ($WithReport) { Write-Host "SessionStart    -> judge-report.py --brief" }
