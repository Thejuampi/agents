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

`Get-ClaudeAgentFrontmatter` (in `install/common.ps1`) hand-authors every subagent's frontmatter; nothing here is bulk-derived from `Get-RoleMeta`'s `capabilityIntent` (that pure-function rule belongs to VS Code / OpenCode — see plan.v3.md §1.4a). Every tool-restriction decision carries an inline comment in the source.

Generated agents include:

- `tools` / `disallowedTools` — the actual capability grant (see per-role notes below).
- `model` (`opus` for orchestrator/planner/sensei; `sonnet` for the other six roles).
- `effort` — sourced from `Get-RoleMeta`'s tier-derived `effortLevel` for every role (`max`/`high`/`medium`). **Declared as a default, not a verified optimum** — this repo has no eval harness, so these values are honest defaults pending a real effort sweep, not tuned numbers.
- `permissionMode` where useful (`plan` for planner, `acceptEdits` for builder/orchestrator — builder does **not** get worktree isolation; see D9 below).
- `color` — a cosmetic per-role UI hint (9 distinct values, one per role) purely for operator legibility across concurrent transcripts. Claude Code documents no strict enum for this field; an unrecognized value is inert, not an error.
- `maxTurns` — present **only** on `sensei` and `refiner`, a cheap runaway-guard ceiling. Both roles have zero tool access and are single-turn judgment/output roles by contract (`agents/sensei.md` / `agents/refiner.md`), so a low ceiling catches a hung/looping session without constraining legitimate use.

