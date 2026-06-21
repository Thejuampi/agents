param([string]$Target = '.')
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\common.ps1"
$Repo = Get-RepoRoot
$TargetPath = Resolve-Target -Target $Target

# VS Code / GitHub Copilot surfaces:
#   - Reusable chat prompts: .github/prompts/<name>.prompt.md   (from commands/*.md)
#   - Path-specific instructions: .github/instructions/<name>.instructions.md
#     (from agents/*.md) with applyTo: "**" so the role guidance applies broadly.
#   Instructions naming (NAME.instructions.md + applyTo frontmatter) is verified
#   against docs.github.com. Prompt-file naming (.prompt.md) is the established
#   convention; verify it matches your Copilot/VS Code version.
#   NOTE: Copilot has no native per-"agent" surface. Mapping role behaviors to
#   instructions is a best-effort approximation; applyTo: "**" injects every role
#   into all Copilot requests, which can be heavy. Narrow applyTo per file if needed.

$PromptsDir = Join-Path $TargetPath '.github\prompts'
$InstrDir = Join-Path $TargetPath '.github\instructions'
New-Item -ItemType Directory -Path $PromptsDir -Force | Out-Null
New-Item -ItemType Directory -Path $InstrDir -Force | Out-Null

$genFiles = @()

foreach ($a in (Get-AgentFiles -Repo $Repo)) {
  $content = (Get-Content -Raw -LiteralPath $a.Path).TrimEnd()
  $header = New-GeneratedComment -Source "agents/$($a.Name).md"
  $body = "---`napplyTo: `"**`"`n---`n`n$header`n`n$content`n"
  $out = Join-Path $InstrDir "$($a.Name).instructions.md"
  Set-Content -LiteralPath $out -Value $body -Encoding utf8 -NoNewline
  $genFiles += $out
}

foreach ($c in (Get-CommandFiles -Repo $Repo)) {
  $content = (Get-Content -Raw -LiteralPath $c.Path).TrimEnd()
  $header = New-GeneratedComment -Source "commands/$($c.Name).md"
  $body = "$header`n`n$content`n"
  $out = Join-Path $PromptsDir "$($c.Name).prompt.md"
  Set-Content -LiteralPath $out -Value $body -Encoding utf8 -NoNewline
  $genFiles += $out
}

Set-ManifestHarness -Target $TargetPath -Harness 'vscode' -Files $genFiles
Write-Host "vscode: $($genFiles.Count) files -> $PromptsDir, $InstrDir"
Write-Host "vscode: best-effort. Verify .prompt.md / .instructions.md against your Copilot version."
