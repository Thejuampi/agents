# Grok Build Adapter

Grok Build / Grok TUI load skills from:

| Scope | Path |
| --- | --- |
| Personal | `~/.grok/skills/<name>/SKILL.md` |
| Project | `<repo>/.grok/skills/<name>/SKILL.md` |

Format matches Agent Skills: YAML frontmatter (`name`, `description`) + markdown body.

## Install

```pwsh
# From C:\Users\Juan\Documents\agents
make install-grok-global
make sync-grok-global

make install-grok TARGET=G:/dev/repos/discount_screener
```

Or:

```pwsh
make install-personal   # codex + claude + grok
```

## Agent references

Grok does not use Claude-style `~/.claude/agents/` files. The installer also writes agent markdown under:

```text
~/.grok/skills/_playbook-agents/<agent>.md
```

Skill bodies point at the canonical sources under `Documents/agents/agents/` and tell the model to role-play or spawn general-purpose subagents with those prompts when named custom agents are unavailable.

## Invoking

```text
/e2e
/plan-this
$e2e
```

Stage 6 black-box QA (`qa`) has no native path deny on Grok — follow `agents/qa.md` policy (docs OK, product source not an oracle) and orchestrator degraded-mode integrity.
