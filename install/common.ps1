param()

<#
  install/common.ps1 — shared generation primitives for every harness installer
  (install/claude.ps1, grok.ps1, codex.ps1, opencode.ps1, vscode.ps1).

  Get-RoleMeta is the single source of truth for model tier / effort / permission
  metadata across all five harnesses (D4/D14, plan.v3.md section 1.4a). Its output
  schema is FROZEN as of wave-1's merge: exactly these seven keys, no more, no
  fewer —
      tier, effortLevel, capabilityIntent, pathPolicy, claudeColor, claudeMaxTurns, opencodeTaskPolicy
  Adding, removing, or renaming a key is a schema amendment, not a sibling edit:
  it goes through the orchestrator (never a wave's own builder) via the amendment
  protocol in plan.v3.md section 1.4a, which also updates the frozen key list
  below and in install/common.tests.ps1's executable frozen-key-list test (I25).

  `verify-sync` (Makefile target, install/verify-sync.ps1) is expected to report
  DRIFT for the entire span between task 1.1 and task 7.6a/7.6b landing — that is
  by design (the generator is meant to diverge from already-installed harnesses
  mid-rollout). No wave 2-6 may treat a non-zero verify-sync exit as a wave-level
  gate; it is a wave-7-only gate.
#>

function Get-AgentFiles {
  param([string]$Repo)
  $d = Join-Path $Repo 'agents'
  if (-not (Test-Path $d)) { return @() }
  Get-ChildItem -LiteralPath $d -Filter *.md | ForEach-Object {
    [pscustomobject]@{ Name = $_.BaseName; Path = $_.FullName }
  }
}

function Get-CommandFiles {
  param([string]$Repo)
  $d = Join-Path $Repo 'commands'
  if (-not (Test-Path $d)) { return @() }
  Get-ChildItem -LiteralPath $d -Filter *.md | ForEach-Object {
    [pscustomobject]@{ Name = $_.BaseName; Path = $_.FullName }
  }
}

function Get-AgentDescription {
  param([string]$Path)
  $lines = Get-Content -LiteralPath $Path
  $inPurpose = $false
  foreach ($l in $lines) {
    if ($l -match '^##\s+Purpose') { $inPurpose = $true; continue }
    if ($inPurpose) {
      $t = $l.Trim()
      if ($t) { return $t }
    }
  }
  foreach ($l in $lines) {
    if ($l -match '^#\s+(.+)') { return $matches[1].Trim() }
  }
  return (Split-Path $Path -Leaf)
}

function Get-CommandAgent {
  param([string]$Path)
  $c = Get-Content -Raw -LiteralPath $Path
  if ($c -match 'Use\s+`agents/([^`/]+)\.md`') { return $matches[1] }
  return $null
}

function Get-DisplayAgentName {
  param([string]$Name)
  if ([string]::IsNullOrWhiteSpace($Name)) { return 'agent' }
  if ($Name.Length -le 2) { return $Name.ToUpper() }
  return $Name.Substring(0, 1).ToUpper() + $Name.Substring(1)
}

$script:RoleMetaFrozenKeys = @('tier', 'effortLevel', 'capabilityIntent', 'pathPolicy', 'claudeColor', 'claudeMaxTurns', 'opencodeTaskPolicy')

function Get-EffortLevelForTier {
  param([string]$Tier)
  # Single derivation function (D4) — effort is never hand-picked per role;
  # it is always a pure function of tier.
  switch ($Tier) {
    'Highest' { return 'max' }
    'High'    { return 'high' }
    'Mid'     { return 'medium' }
    default   { throw "Get-EffortLevelForTier: unknown tier '$Tier' (expected Highest|High|Mid)" }
  }
}

function Get-RoleMeta {
  [CmdletBinding()]  # enables -WarningVariable for W1-N01's silent-fallthrough test
  param([string]$Name)
  # tier / capabilityIntent / pathPolicy / opencodeTaskPolicy: frozen per the
  # patched tables in README.md "Model tiers" and agents/orchestrator.md "Model
  # tier map" (task 1.0b), and the full field spec in plan.v3.md section 1.4a.
  $table = @{
    orchestrator = @{ tier = 'Highest'; capabilityIntent = 'dispatch';        pathPolicy = 'unrestricted';    opencodeTaskPolicy = 'orchestrator' }
    planner      = @{ tier = 'Highest'; capabilityIntent = 'shellReadOnly';   pathPolicy = 'unrestricted';    opencodeTaskPolicy = 'leaf' }
    sensei       = @{ tier = 'Highest'; capabilityIntent = 'noRepoAccess';    pathPolicy = 'unrestricted';    opencodeTaskPolicy = 'leaf' }
    reviewer     = @{ tier = 'High';    capabilityIntent = 'shellReadOnly';   pathPolicy = 'unrestricted';    opencodeTaskPolicy = 'leaf' }
    qa           = @{ tier = 'High';    capabilityIntent = 'shellReadOnly';   pathPolicy = 'noProductSource'; opencodeTaskPolicy = 'leaf' }
    refiner      = @{ tier = 'High';    capabilityIntent = 'noRepoAccess';    pathPolicy = 'unrestricted';    opencodeTaskPolicy = 'leaf' }
    advisor      = @{ tier = 'Mid';     capabilityIntent = 'docsReadOnly';    pathPolicy = 'unrestricted';    opencodeTaskPolicy = 'leaf' }
    builder      = @{ tier = 'Mid';     capabilityIntent = 'shellEdit';       pathPolicy = 'unrestricted';    opencodeTaskPolicy = 'leaf' }
    curator      = @{ tier = 'Mid';     capabilityIntent = 'curatorReadOnly'; pathPolicy = 'unrestricted';    opencodeTaskPolicy = 'leaf' }
  }
  if ($table.ContainsKey($Name)) {
    $row = $table[$Name]
  }
  else {
    Write-Warning "Get-RoleMeta: unknown role '$Name' — no frozen row for it; returning a conservative default (Mid tier, noRepoAccess, unrestricted path, leaf task policy). Add a real row (via the amendment protocol) before shipping a 10th role."
    $row = @{ tier = 'Mid'; capabilityIntent = 'noRepoAccess'; pathPolicy = 'unrestricted'; opencodeTaskPolicy = 'leaf' }
  }
  # claudeColor / claudeMaxTurns: schema slots only. Wave-1 owns the frozen key
  # set; wave-2 (task 2.7) assigns the real per-role color palette and the
  # sensei/refiner maxTurns runaway guard once Claude frontmatter generation
  # consumes them. Left $null here rather than guessed (D5 — no false precision).
  return [ordered]@{
    tier               = $row.tier
    effortLevel        = Get-EffortLevelForTier -Tier $row.tier
    capabilityIntent   = $row.capabilityIntent
    pathPolicy         = $row.pathPolicy
    claudeColor        = $null
    claudeMaxTurns     = $null
    opencodeTaskPolicy = $row.opencodeTaskPolicy
  }
}

function Get-OpenCodeAgentMeta {
  param([string]$Name)
  $table = @{
    refiner      = @{ mode = 'subagent'; permission = [ordered]@{ read = 'deny'; edit = 'deny'; bash = 'deny'; websearch = 'deny'; webfetch = 'deny' } }
    planner      = @{ mode = 'primary';  permission = [ordered]@{ edit = 'deny'; bash = 'ask' } }
    builder      = @{ mode = 'primary';  permission = [ordered]@{ edit = 'allow'; bash = 'allow' } }
    reviewer     = @{ mode = 'subagent'; permission = [ordered]@{ edit = 'deny'; bash = 'ask' } }
    # Stage 6 black-box QA: docs must be readable (no read deny); product write denied; bash for CLI/app.
    # Product-source path deny is policy in agents/qa.md when harness cannot express path-class deny.
    qa           = @{ mode = 'subagent'; permission = [ordered]@{ edit = 'deny'; bash = 'allow' } }
    curator      = @{ mode = 'subagent'; permission = [ordered]@{ edit = 'deny'; bash = 'ask' } }
    sensei       = @{ mode = 'subagent'; permission = [ordered]@{ read = 'deny'; edit = 'deny'; bash = 'deny'; websearch = 'deny'; webfetch = 'deny' } }
    # Docs-only policy (agents/advisor.md): may read; no edit/bash/web exploration of implementation.
    advisor      = @{ mode = 'subagent'; permission = [ordered]@{ edit = 'deny'; bash = 'deny'; websearch = 'deny'; webfetch = 'deny' } }
    # Orchestrator may write E2E session artifacts (plans, retro) and spawn specialists.
    orchestrator = @{ mode = 'primary';  permission = [ordered]@{ edit = 'allow'; bash = 'ask'; task = 'allow' } }
  }
  if ($table.ContainsKey($Name)) { return $table[$Name] }
  return @{ mode = 'subagent'; permission = [ordered]@{ edit = 'deny'; bash = 'ask' } }
}

function New-GeneratedComment {
  param([string]$Source)
  $t = '<!-- generated by `make sync`; source: {SRC}. Do not edit here; edit the source and re-run: make sync -->'
  return ($t -replace '\{SRC\}', $Source)
}

function Resolve-Target {
  param([string]$Target)
  if ([string]::IsNullOrWhiteSpace($Target) -or $Target -eq '.') { return (Get-Location).Path }
  $p = Resolve-Path -LiteralPath $Target -ErrorAction SilentlyContinue
  if (-not $p) { New-Item -ItemType Directory -Path $Target -Force | Out-Null; $p = Resolve-Path -LiteralPath $Target }
  return $p.Path
}

function Normalize-Path {
  param([string]$Path)
  return ($Path.TrimEnd('\', '/'))
}

function Get-ManifestPath {
  param([string]$Target)
  return (Join-Path $Target '.agents-sync\manifest.json')
}

function Read-Manifest {
  param([string]$Target)
  $mp = Get-ManifestPath -Target $Target
  if (-not (Test-Path $mp)) { return @() }
  $data = Get-Content -Raw -LiteralPath $mp | ConvertFrom-Json
  if (-not $data) { return @() }
  return @($data)
}

function Write-Manifest {
  param([string]$Target, $Entries)
  $dir = Join-Path $Target '.agents-sync'
  New-Item -ItemType Directory -Path $dir -Force | Out-Null
  $mp = Join-Path $dir 'manifest.json'
  ,$Entries | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $mp -Encoding utf8
}

function Set-ManifestHarness {
  param([string]$Target, [string]$Harness, [string[]]$Files)
  $rest = @((Read-Manifest -Target $Target) | Where-Object { $_.harness -ne $Harness })
  $rest += [pscustomobject]@{ harness = $Harness; files = @($Files) }
  Write-Manifest -Target $Target -Entries $rest
}

function Remove-EmptyParents {
  param([string]$Path, [string]$StopRoot)
  $stop = Normalize-Path -Path $StopRoot
  $p = Split-Path $Path -Parent
  while ($p) {
    $cur = Normalize-Path -Path $p
    if ($stop -and $cur -eq $stop) { break }
    if (-not (Test-Path -LiteralPath $p)) { break }
    $items = Get-ChildItem -LiteralPath $p -Force -ErrorAction SilentlyContinue
    if (($items | Measure-Object).Count -eq 0) {
      Remove-Item -LiteralPath $p -Force
      $p = Split-Path $p -Parent
    }
    else { break }
  }
}

function Clear-ManifestHarness {
  param([string]$Target, [string]$Harness)
  $all = @(Read-Manifest -Target $Target)
  $entry = $all | Where-Object { $_.harness -eq $Harness }
  $rest = @($all | Where-Object { $_.harness -ne $Harness })
  if ($entry) {
    foreach ($f in @($entry.files)) {
      if (Test-Path -LiteralPath $f) {
        Remove-Item -LiteralPath $f -Force
        Remove-EmptyParents -Path $f -StopRoot $Target
      }
    }
  }
  if (($rest | Measure-Object).Count -eq 0) {
    $mp = Get-ManifestPath -Target $Target
    if (Test-Path $mp) {
      Remove-Item -LiteralPath $mp -Force
      Remove-EmptyParents -Path $mp -StopRoot $Target
    }
  }
  else {
    Write-Manifest -Target $Target -Entries $rest
  }
}

function Get-RepoRoot {
  return (Split-Path $PSScriptRoot -Parent)
}

function Get-CommandTask {
  param([string]$Path)
  $content = Get-Content -Raw -LiteralPath $Path
  $match = [regex]::Match($content, '(?ms)Prompt:\s*```text\s*\r?\n(.*?)\r?\n```')
  if ($match.Success) { return $match.Groups[1].Value.Trim() }
  return $content.Trim()
}

function Get-CommandArgumentHint {
  param([string]$Path)
  # Returns $null when absent (I4) — callers must skip the frontmatter key
  # entirely rather than emit an empty `argument-hint:` line.
  $content = Get-Content -Raw -LiteralPath $Path
  $match = [regex]::Match($content, '(?m)^Argument-Hint:\s*(.+)$')
  if ($match.Success) { return $match.Groups[1].Value.Trim() }
  return $null
}

$script:SkillDescriptionMaxLength = 1024

function Get-CommandSkillDescription {
  [CmdletBinding()]  # enables -WarningVariable for W1-E01's truncation-warning test
  param([string]$Path, [string]$CommandName, [string]$AgentName)
  $content = Get-Content -Raw -LiteralPath $Path
  $skillDescMatch = [regex]::Match($content, '(?m)^Skill-Description:\s*(.+)$')
  if ($skillDescMatch.Success) {
    $desc = $skillDescMatch.Groups[1].Value.Trim()
  }
  else {
    # Fallback (F-13): lead with what the skill does, not the mechanism, and
    # never embed a harness-specific invocation sigil (e.g. Codex's `$name`).
    # Command names follow a `<verb>-this` convention, so the verb itself
    # doubles as the trigger word — no task-specific text is available here.
    $display = Get-DisplayAgentName -Name $AgentName
    $verb = (($CommandName -replace '-this$', '') -replace '-', ' ').Trim()
    if (-not $verb) { $verb = $CommandName }
    $verbCap = if ($verb.Length -le 3) { $verb.ToUpper() } else { $verb.Substring(0, 1).ToUpper() + $verb.Substring(1) }
    $desc = "$verbCap the current request as the $display specialist. Use when the user asks to $verb, wants the $display role, or runs /$CommandName."
  }
  if ($desc.Length -gt $script:SkillDescriptionMaxLength) {
    $truncated = $desc.Substring(0, $script:SkillDescriptionMaxLength)
    $lastSpace = $truncated.LastIndexOf(' ')
    if ($lastSpace -gt 0) { $truncated = $truncated.Substring(0, $lastSpace) }
    Write-Warning "Get-CommandSkillDescription: '$CommandName' description is $($desc.Length) chars (max $($script:SkillDescriptionMaxLength)); truncated at a word boundary to $($truncated.Length) chars."
    $desc = $truncated
  }
  return $desc
}

function New-PlaybookSkillMarkdown {
  param(
    [string]$CommandName,
    [string]$AgentName,
    [string]$Task,
    [string]$SkillDescription,
    [string]$SyncCommand,
    [string]$Repo,
    [switch]$Global,
    [System.Collections.Specialized.OrderedDictionary]$ExtraFrontmatter
  )
  $generated = "<!-- generated by ``$SyncCommand``; source: commands/$CommandName.md. Do not edit here; edit the source and re-run ``$SyncCommand`` -->"

  # Roles are named, never located by this build machine's absolute repo path
  # (F-2/I1): a personal/-Global install isn't tied to one repo checkout and a
  # baked path breaks silently if the repo moves. -Global installs get pure
  # name-based guidance; in-repo installs may additionally point at a
  # repo-relative `agents/<role>.md` fallback for harnesses with no named-agent
  # concept. {0} is substituted with the role name by each call site below.
  $roleFallbackHint = if ($Global) {
    "ask which project's canonical ``agents/{0}.md`` to load (a personal/global install is not tied to one specific repo checkout)"
  }
  else {
    "load the canonical role definition at ``agents/{0}.md`` (repo-relative) in this project"
  }

  if ($CommandName -eq 'e2e' -or $CommandName -eq 'e2e-resume') {
    # Main session IS the orchestrator — never nest another orchestrator (context loss).
    # Applies to both the fresh pipeline (/e2e) and re-entry into a stopped session (/e2e-resume):
    # both run in the main conversation under the same identity rule.
    $orchestratorHint = ($roleFallbackHint -f 'orchestrator')
    $skillBody = @"
# /$CommandName — main agent is the Orchestrator

**YOU** run this pipeline in the **current** conversation. Do **not** spawn an ``orchestrator`` subagent, do not fork a second E2E brain, and do not re-invoke ``/e2e`` or ``/e2e-resume``.

1. Load and follow the orchestrator playbook yourself: role ``orchestrator`` — if this harness has no named-agent concept, $orchestratorHint.
2. Execute the task guidance below as that Orchestrator (full E2E pipeline, resuming from the reconstructed state when invoked as /e2e-resume).
3. Spawn **only** leaf specialists when needed: ``refiner``, ``planner``, ``sensei``, ``advisor``, ``builder``, ``reviewer``, ``curator``, ``qa`` — same name-based lookup rule as above, substituting each specialist's name.
4. Preserve the same Sensei/Advisor/Reviewer threads across review iterations (resume; do not reset).
5. Apply Correctness over delivery convenience; you write plan revisions after v0 yourself.

## Task guidance

$Task
"@
  }
  else {
    $agentHint = ($roleFallbackHint -f $AgentName)
    $skillBody = @"
Spawn the ``$AgentName`` custom agent / subagent to handle the current request when the harness supports named agents.
Give it the relevant conversation and repository context plus this task guidance:

$Task

If the harness cannot spawn a named ``$AgentName`` agent, **you** must $agentHint and execute that role yourself.

When you are already acting as orchestrator (e.g. mid-``/e2e``), do **not** spawn another orchestrator — only leaf specialists (refiner, planner, sensei, advisor, builder, reviewer, curator, qa). Preserve the same Sensei/Advisor/Reviewer threads across review iterations (resume; do not reset). Wait for each specialist step to finish before applying its output; do not redo specialist work with weaker judgment.

Apply Correctness over delivery convenience when the target project defines it: complete and durable work over velocity shortcuts.
"@
  }

  # D2: name/description always first; -ExtraFrontmatter (Claude's argument-hint,
  # disable-model-invocation, etc. — wired up starting wave-2) appends after, in
  # caller-supplied order. Install-PlaybookSkillsTo enforces the agentskills.io
  # six-field ceiling for every non-Claude caller before this function ever runs.
  $fmLines = @('---', "name: $CommandName", "description: $SkillDescription")
  if ($ExtraFrontmatter) {
    foreach ($k in $ExtraFrontmatter.Keys) { $fmLines += "$($k): $($ExtraFrontmatter[$k])" }
  }
  $fmLines += '---'

  return ($fmLines -join "`n") + "`n`n" +
         $generated + "`n`n" +
         $skillBody + "`n"
}

function Get-ClaudeAgentFrontmatter {
  param([string]$Name, [string]$Description)
  # tools / model tuned for Claude Code subagent frontmatter
  $meta = switch ($Name) {
    'orchestrator' {
      @{
        tools = 'Agent, Read, Write, Edit, Grep, Glob, Bash, Skill'
        model = 'opus'
        permissionMode = 'acceptEdits'
      }
    }
    'planner' {
      @{
        tools = 'Read, Grep, Glob, Bash'
        model = 'opus'
        permissionMode = 'plan'
      }
    }
    'sensei' {
      @{
        tools = ''  # no tools — judgment from provided context only
        model = 'opus'
        disallowedTools = 'Read, Write, Edit, Bash, Grep, Glob, WebFetch, WebSearch'
      }
    }
    'advisor' {
      @{
        # Read/Grep/Glob for documentation & contracts only — policy in agents/advisor.md forbids source.
        tools = 'Read, Grep, Glob'
        model = 'sonnet'
        # Block write/shell so Advisor cannot "just check" by running or editing code.
        disallowedTools = 'Write, Edit, Bash, NotebookEdit, WebFetch, WebSearch'
      }
    }
    'builder' {
      @{
        tools = 'Read, Write, Edit, Grep, Glob, Bash'
        model = 'sonnet'
        permissionMode = 'acceptEdits'
        # Note: long/integration tests are policy-forbidden in builder.md (orchestrator runs them).
      }
    }
    'reviewer' {
      @{
        tools = 'Read, Grep, Glob, Bash'
        model = 'sonnet'
      }
    }
    'refiner' {
      @{
        tools = ''
        model = 'sonnet'
        disallowedTools = 'Read, Write, Edit, Bash, Grep, Glob, WebFetch, WebSearch'
      }
    }
    'qa' {
      @{
        # Stage 6: may read docs + run app; must not write product or notebooks.
        # Product-source oracle forbid is policy in agents/qa.md (degraded detect if needed).
        tools = 'Bash, Read, Grep, Glob'
        model = 'sonnet'
        disallowedTools = 'Write, Edit, NotebookEdit'
      }
    }
    'curator' {
      @{
        tools = 'Read, Grep, Glob'
        model = 'sonnet'
      }
    }
    default {
      @{
        tools = 'Read, Grep, Glob, Bash'
        model = 'inherit'
      }
    }
  }
  $lines = @(
    '---'
    "name: $Name"
    "description: $($Description -replace '"', '''')"
  )
  if ($meta.tools) { $lines += "tools: $($meta.tools)" }
  if ($meta.disallowedTools) { $lines += "disallowedTools: $($meta.disallowedTools)" }
  if ($meta.model) { $lines += "model: $($meta.model)" }
  if ($meta.permissionMode) { $lines += "permissionMode: $($meta.permissionMode)" }
  $lines += '---'
  return ($lines -join "`n")
}

$script:AgentSkillsIoFrontmatterFields = @('name', 'description', 'license', 'compatibility', 'metadata', 'allowed-tools')

function Get-DefaultSkillFrontmatter {
  # D2 per-harness default. Claude may grow extra keys (argument-hint,
  # disable-model-invocation, ...) starting wave-2 task 2.5; every other harness
  # is pinned to the agentskills.io six-field subset so packaging/upload never
  # hard-errors on an unknown key. Wave-1 ships no per-role extra values yet —
  # {} is already a valid subset of the six-field spec for every harness.
  param([string]$HarnessLabel)
  return [ordered]@{}
}

function Install-PlaybookSkillsTo {
  param(
    [string]$SkillsRoot,
    [string]$Repo,
    [string]$SyncCommand,
    [string]$HarnessLabel,
    [switch]$Global,
    [System.Collections.Specialized.OrderedDictionary]$ExtraFrontmatter
  )
  if ($null -eq $ExtraFrontmatter) { $ExtraFrontmatter = Get-DefaultSkillFrontmatter -HarnessLabel $HarnessLabel }
  if ($HarnessLabel -ne 'claude') {
    foreach ($k in $ExtraFrontmatter.Keys) {
      if ($script:AgentSkillsIoFrontmatterFields -notcontains $k) {
        throw "Install-PlaybookSkillsTo: '$HarnessLabel' extra frontmatter key '$k' is outside the agentskills.io six-field spec ($($script:AgentSkillsIoFrontmatterFields -join ', ')) — see plan.v3.md D2/I3."
      }
    }
  }
  New-Item -ItemType Directory -Path $SkillsRoot -Force | Out-Null
  $genFiles = @()
  foreach ($c in (Get-CommandFiles -Repo $Repo)) {
    $agent = Get-CommandAgent -Path $c.Path
    if (-not $agent) {
      Write-Warning "$HarnessLabel`: skipping command '$($c.Name)' (no agent reference)"
      continue
    }
    $task = Get-CommandTask -Path $c.Path
    $skillDesc = Get-CommandSkillDescription -Path $c.Path -CommandName $c.Name -AgentName $agent
    $skill = New-PlaybookSkillMarkdown `
      -CommandName $c.Name `
      -AgentName $agent `
      -Task $task `
      -SkillDescription $skillDesc `
      -SyncCommand $SyncCommand `
      -Repo $Repo `
      -Global:$Global `
      -ExtraFrontmatter $ExtraFrontmatter

    $skillDir = Join-Path $SkillsRoot $c.Name
    New-Item -ItemType Directory -Path $skillDir -Force | Out-Null
    $skillOut = Join-Path $skillDir 'SKILL.md'
    Set-Content -LiteralPath $skillOut -Value $skill -Encoding utf8 -NoNewline
    $genFiles += $skillOut
  }
  return $genFiles
}
