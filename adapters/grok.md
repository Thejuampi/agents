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

## Resume / session continuity

| Field | Value |
| --- | --- |
| **Spawn path** | Main agent runs `/e2e` (or `$e2e`) as Orchestrator. Leaf specialists are spawned via `spawn_subagent` (or equivalent general-purpose subagent) with the agent prompt from `agents/*.md` / `~/.grok/skills/_playbook-agents/`. There is no separate named-agent registry like Claude’s `~/.claude/agents/`. |
| **`resume_supported`** | **`true`** |
| **Resume mechanism** | Pass the prior leaf `session_ref` as **`resume_from`** when re-spawning the same role-chain (observed in Grok Build). Do **not** invent other resume APIs beyond observed `resume_from` / `session_ref`. |
| **`session_ref`** | Id returned by the prior successful spawn (UUID-style). Record it in `session-registry.md` on every open/completed row. If the harness returns no id, `session_ref: none` and resume is not available for that hop. |
| **Dead session** | Resume fails, id rejected, or re-bind does not restore the prior leaf → treat as **dead** → run Global Continuity reconstitution checklist (or `cold_start_waived` / **BLOCK**). Never silent cold start on a dependent edge. |
| **When resume fails** | Outcome is **`reconstituted`** (checklist green) or **`cold_start_waived`** / **BLOCK** — never label reconstituted work as `resumed`. |

Orchestrator still owns Continuity law (`agents/orchestrator.md`); this adapter only states harness honesty.