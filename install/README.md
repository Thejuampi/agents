# install/

Automation for converting this repo into native formats for different agent harnesses.
The canonical source of truth is always `../agents/*.md` and `../commands/*.md`.
Installers only **reference** (opencode) or **copy + sync** (other harnesses); they never become a second source of truth.

## Layout

```text
install/
  common.ps1            shared helpers: enumerate agents/commands, parse descriptions, manifest
  opencode.ps1          reference-only, in-repo (the primary target)
  codex.ps1             copy + sync -> project .codex/agents, or global agents + skills/prompts with -Global
  vscode.ps1            copy + sync -> <target>/.github/{prompts,instructions}
  claude.ps1            copy + sync -> project or personal ~/.claude/{skills,agents,commands}
  grok.ps1              copy + sync -> project or personal ~/.grok/skills (+ _playbook-agents)
  list.ps1              print discovered agents and commands
  help.ps1              print Makefile usage
  uninstall*.ps1        remove generated files via the manifest
  clean.ps1             remove in-repo generated artifacts
```

Each installer is also runnable directly, without `make`:

```pwsh
pwsh -NoProfile -File install/opencode.ps1
pwsh -NoProfile -File install/codex.ps1  -Target C:/code/myproject
pwsh -NoProfile -File install/codex.ps1  -Global
pwsh -NoProfile -File install/claude.ps1 -Global
pwsh -NoProfile -File install/grok.ps1   -Global
pwsh -NoProfile -File install/vscode.ps1 -Target C:/code/myproject
```

## Two strategies

| Strategy      | When                                              | How                                                              |
| ------------- | ------------------------------------------------- | ---------------------------------------------------------------- |
| reference     | the harness can read files inside this repo       | generate a thin adapter that points at `agents/*.md` / `commands/*.md` |
| copy + sync   | the harness cannot read outside the target repo   | copy content with a `<!-- generated ... source: ... -->` header; re-run `make sync` to replicate edits |

## Native surfaces

| Harness  | Surface                                                                                          | Strategy   | Status        |
| -------- | ------------------------------------------------------------------------------------------------ | ---------- | ------------- |
| opencode | `.opencode/opencode.json` (`agent.*.prompt = {file:../agents/X.md}`) + `.opencode/commands/X.md` (`@commands/X.md`) | reference  | verified      |
| codex    | `.codex/agents/<name>.toml`; global install adds `~/.agents/skills/` and `~/.codex/prompts/`     | copy+sync  | verified personal path |
| vscode   | `.github/prompts/<name>.prompt.md` (from `commands/`) + `.github/instructions/<name>.instructions.md` (from `agents/`, `applyTo`) | copy+sync  | best-effort*  |
| claude   | `.claude/skills`, `.claude/agents`, `.claude/commands` (project or `~/.claude` with `-Global`)  | copy+sync  | verified personal path |
| grok     | `.grok/skills/<cmd>/SKILL.md` + `_playbook-agents/<agent>.md` (project or `~/.grok` with `-Global`) | copy+sync  | verified personal path |

**Day-to-day personal install** (recommended): `make install-personal` / `make sync-personal` → Codex + Claude + Grok globals. Re-run after every edit to `agents/` or `commands/`.

\* VS Code: `.instructions.md` naming + `applyTo` frontmatter verified against docs.github.com. `.prompt.md` is the established convention but was not confirmed against a live install — verify against your Copilot/VS Code version. Copilot has no native per-"agent" surface, so role behaviors are mapped to path-scoped instructions as an approximation.

### Codex notes

- Custom agents are **TOML** files, not Markdown. Each `agents/X.md` becomes `.codex/agents/X.toml` with the markdown body embedded in `developer_instructions` (triple-quoted literal string).
- `sandbox_mode` is derived per agent: `workspace-write` for `builder` and `qa`, `read-only` otherwise. Edit `Get-CodexSandboxMode` in `codex.ps1` to tune.
- `-Global` installs each command as a personal skill under `~/.agents/skills/X/`. Invoke it as `$X` or select it from the `/` menu in app, CLI, or IDE.
- The global install also creates `~/.codex/prompts/X.md` for `/prompts:X` compatibility in CLI and IDE. Codex has deprecated this custom-prompt surface in favor of skills.
- `AGENTS.md` is not copied; the target project owns its own.

### VS Code notes

- `commands/*.md` → `.github/prompts/<name>.prompt.md` (reusable chat prompts).
- `agents/*.md` → `.github/instructions/<name>.instructions.md` with `applyTo: "**"` (applies broadly). This injects every role into all Copilot requests; narrow `applyTo` per file if that is too heavy.

## Manifest

Every copy-based installer records the files it created in `<target>/.agents-sync/manifest.json`.
`make uninstall TARGET=<dir>` reads that manifest and removes exactly those files, then prunes empty directories.
The manifest is gitignored.

## Adding a new harness

1. Create `install/<harness>.ps1`. Dot-source `common.ps1`; use `Get-AgentFiles`, `Get-CommandFiles`, `Get-AgentDescription`, `Get-CommandAgent`, `New-GeneratedComment`, `Resolve-Target`, `Set-ManifestHarness`.
2. Decide reference vs copy. Prefer reference if the harness can read files in this repo; otherwise copy with a generated header.
3. Add a Makefile target:
   ```make
   install-<harness>:
   	@$(PS) install/<harness>.ps1 -Target "$(TARGET)"
   ```
   and (if it should be default) add it to the `install sync:` dependency list.
4. Ensure `uninstall.ps1` covers the harness name (it loops over a list — add the name there).
5. Document the harness setup in `adapters/<harness>.md`.

Keep harness-specific metadata (e.g. opencode `mode`/`permission`, codex `sandbox_mode`) in the installer or a sidecar data file, never in `agents/*.md`. The canonical agent files stay harness-agnostic.
