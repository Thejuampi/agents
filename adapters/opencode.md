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

## Resume / session continuity

| Field | Value |
| --- | --- |
| **Spawn path** | OpenCode loads agents via generated `.opencode/opencode.json` entries that `{file:…}`-reference `agents/*.md`. Commands under `.opencode/commands/` reference `commands/*.md`. Orchestrator work is the main chat acting as orchestrator; leaves are OpenCode agents selected by name. |
| **`resume_supported`** | **`false`** |
| **Why** | No playbook-documented OpenCode API resumes a prior leaf agent session by id. Config is loaded at startup; agent prompts are re-inlined from files. Do **not** invent a resume API. |
| **`session_ref`** | Unsupported / `none` unless a future OpenCode version exposes a documented handle (then update this adapter with evidence). |
| **Dead session** | Treat every new agent selection as a new leaf unless the **same main chat** still holds context (main-thread continuity ≠ leaf resume). |
| **When resume unsupported** | **`reconstituted`** from session artifacts under `.agents/workspace/tmp/e2e/<slug>/` when checklist green; else **`cold_start_waived`** or **BLOCK**. Silent cold start on dependent edges is forbidden. |

See `agents/orchestrator.md` **Global Continuity**.