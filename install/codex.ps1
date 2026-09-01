param(
  [string]$Target = '.',
  [switch]$Global
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\common.ps1"
$Repo = Get-RepoRoot
$TargetPath = if ($Global) {
  [Environment]::GetFolderPath('UserProfile')
}
else {
  Resolve-Target -Target $Target
}

# Codex CLI native surfaces (verified against developers.openai.com/codex):
#   - Custom agents: TOML files in .codex/agents/*.toml
#     (name, description, developer_instructions, model, model_reasoning_effort;
#     optional sandbox_mode). 'default'/'worker'/'explorer' are Codex built-in
#     agent names and are rejected below if an agents/*.md file matches (3.2).
#   - Project guidance: AGENTS.md at repo root (NOT copied here; the target
#     project should own its own AGENTS.md).
#   - Custom prompts: Markdown files in ~/.codex/prompts/*.md. This legacy,
#     global-only, DEPRECATED surface exposes commands as /prompts:<name> (F-12).
#     It is installed only with -Global because Codex does not discover
#     project-scoped prompts. Kept one more cycle; removal is an open decision.

$AgentsDir = Join-Path $TargetPath '.codex\agents'
New-Item -ItemType Directory -Path $AgentsDir -Force | Out-Null

function Get-CodexSandboxMode {
  param([string]$Name)
  switch ($Name) {
    'builder'      { return 'workspace-write' }  # edits the product tree; that is the role's job
    # Stage 6 black-box QA (agents/qa.md) writes session evidence only — qa/plan.md,
    # qa/findings*.md, qa/probe.md, and screenshots/logs under
    # .agents/workspace/tmp/e2e/<slug>/qa/** plus an evidence temp dir — never
    # product source. Codex's custom-agent TOML has no path-scoped write
    # allowlist field (only sandbox_mode/model/model_reasoning_effort/
    # nickname_candidates/mcp_servers/skills.config), so narrowing to
    # read-only would leave QA unable to persist its own required Stage 6
    # artifacts at all. Product-tree write is denied at the policy layer
    # instead (agents/qa.md hard MUST NOT edit product trees), with
    # BLOCKED_ENV as the documented fallback if a stricter, path-scoped
    # Codex sandbox becomes available later — see "Stage 6 qa eligibility"
    # in adapters/codex.md (task 3.6 decision).
    'qa'           { return 'workspace-write' }
    'orchestrator' { return 'workspace-write' }  # E2E session artifacts (plan.vN, retro)
    default        { return 'read-only' }
  }
}

function Escape-TomlBasicString {
  param([string]$s)
  return ($s -replace '\\','\\' -replace '"','\"')
}

function ConvertTo-TomlDeveloperInstructionsBlock {
  param([string]$Content)
  # Round-trip fidelity (task 3.5, fixes PP-E): developer_instructions must
  # parse back to $Content byte-for-byte, so no separator newline can be
  # inserted before the closing delimiter. TOML literal strings ('''...''')
  # need zero escaping and are preferred when safe, but two conditions make
  # them unsafe here:
  #   - a ''' run inside $Content would prematurely close the string
  #     (W3-E01), and
  #   - $Content ending in a trailing ' would merge with the closing ''' into
  #     an ambiguous/invalid run of quote characters.
  # Fall back to a fully-escaped basic multi-line string ("""...""") in
  # either case; escaping removes both hazards (no agents/*.md currently
  # triggers this fallback; verified at task 3.5).
  $needsBasicString = ($Content -match "'''") -or $Content.EndsWith("'")
  if (-not $needsBasicString) {
    return "'''`n$Content" + "'''"
  }
  $escaped = Escape-TomlBasicString -s $Content
  return '"""' + "`n$escaped" + '"""'
}

$genFiles = @()
$agentFiles = @(Get-AgentFiles -Repo $Repo)

# Codex ships 'default', 'worker', 'explorer' as built-in agent names (task 3.2).
# A repo agents/<name>.md matching one would collide with a Codex-native agent
# at .codex/agents/<name>.toml; fail before writing anything rather than
# silently shadow a built-in.
$script:ReservedCodexAgentNames = @('default', 'worker', 'explorer')
$reservedCollisions = @($agentFiles | Where-Object { $script:ReservedCodexAgentNames -contains $_.Name })
if ($reservedCollisions.Count -gt 0) {
  $collidingNames = ($reservedCollisions | ForEach-Object { $_.Name }) -join ', '
  throw "codex: agents/*.md file(s) named [$collidingNames] collide with Codex built-in agent name(s) ($($script:ReservedCodexAgentNames -join ', ')). Rename the source file(s) before syncing."
}

$syncCommand = if ($Global) { 'make sync-codex-global' } else { 'make sync-codex TARGET=<dir>' }
foreach ($a in $agentFiles) {
  $content = (Get-Content -Raw -LiteralPath $a.Path).TrimEnd()
  $desc = Get-AgentDescription -Path $a.Path
  $sandbox = Get-CodexSandboxMode -Name $a.Name
  $descEsc = Escape-TomlBasicString -s $desc
  # F-6/task 3.1: reasoning effort is sourced from Get-RoleMeta's effortLevel
  # (single derivation from tier, D4) — never a per-role hand-picked value.
  $reasoningEffort = (Get-RoleMeta -Name $a.Name).effortLevel
  $instructionsBlock = ConvertTo-TomlDeveloperInstructionsBlock -Content $content

  $header = "# generated by '$syncCommand'; source: agents/$($a.Name).md" + "`n" +
            "# Do not edit here; edit agents/$($a.Name).md and re-run: $syncCommand" + "`n" +
            "# model left unset: no per-harness model ID pinned yet (plan.v3.md section 4, open decision 6)."

  $toml = $header + "`n`n" +
          "name = `"$($a.Name)`"" + "`n" +
          "description = `"$descEsc`"" + "`n" +
          "model = `"`"" + "`n" +
          "model_reasoning_effort = `"$reasoningEffort`"" + "`n" +
          "sandbox_mode = `"$sandbox`"" + "`n" +
          "developer_instructions = " + $instructionsBlock + "`n"

  $out = Join-Path $AgentsDir "$($a.Name).toml"
  Set-Content -LiteralPath $out -Value $toml -Encoding utf8 -NoNewline
  $genFiles += $out
}

if ($Global) {
  $PromptsDir = Join-Path $TargetPath '.codex\prompts'
  $SkillsRoot = Join-Path $TargetPath '.agents\skills'
  New-Item -ItemType Directory -Path $PromptsDir -Force | Out-Null
  New-Item -ItemType Directory -Path $SkillsRoot -Force | Out-Null

  # F-12/task 3.3: Codex deprecated custom prompts in favor of skills. Kept for
  # one more cycle; removal is an open decision for Juan, not decided here.
  $deprecationNote = '> **Deprecated:** this custom-prompt surface (`~/.codex/prompts/*.md`, invoked as `/prompts:<name>`) is deprecated by Codex in favor of skills; kept for one more cycle. Removal is an open decision for Juan — see `adapters/codex.md`.'

  foreach ($c in (Get-CommandFiles -Repo $Repo)) {
    $agent = Get-CommandAgent -Path $c.Path
    if (-not $agent) {
      Write-Warning "codex: skipping command '$($c.Name)' because it does not reference an agent"
      continue
    }

    $task = Get-CommandTask -Path $c.Path
    $skillDesc = Get-CommandSkillDescription -Path $c.Path -CommandName $c.Name -AgentName $agent
    $displayName = Get-DisplayAgentName -Name $agent
    $generated = "<!-- generated by ``$syncCommand``; source: commands/$($c.Name).md. Do not edit here; edit the source and re-run ``$syncCommand`` -->"

    if ($c.Name -eq 'e2e' -or $c.Name -eq 'e2e-resume') {
      # Main session IS the orchestrator for these two commands — never spawn a nested
      # orchestrator here either (same Identity rule as the skill-writer's self-run branch).
      $prompt = "---`n" +
                "description: Run this pipeline yourself in the current conversation (do not spawn $displayName)`n" +
                "---`n`n" +
                $generated + "`n`n" +
                $deprecationNote + "`n`n" +
                "**YOU** run this pipeline in the **current** conversation. Do **not** spawn an ``$agent`` subagent, do not fork a second E2E brain, and do not re-invoke ``/e2e`` or ``/e2e-resume``.`n`n" +
                $task + "`n"
    }
    else {
      $prompt = "---`n" +
                "description: Run the $displayName custom agent for the current request`n" +
                "---`n`n" +
                $generated + "`n`n" +
                $deprecationNote + "`n`n" +
                "Spawn the ``$agent`` custom agent to handle the current request.`n" +
                "Give it the relevant conversation and repository context plus this task guidance:`n`n" +
                $task + "`n`n" +
                "Wait for the agent to finish, then return its result without redoing its work.`n"
    }

    $out = Join-Path $PromptsDir "$($c.Name).md"
    Set-Content -LiteralPath $out -Value $prompt -Encoding utf8 -NoNewline
    $genFiles += $out

    $skillMention = '$' + $c.Name
    $displayCommand = (Get-Culture).TextInfo.ToTitleCase(($c.Name -replace '-', ' '))
    $shortDesc = $skillDesc
    if ($shortDesc.Length -gt 180) { $shortDesc = $shortDesc.Substring(0, 177) + '...' }

    $skillDir = Join-Path $SkillsRoot $c.Name
    $skillAgentDir = Join-Path $skillDir 'agents'
    New-Item -ItemType Directory -Path $skillAgentDir -Force | Out-Null
    $openaiYaml = "interface:`n" +
                  "  display_name: `"$displayCommand`"`n" +
                  "  short_description: `"$($shortDesc -replace '"','\"')`"`n" +
                  "  default_prompt: `"Use $skillMention to run the $($c.Name) workflow.`"`n"
    $metadataOut = Join-Path $skillAgentDir 'openai.yaml'
    Set-Content -LiteralPath $metadataOut -Value $openaiYaml -Encoding utf8 -NoNewline
    $genFiles += $metadataOut
  }

  $skillFiles = Install-PlaybookSkillsTo `
    -SkillsRoot $SkillsRoot `
    -Repo $Repo `
    -SyncCommand $syncCommand `
    -HarnessLabel 'codex' `
    -Global
  $genFiles += $skillFiles
}

Set-ManifestHarness -Target $TargetPath -Harness 'codex' -Files $genFiles
Write-Host "codex: $($agentFiles.Count) custom agents -> $AgentsDir"
if ($Global) {
  Write-Host "codex: custom prompts -> $PromptsDir (invoke as /prompts:<name>; restart Codex first)"
  Write-Host "codex: personal skills -> $SkillsRoot (invoke as `$<name> or select from the / menu)"
}
else {
  Write-Host "codex: custom prompts are global-only; run this installer with -Global to install them."
}
Write-Host "codex: AGENTS.md not copied; the target project owns its own."
