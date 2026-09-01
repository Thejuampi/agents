#Requires -Version 5.1
[CmdletBinding()]
param([string]$Target = $env:USERPROFILE)

$ErrorActionPreference = 'Stop'
$SettingsPath = Join-Path $Target '.claude\settings.json'
if (-not (Test-Path -LiteralPath $SettingsPath)) { Write-Host 'Nothing to remove.'; return }

$Settings = Get-Content -LiteralPath $SettingsPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($Settings.PSObject.Properties.Name -contains 'hooks' -and $null -ne $Settings.hooks) {
  foreach ($event in @('Stop', 'SessionStart')) {
    if ($Settings.hooks.PSObject.Properties.Name -contains $event) {
      $kept = @($Settings.hooks.$event | Where-Object {
        -not ($_.hooks | Where-Object { $_.command -match 'check-stop\.py|judge-report\.py' })
      })
      if ($kept.Count -gt 0) { $Settings.hooks.$event = $kept }
      else { $Settings.hooks.PSObject.Properties.Remove($event) }
    }
  }
}

Copy-Item -LiteralPath $SettingsPath -Destination "$SettingsPath.bak" -Force
Set-Content -LiteralPath $SettingsPath -Value ($Settings | ConvertTo-Json -Depth 32) -Encoding UTF8
Write-Host "Guard removed from $SettingsPath (backup at $SettingsPath.bak)" -ForegroundColor Green
