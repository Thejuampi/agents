$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\common.ps1"
$Repo = Get-RepoRoot
Clear-ManifestHarness -Target $Repo -Harness 'opencode'
Write-Host "opencode: removed generated adapters from $Repo\.opencode"
