param()
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\common.ps1"
$Repo = Get-RepoRoot

<#
  install/claude.tests.ps1 — fast, self-contained assertions for wave-2's
  Claude Code alignment work (plan.v3.md wave-2, tasks 2.1-2.5, 2.7-2.8).
  Plain pwsh, no test framework, mirrors install/common.tests.ps1's shape. Run:
    pwsh -NoProfile -File install/claude.tests.ps1
  Exits non-zero if any assertion fails. Generates into an isolated temp
  target under the OS temp dir; never touches -Global / ~/.claude.
#>

$script:Failures = New-Object System.Collections.Generic.List[string]
$script:PassCount = 0

function Assert-True {
  param([bool]$Condition, [string]$Message)
  if ($Condition) { $script:PassCount++; Write-Host "PASS: $Message" }
  else { $script:Failures.Add($Message); Write-Host "FAIL: $Message" -ForegroundColor Red }
}

function Assert-Equal {
  param($Expected, $Actual, [string]$Message)
  Assert-True -Condition ($Expected -eq $Actual) -Message "$Message (expected '$Expected', got '$Actual')"
}

function Get-FrontmatterBlock {
  param([string]$Path)
  $lines = Get-Content -LiteralPath $Path
  $dashCount = 0
  $out = @()
  foreach ($l in $lines) {
    if ($l -eq '---') { $dashCount++; if ($dashCount -ge 2) { break }; continue }
    if ($dashCount -eq 1) { $out += $l }
  }
  return ($out -join "`n")
}

function Get-FrontmatterFieldValue {
  # Extracts just one frontmatter field's value line (e.g. 'tools') so tool-name
  # checks don't false-positive against `description:` prose (e.g. "multi-agent")
  # or against `disallowedTools:` (a *denial*, not a grant).
  param([string]$FrontmatterBlock, [string]$Field)
  $m = [regex]::Match($FrontmatterBlock, "(?m)^$Field`:\s*(.*)$")
  if ($m.Success) { return $m.Groups[1].Value.Trim() }
  return ''
}

