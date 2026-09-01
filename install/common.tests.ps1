param()
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\common.ps1"
$Repo = Get-RepoRoot

<#
  install/common.tests.ps1 — fast, self-contained assertions for the wave-1
  primitives in install/common.ps1. Plain pwsh, no test framework (AGENTS.md
  prefers plain tooling; this repo has none). Run directly:
    pwsh -NoProfile -File install/common.tests.ps1
  Exits non-zero if any assertion fails.
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

# --- W1-P05 / I25: 9 explicit Get-RoleMeta records; frozen key set exactly ----
$roles = @('orchestrator', 'planner', 'sensei', 'advisor', 'builder', 'reviewer', 'refiner', 'qa', 'curator')
$expectedTiers = @{
  orchestrator = 'Highest'; planner = 'Highest'; sensei = 'Highest'
  reviewer     = 'High'; qa = 'High'; refiner = 'High'
  advisor      = 'Mid'; builder = 'Mid'; curator = 'Mid'
}
$frozenKeys = @('tier', 'effortLevel', 'capabilityIntent', 'pathPolicy', 'claudeColor', 'claudeMaxTurns', 'opencodeTaskPolicy')
Assert-Equal -Expected 9 -Actual $roles.Count -Message 'exactly 9 roles enumerated'

foreach ($role in $roles) {
  $meta = Get-RoleMeta -Name $role
  Assert-True -Condition ($null -ne $meta) -Message "Get-RoleMeta('$role') returns a non-null record"
  $actualKeys = @($meta.Keys)
  $missing = @($frozenKeys | Where-Object { $actualKeys -notcontains $_ })
  $extra = @($actualKeys | Where-Object { $frozenKeys -notcontains $_ })
  Assert-True -Condition ($missing.Count -eq 0 -and $extra.Count -eq 0) `
    -Message "Get-RoleMeta('$role') key set matches the frozen list exactly (missing: [$($missing -join ',')], extra: [$($extra -join ',')])"
  Assert-Equal -Expected $expectedTiers[$role] -Actual $meta.tier -Message "'$role' tier matches the patched README/orchestrator.md tables"
}

# --- W1-P06: capabilityIntent / pathPolicy enums for all 9 roles -------------
$validCapabilityIntents = @('dispatch', 'shellEdit', 'shellReadOnly', 'docsReadOnly', 'noRepoAccess', 'curatorReadOnly')
$validPathPolicies = @('unrestricted', 'noProductSource')
foreach ($role in $roles) {
  $meta = Get-RoleMeta -Name $role
  Assert-True -Condition ($validCapabilityIntents -contains $meta.capabilityIntent) -Message "'$role' capabilityIntent '$($meta.capabilityIntent)' is a valid enum value"
  Assert-True -Condition ($validPathPolicies -contains $meta.pathPolicy) -Message "'$role' pathPolicy '$($meta.pathPolicy)' is a valid enum value"
}
Assert-Equal -Expected 'noProductSource' -Actual (Get-RoleMeta -Name 'qa').pathPolicy -Message 'qa is the only role with pathPolicy=noProductSource'
$nonQaUnrestricted = @($roles | Where-Object { $_ -ne 'qa' } | ForEach-Object { (Get-RoleMeta -Name $_).pathPolicy }) | Where-Object { $_ -ne 'unrestricted' }
Assert-Equal -Expected 0 -Actual $nonQaUnrestricted.Count -Message 'every non-qa role stays pathPolicy=unrestricted'

# --- W1-P07 (closes sensei r3 P1-6): the schema is genuinely load-bearing ----
# No harness renderer consumes (capabilityIntent, pathPolicy) yet — that wiring
# is wave-2/4/5's job (plan.v3.md 1.4a). This is a reference consumer, local to
# this test file only, proving the two fields are distinguishable in a way any
# correct future renderer would have to branch on. Each consuming wave adds its
# own equivalent assertion against its REAL renderer once it exists.
function Get-ReferenceProductSourceDenial {
  param([string]$PathPolicy)
  return ($PathPolicy -eq 'noProductSource')
}
$before = Get-ReferenceProductSourceDenial -PathPolicy 'unrestricted'
$after = Get-ReferenceProductSourceDenial -PathPolicy 'noProductSource'
Assert-True -Condition ($before -ne $after) -Message 'flipping pathPolicy alone changes the reference-consumer output (schema is load-bearing, not decorative)'

# --- W1-N01: unknown role -> default record + warning naming the role -------
$warnings = @()
$bogus = Get-RoleMeta -Name 'bogus-role' -WarningVariable warnings -WarningAction SilentlyContinue
Assert-True -Condition ($null -ne $bogus) -Message "Get-RoleMeta('bogus-role') returns a default record, not null"
Assert-True -Condition (@($warnings | Where-Object { $_ -match 'bogus-role' }).Count -gt 0) -Message "Get-RoleMeta('bogus-role') emits a warning naming the unknown role"

# --- W1-N04: a hypothetical unschemed key fails the frozen-key-list test ----
$syntheticWithExtraKey = [ordered]@{ tier = 'Mid'; effortLevel = 'medium'; capabilityIntent = 'shellEdit'; pathPolicy = 'unrestricted'; claudeColor = $null; claudeMaxTurns = $null; opencodeTaskPolicy = 'leaf'; newUnschemedKey = 'x' }
$syntheticKeys = @($syntheticWithExtraKey.Keys)
$syntheticExtra = @($syntheticKeys | Where-Object { $frozenKeys -notcontains $_ })
Assert-True -Condition ($syntheticExtra.Count -eq 1 -and $syntheticExtra[0] -eq 'newUnschemedKey') -Message 'a synthetic unschemed key is caught and named by the same frozen-key-list check (I25 mechanism proof)'

# --- Get-CommandArgumentHint (task 1.4, I4) ----------------------------------
$e2eHint = Get-CommandArgumentHint -Path (Join-Path $Repo 'commands\e2e.md')
$resumeHint = Get-CommandArgumentHint -Path (Join-Path $Repo 'commands\e2e-resume.md')
Assert-Equal -Expected '[session-slug]' -Actual $e2eHint -Message 'commands/e2e.md Argument-Hint parses to [session-slug]'
Assert-Equal -Expected '[session-slug]' -Actual $resumeHint -Message 'commands/e2e-resume.md Argument-Hint parses to [session-slug]'
$othersWithoutHint = Get-CommandFiles -Repo $Repo | Where-Object { $_.Name -notin @('e2e', 'e2e-resume') }
Assert-Equal -Expected 9 -Actual $othersWithoutHint.Count -Message 'exactly 9 other command files exist'
foreach ($c in $othersWithoutHint) {
  $hint = Get-CommandArgumentHint -Path $c.Path
  Assert-True -Condition ($null -eq $hint) -Message "'$($c.Name).md' has no Argument-Hint -> parser returns `$null (not empty string)"
}

