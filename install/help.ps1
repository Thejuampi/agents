$here = @'
Agent Playbook - install/sync Makefile

Primary:
  make install-opencode            Generate opencode-native adapters in THIS repo (reference-only).
  make sync-opencode               Same as install-opencode (idempotent; re-run after editing agents/ or commands/).
  make uninstall-opencode          Remove generated opencode adapters from this repo.

Copy-based (validated native surfaces), into a target project:
  make install TARGET=<dir>        Install codex + vscode into <dir>.
  make sync TARGET=<dir>           Same as install (re-run to replicate edits to clients).
  make uninstall TARGET=<dir>      Remove generated files from <dir>.

Per-harness:
  make install-codex  TARGET=<dir>   -> <dir>/.codex/agents/*.toml          (custom agents; no command surface in Codex)
  make install-vscode TARGET=<dir>   -> <dir>/.github/prompts/*.prompt.md   (from commands/)
                                       <dir>/.github/instructions/*.instructions.md  (from agents/)

Opt-in / best-effort (NOT in the default install path):
  make install-claude TARGET=<dir>   -> <dir>/.claude/  (not validated; verify before relying on it)

Other:
  make list                        List discovered agents and commands.
  make all                         install-opencode + install TARGET.
  make clean                       Remove in-repo generated artifacts.
  make help                        Show this help.

Variables:
  TARGET   Destination project for copy-based harnesses. Default: .

Native surfaces (verified):
  opencode  .opencode/opencode.json (agent.prompt = {file:../agents/X.md}) + .opencode/commands/X.md (@commands/X.md)
  codex     .codex/agents/<name>.toml (name/description/developer_instructions/sandbox_mode); AGENTS.md owned by target; no custom slash commands
  vscode    .github/prompts/<name>.prompt.md + .github/instructions/<name>.instructions.md (applyTo)

Notes:
  - opencode is reference-only: agents/commands stay the single source of truth.
  - For OTHER opencode projects to use this repo, add it as a "reference" (see adapters/opencode.md).
  - codex/vscode copy content because those harnesses cannot read outside the target repo.
    Re-run `make sync TARGET=<dir>` after editing agents/*.md or commands/*.md.
  - Each generated file carries a header pointing back to its source.
  - Generated artifacts are gitignored; the canonical files in agents/ and commands/ are the source of truth.
'@
Write-Host $here
