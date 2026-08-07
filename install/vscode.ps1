param([string]$Target = '.')
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\common.ps1"
$Repo = Get-RepoRoot
$TargetPath = Resolve-Target -Target $Target

<#
  install/vscode.ps1 — VS Code / GitHub Copilot projector (plan.v3.md wave-4).

  Generation approach (post-D6/F-5): roles project to native VS Code **custom
  agents** (`.github/agents/<role>.agent.md`), not to 9 always-on
  `applyTo: "**"` instruction files. The old approach injected the full text of
  all 9 `agents/*.md` (~123 KB) into every single Copilot chat request,
  regardless of which role was relevant — VS Code's own guidance is explicit
  that instructions without a narrow `applyTo` are the wrong surface for this.
  Exactly one always-on instructions file survives
  (`agent-playbook.instructions.md`, `applyTo: "**"`), holding only the
  Principles table (extracted live from README.md, single source of truth) —
  budget: I11, < 2 KB total.

  `tools` for the 8 leaf roles is a **pure function** of `Get-RoleMeta`'s
  `(capabilityIntent, pathPolicy)` pair (plan.v3.md section 1.4a) — see
  Get-VSCodeAgentTools below. `orchestrator` is the sole, deliberate exception:
  its `tools`/`agents` grant is hand-authored and fixed, mirroring wave-2's
  Claude carve-out (never derived from `capabilityIntent: dispatch`) — see
  adapters/vscode.md "Orchestrator carve-out".

  Tool/field names verified against code.visualstudio.com/docs/copilot/
  customization/{custom-agents,custom-instructions,prompt-files} and
  code.visualstudio.com/docs/agents/{concepts,run}/tools, retrieved
  2026-08-06/07 (see adapters/vscode.md's citations).
#>

$AgentsDir = Join-Path $TargetPath '.github\agents'
$PromptsDir = Join-Path $TargetPath '.github\prompts'
$InstrDir = Join-Path $TargetPath '.github\instructions'
New-Item -ItemType Directory -Path $AgentsDir -Force | Out-Null
New-Item -ItemType Directory -Path $PromptsDir -Force | Out-Null
New-Item -ItemType Directory -Path $InstrDir -Force | Out-Null

# --- Task 4.1: (capabilityIntent, pathPolicy) -> VS Code `tools` (pure function) ---
# Tool/toolset names are the ones attested in VS Code's own docs (see header):
# 'search/codebase', 'search/usages' (read/search), 'edit' (file edits),
# 'read/terminalLastCommand' + 'terminal' (shell), 'agent' (subagent dispatch —
# withheld from every derived grant; only the orchestrator carve-out and D6's
# handoffs use agent identity, never the raw dispatch tool for a leaf).
function Get-VSCodeAgentTools {
  param([string]$CapabilityIntent, [string]$PathPolicy)
  # PathPolicy is accepted (not silently dropped) for interface symmetry with
  # Get-RoleMeta's pure-function pair, but VS Code has no path-scoped tool
  # primitive — same limitation Claude's generator has (adapters/claude.md
  # "Product-source path deny is policy in agents/qa.md"). Faking a tool-level
  # split here (e.g. denying 'search/codebase' to qa) would cripple qa's
  # genuine need to read docs, for no real containment gain — see
  # adapters/vscode.md's qa note for the honest disclosure instead.
  switch ($CapabilityIntent) {
    'noRepoAccess'    { return @() }
    'docsReadOnly'    { return @('search/codebase', 'search/usages') }
    'curatorReadOnly' { return @('search/codebase', 'search/usages') }
    'shellReadOnly'   { return @('search/codebase', 'search/usages', 'read/terminalLastCommand', 'terminal') }
    'shellEdit'       { return @('search/codebase', 'search/usages', 'edit', 'read/terminalLastCommand', 'terminal') }
    default { throw "Get-VSCodeAgentTools: unsupported capabilityIntent '$CapabilityIntent' ('dispatch' is the orchestrator's hand-authored carve-out, never routed through here — see install/vscode.ps1's `$OrchestratorTools)" }
  }
}

# Model is still a pure function of `tier` (D4) even for the orchestrator —
# only tools/agents are hand-authored there. Mirrors Claude's opus/sonnet split
# (Get-ClaudeAgentFrontmatter): Highest gets the top model class, High and Mid
# share the second tier — same collapse, not an extra invented gradient.
# Model names are taken verbatim from VS Code's own custom-agents doc examples
# (`model: ['Claude Opus 4.5', 'GPT-5.2']` / handoffs.model's paired
# 'Claude Sonnet 4.5 (copilot)' + 'GPT-5 (copilot)') — a prioritized array, not
# a single vendor lock, consistent with README's "one model only... do not
# invent a weaker path" (declared default, not a verified optimum — D5).
function Get-VSCodeModelsForTier {
  param([string]$Tier)
  switch ($Tier) {
    'Highest' { return @('Claude Opus 4.5', 'GPT-5.2') }
    'High'    { return @('Claude Sonnet 4.5', 'GPT-5') }
    'Mid'     { return @('Claude Sonnet 4.5', 'GPT-5') }
    default   { throw "Get-VSCodeModelsForTier: unknown tier '$Tier'" }
  }
}

function ConvertTo-YamlFlowList {
  # Deliberately untyped $Items: PowerShell coerces a $null argument bound to a
  # [string[]] parameter into a one-element array containing an empty string
  # (@('')), not an empty array — silently turning an intended `tools: []`
  # (no tools at all, e.g. sensei/refiner) into `tools: ['']` (one bogus tool
  # name). Caught by generation-output inspection, not a type annotation.
  param($Items)
  $arr = @($Items | Where-Object { $null -ne $_ })
  if ($arr.Count -eq 0) { return '[]' }
  return '[' + (($arr | ForEach-Object { "'$_'" }) -join ', ') + ']'
}

# Task 4.4: stage-chain handoffs (planner -> builder -> reviewer -> qa -> sensei).
# Each edge: label + agent + prompt + send:false (never auto-submit — a human
# or the orchestrator reviews before advancing a stage, matching Stage
# 3/5/6 gates in agents/orchestrator.md).
$script:Handoffs = @{
  planner  = @{ label = 'Start Implementation'; agent = 'builder';  prompt = 'Implement the approved plan wave assigned to you (Independent or Serial per depends_on).' }
  builder  = @{ label = 'Request Review';       agent = 'reviewer'; prompt = 'Review the implementation just completed against the plan and the codebase.' }
  reviewer = @{ label = 'Run Black-box QA';     agent = 'qa';       prompt = 'Run Stage 6 black-box QA against this reviewed revision.' }
  qa       = @{ label = 'Final Sensei Pass';    agent = 'sensei';   prompt = 'Run the Stage 7 final Sensei pass on this QA-certified revision.' }
}

function Get-AgentMarkdown {
  param([string]$Name, [string]$Description, [string]$SourcePath)
  $meta = Get-RoleMeta -Name $Name
  $lines = @('---', "name: $(Get-DisplayAgentName -Name $Name)", "description: $($Description -replace '"', '''')")

  if ($Name -eq 'orchestrator') {
    # Carve-out (plan.v3.md 1.4a, mirrors wave-2's Claude carve-out): hand-authored
    # and fixed, never derived from capabilityIntent='dispatch'. 'agent' (the tool
    # VS Code's own docs say is required for `agents:` to actually dispatch) is
    # deliberately withheld — see adapters/vscode.md for the disclosed tension this
    # creates (agents: present but inert without it, exactly the point).
    $OrchestratorTools = @('search/codebase', 'search/usages', 'edit', 'read/terminalLastCommand', 'terminal')
    $OrchestratorLeaves = @('refiner', 'planner', 'sensei', 'advisor', 'builder', 'reviewer', 'curator', 'qa')
    $lines += "tools: $(ConvertTo-YamlFlowList -Items $OrchestratorTools)"
    $lines += "model: $(ConvertTo-YamlFlowList -Items (Get-VSCodeModelsForTier -Tier $meta.tier))"
    $lines += "agents: $(ConvertTo-YamlFlowList -Items $OrchestratorLeaves)"
    # I13/W4-N04: 'orchestrator' absent from its own agents: list; 'agent' (the
    # dispatch tool) absent from tools; disable-model-invocation additionally
    # stops any *other* agent from invoking this one as a subagent at all —
    # a stronger, VS Code-native backstop for README's "NEVER spawn orchestrator".
    $lines += 'disable-model-invocation: true'
  }
  else {
    $tools = Get-VSCodeAgentTools -CapabilityIntent $meta.capabilityIntent -PathPolicy $meta.pathPolicy
    $lines += "tools: $(ConvertTo-YamlFlowList -Items $tools)"
    $lines += "model: $(ConvertTo-YamlFlowList -Items (Get-VSCodeModelsForTier -Tier $meta.tier))"
    if ($script:Handoffs.ContainsKey($Name)) {
      $h = $script:Handoffs[$Name]
      $lines += 'handoffs:'
      $lines += "  - label: $($h.label)"
      $lines += "    agent: $($h.agent)"
      $lines += "    prompt: $($h.prompt -replace '"', '''')"
      $lines += '    send: false'
    }
  }
  $lines += '---'

  $content = (Get-Content -Raw -LiteralPath $SourcePath).TrimEnd()
  $header = New-GeneratedComment -Source "agents/$Name.md"
  return (($lines -join "`n") + "`n`n$header`n`n$content`n")
}