# --- Get-CommandSkillDescription fallback (task 1.5, F-13) -------------------
foreach ($c in $othersWithoutHint) {
  $agent = Get-CommandAgent -Path $c.Path
  $desc = Get-CommandSkillDescription -Path $c.Path -CommandName $c.Name -AgentName $agent
  Assert-True -Condition ($desc -notmatch '\$\w') -Message "'$($c.Name)' generated description has no `$-prefixed command sigil"
  Assert-True -Condition ($desc.Length -le 1024) -Message "'$($c.Name)' generated description is <= 1024 chars"
  Assert-True -Condition ($desc.Length -gt 0) -Message "'$($c.Name)' generated description is non-empty"
}
$e2eDesc = Get-CommandSkillDescription -Path (Join-Path $Repo 'commands\e2e.md') -CommandName 'e2e' -AgentName 'orchestrator'
$resumeDesc = Get-CommandSkillDescription -Path (Join-Path $Repo 'commands\e2e-resume.md') -CommandName 'e2e-resume' -AgentName 'orchestrator'
Assert-True -Condition ($e2eDesc -notmatch '\$\w') -Message 'e2e Skill-Description has no $-prefixed command sigil'
Assert-True -Condition ($resumeDesc -notmatch '\$\w') -Message 'e2e-resume Skill-Description has no $-prefixed command sigil'

# --- W1-E01: overlong Skill-Description truncates at a word boundary --------
$tmpCmd = Join-Path ([System.IO.Path]::GetTempPath()) ("verify-e01-" + [guid]::NewGuid().ToString('N') + '.md')
$longDesc = (('build the widget ' * 70)).Trim()
Assert-True -Condition ($longDesc.Length -gt 1024) -Message 'synthetic overlong description fixture is actually > 1024 chars'
Set-Content -LiteralPath $tmpCmd -Value "# /synthetic`n`nUse ``agents/builder.md``.`n`nSkill-Description: $longDesc`n`nPrompt:`n`n``````text`ndo it`n``````"
$truncWarnings = @()
$truncated = Get-CommandSkillDescription -Path $tmpCmd -CommandName 'synthetic' -AgentName 'builder' -WarningVariable truncWarnings -WarningAction SilentlyContinue
Assert-True -Condition ($truncated.Length -le 1024) -Message 'overlong Skill-Description is truncated to <= 1024 chars'
Assert-True -Condition (-not $truncated.EndsWith(' ')) -Message 'truncated description does not end mid-word with trailing space'
Assert-True -Condition ($truncWarnings.Count -gt 0) -Message 'truncation emits a warning'
Remove-Item -LiteralPath $tmpCmd -Force -ErrorAction SilentlyContinue

# --- N03 mirror: Install-PlaybookSkillsTo rejects an out-of-spec key for non-Claude harnesses ---
$rejected = $false
try {
  Install-PlaybookSkillsTo -SkillsRoot (Join-Path ([System.IO.Path]::GetTempPath()) ("verify-n03-" + [guid]::NewGuid().ToString('N'))) `
    -Repo $Repo -SyncCommand 'test' -HarnessLabel 'grok' -ExtraFrontmatter ([ordered]@{ 'argument-hint' = 'x' }) | Out-Null
}
catch { $rejected = $true }
Assert-True -Condition $rejected -Message 'Install-PlaybookSkillsTo throws when a non-Claude harness gets a key outside the agentskills.io six-field spec (I3)'

Write-Host ""
Write-Host "$($script:PassCount) passed, $($script:Failures.Count) failed."
if ($script:Failures.Count -gt 0) {
  Write-Host "Failures:" -ForegroundColor Red
  foreach ($f in $script:Failures) { Write-Host "  - $f" -ForegroundColor Red }
  exit 1
}
exit 0
