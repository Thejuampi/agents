param([string]$Target = '.')
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\common.ps1"
$TargetPath = Resolve-Target -Target $Target

foreach ($h in 'claude', 'codex', 'grok', 'vscode') {
  Clear-ManifestHarness -Target $TargetPath -Harness $h
}
Write-Host "uninstall: removed generated harness files from $TargetPath"