**Sensei and Refiner (F-4, closed).** Both previously shipped `tools: ''`, which Claude Code resolves as "inherits every tool" (an *empty string* still skips the `tools:` line entirely) — silently defeating the `disallowedTools` denylist sitting next to it, which itself omitted `Agent`, `Skill`, `SendMessage`, `PowerShell`, and every other tool a background subagent retains but the denylist's authors hadn't enumerated. Both roles now carry an explicit, non-empty **allowlist**: `tools: TodoWrite` — the one harmless bookkeeping tool, nothing else. This is fail-closed against future Claude tool additions too (a denylist would need updating every time Anthropic ships a new tool; an allowlist doesn't).

Advisor may `Read`/`Grep`/`Glob` for **documentation only** (see `agents/advisor.md`); Write/Edit/Bash/PowerShell are disallowed or simply absent.

**PowerShell (F-15).** Claude Code's `PowerShell` tool is on by default on Windows without Git Bash, and this repo's own installers are `pwsh`. `builder`, `qa`, `reviewer`, and `planner` get `PowerShell` alongside `Bash` so they aren't shell-less on such a machine. `sensei`, `refiner`, `advisor`, and `curator` have no shell need under their own `agents/*.md` contracts and get neither. `orchestrator` is deliberately **excluded** from this policy — see the carve-out below.

### Orchestrator carve-out (2.4′, widened I26)

`orchestrator`'s tool grant is **hand-authored and fixed**, never derived from `capabilityIntent` (`= 'dispatch'`) or from the PowerShell-parity policy above. Applying either mechanically would re-derive (or drift toward) an `Agent`-bearing grant — directly contradicting README's Identity hard rule ("✗ NEVER spawn orchestrator"): a spawned orchestrator subagent must be able to **return a recommendation** to the parent, never dispatch further work itself.

This session's own live-loaded Claude Code agent registry (as of 2026-08-06) showed the orchestrator subagent granting `Agent, Read, Write, Edit, Grep, Glob, Bash, Skill` (no `SendMessage`). The generated `orchestrator.md` reproduces that grant **minus `Agent`**:

| | Before (live-loaded grant) | After (this repo's generator) |
| --- | --- | --- |
| `tools` | `Agent, Read, Write, Edit, Grep, Glob, Bash, Skill` | `Read, Write, Edit, Grep, Glob, Bash, Skill` |
| `Agent` present? | yes | **no** |
| `SendMessage` present? | no | no |

**What this proves, and what it doesn't (correcting an earlier over-claim):** this is the generator's output against a temp/sandbox target, verified in-session. It does **not** prove the operator's real, live `~/.claude/agents/orchestrator.md` has been corrected — that sync is deferred to post-retro task 7.6b. Until then, a spawnable orchestrator subagent holding `Agent` remains installed on this machine; this is a disclosed, accepted condition for the duration of this session, not something wave-2 alone fixes.

### Stage 6 `qa` frontmatter

`Get-ClaudeAgentFrontmatter` for `qa` (in `install/common.ps1`):

| Field | Value |
| --- | --- |
| `tools` | `Bash, Read, Grep, Glob, PowerShell` |
| `disallowedTools` | `Write, Edit, NotebookEdit` |
| `model` | `sonnet` |
| `effort` | `high` |
| `color` | `orange` |

QA may read docs and drive the app via Bash/PowerShell; it must not write product files. Orchestrator **copy-only** persists `qa/plan.md` + `qa/findings.md` + provenance. Product-source oracle forbid remains policy in `agents/qa.md` (degraded detect if a path is opened anyway).

## Claude frontmatter fields: emitted vs. deliberately rejected

This repo emits `name`, `description`, `tools`, `disallowedTools`, `model`, `effort`, `permissionMode`, `color`, `maxTurns` (subagents) and `name`, `description`, `argument-hint`, `disable-model-invocation` (skills — the last two Claude-only, see below). It deliberately **rejects** these documented Claude fields:

| Field | Why rejected |
| --- | --- |
| `memory` | Would auto-persist learnings across sessions; `agents/curator.md`'s law is "session learnings as **candidates** only (no auto-persist)" — adopting it would silently violate the role contract (D8). |
| `isolation: worktree` | Claude worktrees branch from the **default branch**, not the parent session's `HEAD`. This would silently break the builder's exact-base-SHA law and STEP 0 verification (D9) — `agents/orchestrator.md`'s Stage 4 already warns against trusting it. |
| `hooks` | Per-user shell config, not projectable Markdown; `AGENTS.md` prefers plain Markdown, and nothing failing today would be fixed by hooks (D11). |
| `mcpServers` | No MCP server is part of this playbook's design; adding one here would be scope creep unrelated to any current finding. |
| `background` | The 9-role contract is synchronous orchestrator-worker (D1); background execution has no owner in this design and would silently detach from Global Continuity. |
| `initialPrompt` | Role definitions already ARE the initial prompt via the generated frontmatter + body; a second, separate initial-prompt field would be a second source of truth (DRY violation). |
| **Orchestrator's `Agent`/`SendMessage` grant** | Not a rejected *field* but a rejected *value* for an emitted field — see the carve-out above. Permanent, deliberate exception, not a one-off patch: if the orchestrator subagent is ever spawned at all (only via the documented `/orchestrate-this` single-step advisory fallback), it returns a recommendation for the parent to act on; it must not itself dispatch further work. |

Output styles and agent teams are rejected too (not frontmatter fields, but adjacent Claude features): output styles are a global system-prompt overlay, the wrong layer for 9 distinct roles; agent teams are experimental, off by default, with documented session-resumption limitations that would regress this repo's Continuity mechanism (D10).

## Invoking

```text
/e2e
/plan-this
@sensei (agent) review this plan
```

The `/e2e` skill instructs the main session to act as Orchestrator and delegate to named subagents when available.

### Why both skills and commands (2.8)

Both `.claude/skills/<name>/SKILL.md` and `.claude/commands/<name>.md` are generated for every role, from the same `commands/<name>.md` source. **Skills are authoritative**: `disable-model-invocation`, `argument-hint`, and every other Claude-only skill capability live only on the skill surface, and "skills and commands that share a name both register `/name`; prefer skills" (above) states the precedence explicitly. Legacy commands are kept anyway, as a **considered, deliberate decision, not an oversight**: they cost nothing to generate, they preserve `/name` muscle memory from before skills existed as the primary surface, and Claude Code still resolves them if a skill is ever absent. If skill and command content ever disagree, the skill wins.

Because both surfaces are generated from the same `commands/<name>.md` task text, `install/claude.tests.ps1` (task 2.8's generation-source check) asserts the `e2e` and `e2e-resume` skill body **and** command alias body each embed the identical source task text — catching silent drift between the two copies rather than trusting them to stay in sync by convention.

## Resume / session continuity

| Field | Value |
| --- | --- |
| **Spawn path** | Main session is Orchestrator (`/e2e`). Leaves are Claude **subagents** from `~/.claude/agents/<name>.md` or project `.claude/agents/` (or Task/Agent tool equivalents). Skills under `~/.claude/skills/` are entrypoints, not Continuity roots. |
| **`resume_supported`** | **`true`** |
| **How resume works** | Claude Code resumes a subagent via the **`SendMessage`** tool, addressed by the agent's **ID or name** in the `to` field. (1) When a subagent completes, its **agent ID is returned to the parent** conversation. (2) Built-in **Explore**/**Plan** subagent types return **no agent ID** and **cannot be resumed** — only named custom subagents (this repo's 9 roles) can. (3) Subagent transcripts persist at `~/.claude/projects/{project}/{sessionId}/subagents/agent-{agentId}.jsonl`. (4) Resumption **survives a Claude Code restart** as long as the **session itself** is resumed (the same `{sessionId}` in that path). (5) `SendMessage` **refuses if a newer agent has already taken the target name** — prefer addressing by **ID**, not name, once an ID is known, to avoid a name-collision refusal retargeting the wrong live agent. |
| **`session_ref`** | Store the returned subagent **agent ID** in `session-registry.md` for the owning role/wave. Format is Claude Code's own agent-ID format (opaque string), not invented by this repo. |
| **Dead session** | A subagent spawn with no prior ID/name to resume = treat prior leaf as dead. A main-session restart **without** resuming the same Claude Code session ID = dead for Continuity purposes (transcripts are keyed by `{sessionId}`, not just by agent ID). |
| **When resume is genuinely unreachable** | Built-in Explore/Plan subagent invocations (no ID returned), or a Claude Code restart that did not resume the underlying session: fall back to **`reconstituted`** from admitted packages (`sensei-r*.md`, `advisor-r*.md`, builder reports, `fix-package-r*.md`, ledger) when the checklist is green; else **`cold_start_waived`** or **BLOCK**. Silent cold start on dependent edges is forbidden. |

### Worked example: a Serial edge reaching `resumed` on Claude

1. **Wave A (builder)** is spawned as a named `builder` subagent. On completion, Claude Code returns its **agent ID** (e.g. `agent-7f3c…`) to the orchestrator (main session).
2. The orchestrator writes a `session-registry.md` row: `role=builder`, `chain_id=wave-A`, `session_ref=agent-7f3c…`, `status=completed`, admitted.
3. **Wave B** (Serial, `depends_on: [wave-A]`, same role) is dispatched. Per Global Continuity's bridge rule, `resumed` is admitted only when the adapter has `resume_supported: true` **and** the live `session_ref` re-binds — both hold here.
4. The orchestrator calls `SendMessage` with `to: agent-7f3c…` (by **ID**, not name — avoiding any name-reuse refusal) and the Wave B task. Claude Code resumes the **same** subagent, with its prior transcript context intact at `~/.claude/projects/{project}/{sessionId}/subagents/agent-7f3c….jsonl`.
5. STEP 0 (`expected_base_sha` verification) still runs independently inside the resumed subagent — Continuity resuming the session never substitutes for the builder's own base-SHA check.
6. Outcome recorded: `continuity_mode: resumed`. Before F-3 was fixed, this exact edge could only reach `reconstituted` (adapter honesty forced it, even though the underlying mechanism was live) — this is the concrete effect of flipping `resume_supported` to `true`.

If the outer Claude Code session itself is restarted mid-chain and then **resumed** (same `{sessionId}`), step 4 still succeeds: the subagent transcript at that session's path is restored, and `SendMessage` can retarget the same agent ID.

**Source (I8 traceability):** `code.claude.com/docs/en/sub-agents` §"Resume subagents" — cited verbatim in plan.v3.md F-3: "To continue an existing subagent's work instead of starting over, ask Claude to resume it… Claude uses the `SendMessage` tool with the agent's ID or name as the `to` field"; transcripts persist at `~/.claude/projects/{project}/{sessionId}/subagents/agent-{agentId}.jsonl`; "subagent transcripts persist within their session. You can resume a subagent after restarting Claude Code by resuming the same session." This adapter does not independently re-verify that doc page against a live fetch in this wave; it restates the plan's own already-cited source rather than inventing new claims.

See `agents/orchestrator.md` **Global Continuity**.
