# OpenCode Adapter

OpenCode supports project or global agents as Markdown files with frontmatter.

## Automated install (reference-only)

Run once inside this repo:

```pwsh
make install-opencode
```

This generates two things, both pure references (no content is copied):

- `.opencode/opencode.json` — one `agent` entry per `agents/*.md`, each with
  `prompt: "{file:../agents/<name>.md}"`. OpenCode reads the canonical file at load
  time and inlines it into the agent prompt. Agent `mode`/`permission` are derived
  from a small table in `install/common.ps1` (`Get-OpenCodeAgentMeta`); edit there
  to tune.
- `.opencode/commands/<name>.md` — a thin file whose body is just
  `@commands/<name>.md`. OpenCode inlines the canonical command text at execution
  time.

Re-run `make sync-opencode` after editing `agents/*.md` or `commands/*.md`.
Generated files are gitignored; `agents/` and `commands/` remain the single source
of truth. Put personal OpenCode customizations in a root `opencode.jsonc`
(OpenCode deep-merges it with the generated `.opencode/opencode.json`); do not edit
the generated file directly, since `sync-opencode` overwrites it.

Restart OpenCode after install or sync — config is loaded once at startup.

### Stage 6 `qa` permissions

`Get-OpenCodeAgentMeta` for `qa` (in `install/common.ps1`):

| Permission | Value | Why |
| --- | --- | --- |
| `edit` | `deny` | Product tree write forbidden; Orchestrator copy-only persists `qa/*` |
| `bash` | `allow` | CLI / app / attach probe |
| `read` | **not denied** | Docs and operator runbooks must be readable for black-box planning |

There is **no** `read = 'deny'` on QA. Product-source path deny is policy in `agents/qa.md` (degraded + source-citation process fail when the harness cannot express path-class deny). Eligibility: prefer path deny when OpenCode supports it; else `degraded`.

The generated config does not add `AGENTS.md` to `instructions`: OpenCode already
loads `AGENTS.md` as project rules, and listing it again would duplicate context.

## Using this repo from another OpenCode project

Do not copy anything. Add this repo as a reference in the other project's
`opencode.json`:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "references": {
    "agents-repo": {
      "path": "C:/Users/Juan/Documents/agents",
      "description": "Canonical agent definitions and commands"
    }
  }
}
```

The other project can then `@`-reference files under the `agents-repo` alias.
Edits made here are visible there on the next OpenCode restart.

## DRY Rule

The canonical prompt stays in `agents/*.md`.

OpenCode-specific files are adapters only. The generated `.opencode/` files point
at the canonical files; they never duplicate their content.
