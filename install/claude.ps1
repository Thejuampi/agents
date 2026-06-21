param([string]$Target = '.')
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\common.ps1"
$Repo = Get-RepoRoot
$TargetPath = Resolve-Target -Target $Target

# BEST-EFFORT / OPT-IN. Not in the default `make install` path.
# Claude Code surface is not validated here; this copies agents/*.md and
# commands/*.md into .claude/ as a starting point. Verify against your
# Claude Code version before relying on it.

$AgentsDir = Join-Path $TargetPath '.claude\agents'
$CmdsDir = Join-Path $TargetPath '.claude\commands'
New-Item -ItemType Directory -Path $AgentsDir -Force | Out-Null
New-Item -ItemType Directory -Path $CmdsDir -Force | Out-Null

$genFiles = @()

foreach ($a in (Get-AgentFiles -Repo $Repo)) {
  $content = (Get-Content -Raw -LiteralPath $a.Path).TrimEnd()
  $desc = Get-AgentDescription -Path $a.Path
  $header = New-GeneratedComment -Source "agents/$($a.Name).md"
  $body = "---`nname: $($a.Name)`ndescription: $desc`n---`n`n$header`n`n$content`n"
  $out = Join-Path $AgentsDir "$($a.Name).md"
  Set-Content -LiteralPath $out -Value $body -Encoding utf8 -NoNewline
  $genFiles += $out
}

foreach ($c in (Get-CommandFiles -Repo $Repo)) {
  $content = (Get-Content -Raw -LiteralPath $c.Path).TrimEnd()
  $header = New-GeneratedComment -Source "commands/$($c.Name).md"
  $body = "$header`n`n$content`n"
  $out = Join-Path $CmdsDir "$($c.Name).md"
  Set-Content -LiteralPath $out -Value $body -Encoding utf8 -NoNewline
  $genFiles += $out
}

Set-ManifestHarness -Target $TargetPath -Harness 'claude' -Files $genFiles
Write-Host "claude: $($genFiles.Count) files -> $TargetPath\.claude"
