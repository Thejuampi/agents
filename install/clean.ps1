$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\common.ps1"
$Repo = Get-RepoRoot

Clear-ManifestHarness -Target $Repo -Harness 'opencode'

$sycDir = Join-Path $Repo '.agents-sync'
if (Test-Path -LiteralPath $sycDir) { Remove-Item -LiteralPath $sycDir -Recurse -Force }
$ocDir = Join-Path $Repo '.opencode'
if (Test-Path -LiteralPath $ocDir) {
  $cfg = Join-Path $ocDir 'opencode.json'
  if (Test-Path -LiteralPath $cfg) { Remove-Item -LiteralPath $cfg -Force }
  if (Test-Path -LiteralPath "$cfg.bak") { Remove-Item -LiteralPath "$cfg.bak" -Force }
  $cmdDir = Join-Path $ocDir 'commands'
  if (Test-Path -LiteralPath $cmdDir) { Remove-Item -LiteralPath $cmdDir -Recurse -Force }
  if ((Get-ChildItem -LiteralPath $ocDir -Force -ErrorAction SilentlyContinue | Measure-Object).Count -eq 0) {
    Remove-Item -LiteralPath $ocDir -Force
  }
}
Write-Host "clean: removed generated artifacts from $Repo"