$genFiles = @()

# Task 4.1: 9 .agent.md custom agents.
foreach ($a in (Get-AgentFiles -Repo $Repo)) {
  $desc = Get-AgentDescription -Path $a.Path
  $body = Get-AgentMarkdown -Name $a.Name -Description $desc -SourcePath $a.Path
  $out = Join-Path $AgentsDir "$($a.Name).agent.md"
  Set-Content -LiteralPath $out -Value $body -Encoding utf8 -NoNewline
  $genFiles += $out
}

# Task 4.2: single always-on instructions file — Principles table only (I11).
# Extracted live from README.md (single source of truth, DRY) rather than
# duplicated verbatim here; the table's own 4th row already states the
# "main agent is the brain on /e2e" identity rule, so no separate copy is
# needed to satisfy that half of task 4.2.
function Get-ReadmePrinciplesSection {
  param([string]$Path)
  $lines = Get-Content -LiteralPath $Path
  $startIdx = $null
  for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match '^##\s+Principles\s*$') { $startIdx = $i; break }
  }
  if ($null -eq $startIdx) { throw "Get-ReadmePrinciplesSection: README.md has no '## Principles' heading" }
  $section = @()
  for ($i = $startIdx; $i -lt $lines.Count; $i++) {
    if ($i -gt $startIdx -and $lines[$i] -match '^---\s*$') { break }
    $section += $lines[$i]
  }
  return (($section -join "`n").Trim())
}

