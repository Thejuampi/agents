$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\common.ps1"
$Repo = Get-RepoRoot

$agents = Get-AgentFiles -Repo $Repo | Sort-Object Name
$commands = Get-CommandFiles -Repo $Repo | Sort-Object Name

Write-Host "Agents ($($agents.Count)):"
foreach ($a in $agents) {
  $desc = Get-AgentDescription -Path $a.Path
  Write-Host "  $($a.Name.PadRight(14)) $desc"
}
Write-Host ""
Write-Host "Commands ($($commands.Count)):"
foreach ($c in $commands) {
  $agent = Get-CommandAgent -Path $c.Path
  $agent = if ($agent) { $agent } else { '?' }
  Write-Host "  /$($c.Name.PadRight(18)) -> $agent"
}
