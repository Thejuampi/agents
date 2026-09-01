param(
  [string]$Target = '.',
  [switch]$Global
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\common.ps1"
$Repo = Get-RepoRoot

# Grok Build / Grok TUI skills:
#   Personal:  ~/.grok/skills/<name>/SKILL.md
#   Project:   <target>/.grok/skills/<name>/SKILL.md
# Same SKILL.md shape as Claude / Codex agent skills (YAML frontmatter + body).

if ($Global) {
  $SkillsRoot = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.grok\skills'
  $syncCommand = 'make sync-grok-global'
  $manifestTarget = Join-Path ([Environment]::GetFolderPath('UserProfile')) '.grok'
}
else {
  $TargetPath = Resolve-Target -Target $Target
  $SkillsRoot = Join-Path $TargetPath '.grok\skills'
  $syncCommand = 'make sync-grok TARGET=<dir>'
  $manifestTarget = $TargetPath
}

# 5.5 (F-9): no `~/.grok/agents/` projection is shipped. Grok's real subagent
# location is `.grok/agents/` / `~/.grok/agents/`, but its file format is not
# documented anywhere this session could verify (docs.x.ai has no agent-file
# schema page as of 2026-08-06 — see adapters/grok.md and plan.v3.md D7).
# Guessing a format is explicitly forbidden, so the prior `_playbook-agents`
# reference dump (never loaded by Grok anyway) is removed rather than replaced
# with an unverified guess. Grok's documented Claude Code compatibility means
# `agents/*.md` is already readable via `~/.claude/agents/` with zero extra
# projection (adapters/grok.md "reads for free" table).

# 5.5/W5-R02 upgrade path: purge any files a prior grok.ps1 run recorded for
# this harness (including a pre-5.5 install's now-removed `_playbook-agents`
# dump) before writing the fresh manifest, so stale generated files don't
# outlive the code that produced them.
Clear-ManifestHarness -Target $manifestTarget -Harness 'grok'

$genFiles = Install-PlaybookSkillsTo `
  -SkillsRoot $SkillsRoot `
  -Repo $Repo `
  -SyncCommand $syncCommand `
  -HarnessLabel 'grok' `
  -Global:$Global

Set-ManifestHarness -Target $manifestTarget -Harness 'grok' -Files $genFiles
$cmdCount = @(Get-CommandFiles -Repo $Repo).Count
Write-Host "grok: $cmdCount skills -> $SkillsRoot"
Write-Host "grok: role definitions read via Claude Code compatibility (~/.claude/agents/) or agents/*.md fallback in skill bodies; no _playbook-agents dump (see adapters/grok.md)."
if ($Global) {
  Write-Host "grok: personal install complete. Skills appear as /e2e, /plan-this, etc. after reload."
}