$TmpTarget = Join-Path ([System.IO.Path]::GetTempPath()) ("claude-tests-" + [guid]::NewGuid().ToString('N'))
try {
  pwsh -NoProfile -File (Join-Path $PSScriptRoot 'claude.ps1') -Target $TmpTarget | Out-Null
  $AgentsDir = Join-Path $TmpTarget '.claude\agents'
  $SkillsRoot = Join-Path $TmpTarget '.claude\skills'
  $CmdsDir = Join-Path $TmpTarget '.claude\commands'

  # --- W2-P01: 9 agents, 9 skills, 9 commands generated -----------------------
  $agentFiles = @(Get-ChildItem -LiteralPath $AgentsDir -Filter *.md)
  $skillDirs = @(Get-ChildItem -LiteralPath $SkillsRoot -Directory)
  $cmdFiles = @(Get-ChildItem -LiteralPath $CmdsDir -Filter *.md)
  Assert-Equal -Expected 9 -Actual $agentFiles.Count -Message 'W2-P01: 9 agent files generated'
  Assert-Equal -Expected 9 -Actual $skillDirs.Count -Message 'W2-P01: 9 skill dirs generated'
  Assert-Equal -Expected 9 -Actual $cmdFiles.Count -Message 'W2-P01: 9 command alias files generated'

  # --- W2-P02 (generator half; sandboxed-launch confirmation deferred to wave-7) --
  $senseiFm = Get-FrontmatterBlock -Path (Join-Path $AgentsDir 'sensei.md')
  $senseiToolsVal = Get-FrontmatterFieldValue -FrontmatterBlock $senseiFm -Field 'tools'
  Assert-Equal -Expected 'TodoWrite' -Actual $senseiToolsVal -Message 'W2-P02: sensei.md tools resolves to an explicit non-empty allowlist (TodoWrite only)'
  foreach ($forbidden in @('Agent', 'Skill', 'SendMessage', 'Read', 'Bash', 'PowerShell')) {
    Assert-True -Condition ($senseiToolsVal -cnotmatch "\b$forbidden\b") -Message "W2-P02: sensei.md tools does not grant '$forbidden'"
  }
  $refinerFm = Get-FrontmatterBlock -Path (Join-Path $AgentsDir 'refiner.md')
  $refinerToolsVal = Get-FrontmatterFieldValue -FrontmatterBlock $refinerFm -Field 'tools'
  Assert-Equal -Expected 'TodoWrite' -Actual $refinerToolsVal -Message 'W2-N01 (generator half): refiner.md tools resolves to an explicit non-empty allowlist (TodoWrite only)'
  foreach ($forbidden in @('Agent', 'Skill', 'SendMessage', 'Read', 'Bash', 'PowerShell')) {
    Assert-True -Condition ($refinerToolsVal -cnotmatch "\b$forbidden\b") -Message "W2-N01 (generator half): refiner.md tools does not grant '$forbidden'"
  }

  # --- W2-P03 / W2-N02 (I7): argument-hint + disable-model-invocation --------
  foreach ($skillName in @('e2e', 'e2e-resume')) {
    $fm = Get-FrontmatterBlock -Path (Join-Path $SkillsRoot "$skillName\SKILL.md")
    Assert-True -Condition ($fm -match '(?m)^argument-hint:') -Message "W2-P03: '$skillName' SKILL.md has argument-hint"
    Assert-True -Condition ($fm -match '(?m)^disable-model-invocation:\s*true\s*$') -Message "W2-P03: '$skillName' SKILL.md has disable-model-invocation: true"
  }
  $otherSkills = @($skillDirs | Where-Object { $_.Name -notin @('e2e', 'e2e-resume') })
  Assert-Equal -Expected 7 -Actual $otherSkills.Count -Message 'W2-N02: exactly 7 other skills exist'
  foreach ($s in $otherSkills) {
    $fm = Get-FrontmatterBlock -Path (Join-Path $s.FullName 'SKILL.md')
    Assert-True -Condition ($fm -notmatch 'disable-model-invocation') -Message "W2-N02: '$($s.Name)' SKILL.md has no disable-model-invocation (stays model-invocable)"
    Assert-True -Condition ($fm -notmatch '(?m)^argument-hint:') -Message "W2-N02: '$($s.Name)' SKILL.md has no argument-hint"
  }

  # --- W2-P05: model + effort match Get-RoleMeta for all 9 roles -------------
  $roleModels = @{
    orchestrator = 'opus'; planner = 'opus'; sensei = 'opus'
    reviewer     = 'sonnet'; qa = 'sonnet'; refiner = 'sonnet'
    advisor      = 'sonnet'; builder = 'sonnet'; curator = 'sonnet'
  }
  foreach ($role in $roleModels.Keys) {
    $meta = Get-RoleMeta -Name $role
    $fm = Get-FrontmatterBlock -Path (Join-Path $AgentsDir "$role.md")
    Assert-True -Condition ($fm -match "(?m)^model:\s*$($roleModels[$role])\s*$") -Message "W2-P05: '$role' generated model matches expected tier-derived model"
    Assert-True -Condition ($fm -match "(?m)^effort:\s*$($meta.effortLevel)\s*$") -Message "W2-P05: '$role' generated effort matches Get-RoleMeta.effortLevel ('$($meta.effortLevel)')"
  }

  # --- Task 2.3 (F-15): PowerShell alongside Bash for the 5 shell roles, ------
  # neither for sensei/refiner/advisor/curator. orchestrator excluded from the
  # PowerShell-parity policy by the more specific 2.4' fixed-literal carve-out
  # (disclosed as a plan self-consistency finding in the wave-2 report).
  foreach ($role in @('builder', 'qa', 'reviewer', 'planner')) {
    $fm = Get-FrontmatterBlock -Path (Join-Path $AgentsDir "$role.md")
    $toolsVal = Get-FrontmatterFieldValue -FrontmatterBlock $fm -Field 'tools'
    Assert-True -Condition ($toolsVal -cmatch '\bBash\b' -and $toolsVal -cmatch '\bPowerShell\b') -Message "task 2.3: '$role' tools lists both Bash and PowerShell"
  }
  foreach ($role in @('sensei', 'refiner', 'advisor', 'curator')) {
    $fm = Get-FrontmatterBlock -Path (Join-Path $AgentsDir "$role.md")
    $toolsVal = Get-FrontmatterFieldValue -FrontmatterBlock $fm -Field 'tools'
    Assert-True -Condition ($toolsVal -cnotmatch '\bBash\b' -and $toolsVal -cnotmatch '\bPowerShell\b') -Message "task 2.3: '$role' tools lists neither Bash nor PowerShell"
  }

  # --- W2-N04 / W2-N05: generated orchestrator.md excludes Agent + SendMessage
  $orchFm = Get-FrontmatterBlock -Path (Join-Path $AgentsDir 'orchestrator.md')
  $orchToolsVal = Get-FrontmatterFieldValue -FrontmatterBlock $orchFm -Field 'tools'
  Assert-True -Condition ($orchToolsVal -cnotmatch '\bAgent\b') -Message 'W2-N04: generated orchestrator.md tools excludes Agent'
  Assert-True -Condition ($orchToolsVal -cnotmatch '\bSendMessage\b') -Message 'W2-N04: generated orchestrator.md tools excludes SendMessage'
  Assert-Equal -Expected 'Read, Write, Edit, Grep, Glob, Bash, Skill' -Actual $orchToolsVal -Message '2.4prime: generated orchestrator.md tools matches the exact fixed literal from plan.v3.md 1.4a'

  # --- W2-N03: zero isolation:/memory: keys in any generated frontmatter -----
  $allGenerated = @($agentFiles.FullName) + @($skillDirs | ForEach-Object { Join-Path $_.FullName 'SKILL.md' })
  foreach ($f in $allGenerated) {
    $fm = Get-FrontmatterBlock -Path $f
    Assert-True -Condition ($fm -notmatch '(?m)^\s*isolation:') -Message "W2-N03: '$f' frontmatter has no isolation: key"
    Assert-True -Condition ($fm -notmatch '(?m)^\s*memory:') -Message "W2-N03: '$f' frontmatter has no memory: key"
  }

  # --- task 2.7: 9 distinct colors; maxTurns only on sensei/refiner ----------
  $colors = @()
  foreach ($f in $agentFiles) {
    $fm = Get-FrontmatterBlock -Path $f.FullName
    $m = [regex]::Match($fm, '(?m)^color:\s*(\S+)\s*$')
    Assert-True -Condition $m.Success -Message "task 2.7: '$($f.Name)' has a color"
    if ($m.Success) { $colors += $m.Groups[1].Value }
  }
  Assert-Equal -Expected 9 -Actual (@($colors | Select-Object -Unique)).Count -Message 'task 2.7: all 9 generated colors are distinct'
  foreach ($role in @('sensei', 'refiner')) {
    $fm = Get-FrontmatterBlock -Path (Join-Path $AgentsDir "$role.md")
    Assert-True -Condition ($fm -match '(?m)^maxTurns:\s*\d+\s*$') -Message "task 2.7: '$role' has a numeric maxTurns"
  }
  foreach ($role in @('orchestrator', 'planner', 'reviewer', 'qa', 'advisor', 'builder', 'curator')) {
    $fm = Get-FrontmatterBlock -Path (Join-Path $AgentsDir "$role.md")
    Assert-True -Condition ($fm -notmatch '(?m)^maxTurns:') -Message "task 2.7: '$role' has no maxTurns (only sensei/refiner do)"
  }

  # --- Alias-loop path-leak fix: no absolute filesystem path anywhere --------
  foreach ($f in (Get-ChildItem -LiteralPath $CmdsDir -Filter *.md)) {
    $content = Get-Content -Raw -LiteralPath $f.FullName
    Assert-True -Condition ($content -notmatch [regex]::Escape($Repo)) -Message "task 2.1-disclosed-fix: '$($f.Name)' command alias body contains no baked absolute repo path"
    Assert-True -Condition ($content -notmatch '[A-Za-z]:\\\\Users\\\\') -Message "task 2.1-disclosed-fix: '$($f.Name)' command alias body contains no Windows user-profile absolute path"
  }

  # --- Task 2.8: generation-source check — e2e/e2e-resume skill body task ----
  # text matches the legacy command alias body's task text (same source,
  # commands/e2e*.md, not two independently-drifting copies).
  foreach ($cmdName in @('e2e', 'e2e-resume')) {
    $srcTask = Get-CommandTask -Path (Join-Path $Repo "commands\$cmdName.md")
    $skillBody = Get-Content -Raw -LiteralPath (Join-Path $SkillsRoot "$cmdName\SKILL.md")
    $cmdBody = Get-Content -Raw -LiteralPath (Join-Path $CmdsDir "$cmdName.md")
    Assert-True -Condition ($skillBody.Contains($srcTask.Trim())) -Message "task 2.8: '$cmdName' skill body embeds the same source task text as commands/$cmdName.md"
    Assert-True -Condition ($cmdBody.Contains($srcTask.Trim())) -Message "task 2.8: '$cmdName' command alias body embeds the same source task text as commands/$cmdName.md"
  }

  # --- W2-R02 (D9): builder permissionMode still acceptEdits, no isolation ---
  $builderFm = Get-FrontmatterBlock -Path (Join-Path $AgentsDir 'builder.md')
  Assert-True -Condition ($builderFm -match '(?m)^permissionMode:\s*acceptEdits\s*$') -Message 'W2-R02: builder permissionMode is still acceptEdits'
  Assert-True -Condition ($builderFm -notmatch 'isolation') -Message 'W2-R02: builder frontmatter has no isolation key (D9)'

  # --- W2-R01: e2e skill body regression guard --------------------------------
  $e2eSkillBody = Get-Content -Raw -LiteralPath (Join-Path $SkillsRoot 'e2e\SKILL.md')
  Assert-True -Condition ($e2eSkillBody -match '\*\*YOU\*\* run this pipeline in the \*\*current\*\* conversation') -Message 'W2-R01: e2e skill body retains the "YOU run this pipeline in the current conversation" branch'
}
finally {
  if (Test-Path -LiteralPath $TmpTarget) { Remove-Item -LiteralPath $TmpTarget -Recurse -Force -ErrorAction SilentlyContinue }
}

Write-Host ""
Write-Host "$($script:PassCount) passed, $($script:Failures.Count) failed."
if ($script:Failures.Count -gt 0) {
  Write-Host "Failures:" -ForegroundColor Red
  foreach ($f in $script:Failures) { Write-Host "  - $f" -ForegroundColor Red }
  exit 1
}
exit 0
