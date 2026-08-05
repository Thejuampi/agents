# Claude Code Adapter

Claude Code loads **skills** and **subagents** from well-known directories.

## Surfaces

| Kind | Personal | Project |
| --- | --- | --- |
| Skills (`/e2e`, `/plan-this`, …) | `~/.claude/skills/<name>/SKILL.md` | `<repo>/.claude/skills/<name>/SKILL.md` |
| Subagents (`sensei`, `builder`, …) | `~/.claude/agents/<name>.md` | `<repo>/.claude/agents/<name>.md` |
| Legacy commands | `~/.claude/commands/<name>.md` | `<repo>/.claude/commands/<name>.md` |

Skills and commands that share a name both register `/name`; prefer skills.

## Install

```pwsh
# From C:\Users\Juan\Documents\agents
make install-claude-global          # personal: all projects
make sync-claude-global             # re-run after editing agents/ or commands/

make install-claude TARGET=G:/dev/repos/discount_screener
make sync-claude TARGET=G:/dev/repos/discount_screener
```

Or with the personal bundle:

```pwsh
make install-personal   # codex + claude + grok
```

After the first install that creates `~/.claude/agents/`, **restart Claude Code** so the agents directory is watched.

## Subagent frontmatter

Generated agents include Claude-native fields:

- `tools` / `disallowedTools`
- `model` (`opus` for orchestrator/planner/sensei; `sonnet` for builder/advisor/reviewer/…)
- `permissionMode` where useful (`plan` for planner, `acceptEdits` for builder/orchestrator)

Sensei and Refiner disallow repo tools so they stay context-only (or judgment-only). Advisor may `Read`/`Grep`/`Glob` for **documentation only** (see `agents/advisor.md`); Write/Edit/Bash are disallowed.

## Invoking

```text
/e2e
/plan-this
@sensei (agent) review this plan
```

The `/e2e` skill instructs the main session to act as Orchestrator and delegate to named subagents when available.

## Resume / session continuity

| Field | Value |
| --- | --- |
| **Spawn path** | Main session is Orchestrator (`/e2e`). Leaves are Claude **subagents** from `~/.claude/agents/<name>.md` or project `.claude/agents/` (or Task/Agent tool equivalents). Skills under `~/.claude/skills/` are entrypoints, not Continuity roots. |
| **`resume_supported`** | **`false`** |
| **Why** | Claude Code can keep the **main** conversation continuous, but this playbook does **not** document a stable public API to resume a prior leaf subagent run by id. Soft “same thread” is orchestrator process discipline, not a verified resume primitive. Do **not** invent `resume_from`-style APIs. |
| **`session_ref`** | If the harness exposes a subagent/run id, store it in `session-registry.md`; otherwise `none`. Format is harness-defined and version-dependent. |
| **Dead session** | New subagent spawn without prior id = treat prior leaf as dead. Main-session restart without registry re-bind = dead for Continuity purposes. |
| **When resume unsupported** | **`reconstituted`** from admitted packages (`sensei-r*.md`, `advisor-r*.md`, builder reports, `fix-package-r*.md`, ledger) when checklist green; else **`cold_start_waived`** or **BLOCK**. Silent cold start on dependent edges is forbidden. |

See `agents/orchestrator.md` **Global Continuity**.