$principles = Get-ReadmePrinciplesSection -Path (Join-Path $Repo 'README.md')
$instrHeader = New-GeneratedComment -Source 'README.md "Principles" section'
$instrBody = "---`napplyTo: `"**`"`n---`n`n$instrHeader`n`n$principles`n"
$instrOut = Join-Path $InstrDir 'agent-playbook.instructions.md'
Set-Content -LiteralPath $instrOut -Value $instrBody -Encoding utf8 -NoNewline
$genFiles += $instrOut

# Task 4.3: prompt files get real frontmatter (F-14) — name, description, agent,
# argument-hint where wave-1's parser supplies one (I4: absent -> no key at all).
foreach ($c in (Get-CommandFiles -Repo $Repo)) {
  $agent = Get-CommandAgent -Path $c.Path
  $agentForDesc = if ($agent) { $agent } else { 'agent' }
  $skillDesc = Get-CommandSkillDescription -Path $c.Path -CommandName $c.Name -AgentName $agentForDesc
  $argHint = Get-CommandArgumentHint -Path $c.Path
  $task = Get-CommandTask -Path $c.Path

  $fm = @('---', "name: $($c.Name)", "description: $($skillDesc -replace '"', '''')")
  if ($agent) { $fm += "agent: $agent" }
  if ($argHint) { $fm += "argument-hint: $argHint" }
  $fm += '---'

  $header = New-GeneratedComment -Source "commands/$($c.Name).md"
  $body = (($fm -join "`n") + "`n`n$header`n`n$task`n")
  $out = Join-Path $PromptsDir "$($c.Name).prompt.md"
  Set-Content -LiteralPath $out -Value $body -Encoding utf8 -NoNewline
  $genFiles += $out
}

Set-ManifestHarness -Target $TargetPath -Harness 'vscode' -Files $genFiles
Write-Host "vscode: $(@(Get-AgentFiles -Repo $Repo).Count) custom agents -> $AgentsDir"
Write-Host "vscode: $(@(Get-CommandFiles -Repo $Repo).Count) prompt files -> $PromptsDir"
Write-Host "vscode: 1 always-on instructions file -> $InstrDir"
Write-Host "vscode: best-effort. Verify .agent.md / .prompt.md / .instructions.md against your Copilot version."
