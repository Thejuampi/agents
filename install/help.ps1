$here = @'
Agent Playbook - install/sync Makefile

Primary:
  make install-opencode            Generate opencode-native adapters in THIS repo (reference-only).
  make sync-opencode               Same as install-opencode (idempotent; re-run after editing agents/ or commands/).
  make uninstall-opencode          Remove generated opencode adapters from this repo.

Copy-based into a target project:
  make install TARGET=<dir>        Install codex + vscode into <dir>.
  make sync TARGET=<dir>           Same as install.
  make uninstall TARGET=<dir>      Remove generated files from <dir>.

Per-harness (project):
  make install-codex TARGET=<dir>    -> <dir>/.codex/agents/*.toml
  make install-vscode TARGET=<dir>   -> <dir>/.github/prompts + instructions
  make install-claude TARGET=<dir>   -> <dir>/.claude/{skills,agents,commands}
  make install-grok TARGET=<dir>     -> <dir>/.grok/skills

Personal (all projects on this machine):
  make install-codex-global          -> ~/.codex/agents + ~/.agents/skills + ~/.codex/prompts
  make install-claude-global         -> ~/.claude/skills + ~/.claude/agents + ~/.claude/commands
  make install-grok-global           -> ~/.grok/skills (+ _playbook-agents refs)
  make install-personal              -> codex-global + claude-global + grok-global  (recommended day-to-day)
  make sync-personal                 -> same as install-personal

Other:
  make list                        List discovered agents and commands.
  make all                         install-opencode + install TARGET.
  make clean                       Remove in-repo generated artifacts.
  make help                        Show this help.

Variables:
  TARGET   Destination project for copy-based harnesses. Default: .

Native surfaces:
  opencode  .opencode/opencode.json + .opencode/commands/
  codex     .codex/agents/*.toml; global also ~/.agents/skills
  vscode    .github/prompts + .github/instructions
  claude    .claude/skills/*/SKILL.md + .claude/agents/*.md (+ commands aliases)
  grok      .grok/skills/*/SKILL.md

Notes:
  - Canonical source of truth: agents/*.md and commands/*.md
  - Re-run make sync-*-global after editing agents or commands
  - First Claude install that creates ~/.claude/agents may need a Claude Code restart
  - /e2e is the full multi-agent pipeline; see agents/orchestrator.md
'@
Write-Host $here
