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

Sensei and Refiner disallow repo tools so they stay context-only (or judgment-only).

## Invoking

```text
/e2e
/plan-this
@sensei (agent) review this plan
```

The `/e2e` skill instructs the main session to act as Orchestrator and delegate to named subagents when available.
