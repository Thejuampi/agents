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
  to tune. `model`, `temperature`, and `permission.task` are derived in
  `install/opencode.ps1` itself from `Get-RoleMeta`'s frozen `tier` and
  `opencodeTaskPolicy` fields (wave-1, `install/common.ps1`) — never hand-picked
  per role in this file.
- `.opencode/commands/<name>.md` — a thin file whose body is just
  `@commands/<name>.md`. OpenCode inlines the canonical command text at execution
  time.

Re-run `make sync-opencode` after editing `agents/*.md` or `commands/*.md`.
Generated files are gitignored; `agents/` and `commands/` remain the single source
of truth. Put personal OpenCode customizations in a root `opencode.jsonc`
(OpenCode deep-merges it with the generated `.opencode/opencode.json`); do not edit
the generated file directly, since `sync-opencode` overwrites it.

Restart OpenCode after install or sync — config is loaded once at startup.

### Permission keys

| Key | Meaning | Source |
| --- | --- | --- |
| `mode` | `primary` (runs as the main chat agent) or `subagent` (spawned by name) | `Get-OpenCodeAgentMeta` |
| `permission.read` / `edit` / `bash` / `websearch` / `webfetch` | Per-tool-class allow/ask/deny | `Get-OpenCodeAgentMeta` |
| `permission.task` | Which named agents this agent may spawn via OpenCode's Task tool | `Get-RoleMeta`'s `opencodeTaskPolicy` (see below) |
| `model` | Tier alias (`opus` for `Highest`, `sonnet` otherwise) | `Get-RoleMeta`'s `tier`, via `Get-OpenCodeModelForTier` in `install/opencode.ps1` |
| `temperature` | `0.1` for analysis/judgment roles only | Explicit list in `install/opencode.ps1` — `sensei`, `advisor`, `planner`, `reviewer` |

`tools` is **not emitted anywhere** in the generated config — OpenCode's own
agent-configuration docs (`opencode.ai/docs/agents`) treat `permission` as the
current mechanism and describe `tools` as the superseded one; `permission`
already expresses everything this repo's roles need (per-tool-class allow/ask/deny
plus `task`), so there is nothing left for a separate `tools` list to add.

### `permission.task` — the identity rule, in config (F-7, task 5.1)

README's Identity hard rule ("never spawn `orchestrator`; only leaf specialists
spawn nothing") is now enforced by OpenCode's own permission engine, not prose
alone. Every entry is explicit — no wildcard-first ordering trick — because
OpenCode evaluates `permission.task` as glob rules and "When set to `deny`, the
subagent is removed from the Task tool description entirely, so the model won't
attempt to invoke it" (`opencode.ai/docs/agents` §"Task permissions"). A real
generated block (`.opencode/opencode.json`, 2026-08-06):

```json
"orchestrator": {
  "permission": {
    "task": {
      "advisor": "allow",
      "builder": "allow",
      "curator": "allow",
      "planner": "allow",
      "qa": "allow",
      "refiner": "allow",
      "reviewer": "allow",
      "sensei": "allow"
    }
  }
}
```

Every leaf agent (`refiner`, `planner`, `sensei`, `advisor`, `builder`,
`reviewer`, `curator`, `qa`) gets:

```json
"permission": { "task": { "*": "deny" } }
```

**Derivation, not hand-authoring:** `install/opencode.ps1` builds the orchestrator's
allow-list by enumerating the real `agents/*.md` file set and keeping every name
whose `Get-RoleMeta -Name <role>` returns `opencodeTaskPolicy: 'leaf'` — it does not
hard-code the eight names. A 10th role added later via the amendment protocol
(`plan.v3.md` §1.4a) that ships an `agents/<role>.md` file and a `Get-RoleMeta` row
is picked up automatically on the next `make sync-opencode`, closing the "silently
omitted" failure mode named in task 5.1's acceptance criteria. `orchestrator`
itself is excluded from every allow-list (including its own) because its
`opencodeTaskPolicy` is `'orchestrator'`, not `'leaf'` — it never appears as a
value anyone may target.

**Orchestrator dispatch-risk scoping note (plan.v3.md §1.4a, restated verbatim
by requirement of this wave's documentation deliverable):** OpenCode's
`opencodeTaskPolicy: orchestrator` (targets the 8 leaves via `permission.task`) is
native, intended task-dispatch — not the same risk class as Claude/VS Code's
general-purpose dispatch tools. This distinction is stated explicitly: unlike
Claude's `Agent` tool or VS Code's `agents:` handoff list (which are
general-purpose "spawn anything" primitives that had to be hand-restricted to
exclude the orchestrator role itself — see `adapters/claude.md`'s "considered and
rejected" table), `permission.task` is OpenCode's own purpose-built,
per-target-name permission surface. Deriving it from `opencodeTaskPolicy` is
therefore safe and requires no hand-authored carve-out the way Claude/VS Code's
orchestrator tool grants do. If a future OpenCode capability introduces an
equivalent general-purpose dispatch risk, it gets the same hand-authored treatment
Claude/VS Code use, and the deviation from this note is disclosed at that time.

### Stage 6 `qa` permissions

`Get-OpenCodeAgentMeta` for `qa` (in `install/common.ps1`):

| Permission | Value | Why |
| --- | --- | --- |
| `edit` | `deny` | Product tree write forbidden; Orchestrator copy-only persists `qa/*` |
| `bash` | `allow` | CLI / app / attach probe |
| `read` | **not denied** | Docs and operator runbooks must be readable for black-box planning |

There is **no** `read = 'deny'` on QA. Product-source path deny is policy in `agents/qa.md` (degraded + source-citation process fail when the harness cannot express path-class deny). Eligibility: prefer path deny when OpenCode supports it; else `degraded`.

### Skills: read natively, not duplicated (F-8, task 5.4)

OpenCode discovers skills and rules from locations it already owns — this repo
ships **no** `.opencode/skills` directory, because doing so would duplicate what
OpenCode already finds for free. Per `opencode.ai/docs/skills` and
`opencode.ai/docs/rules`, the six discovery paths are:

| # | Path | Kind |
| --- | --- | --- |
| 1 | `.claude/skills` | Skills (project) |
| 2 | `~/.claude/skills` | Skills (personal) |
| 3 | `.agents/skills` | Skills (project) |
| 4 | `~/.agents/skills` | Skills (personal) |
| 5 | `CLAUDE.md` | Rules (project) |
| 6 | `~/.claude/CLAUDE.md` | Rules (personal) |

This repo's `make install-claude` / `make sync-claude-global` already populate
`~/.claude/skills/`; OpenCode reads that projection with zero extra work. There is
no dedicated OpenCode skills projection to keep in sync, and none should be added.

**`AGENTS.md` / `CLAUDE.md` precedence:** OpenCode reads `AGENTS.md` natively as
project rules (`opencode.ai/docs/rules`) — this is why the generated
`.opencode/opencode.json` does not add `AGENTS.md` to an `instructions` list (it
would duplicate context OpenCode already loads). This repo does not generate a
`CLAUDE.md` file, so there is no dual-authorship conflict between `AGENTS.md` and
`CLAUDE.md` to arbitrate for this project. If an operator's personal
`~/.claude/CLAUDE.md` also exists, this session did not independently verify
OpenCode's merge/precedence order between it and a project's own `AGENTS.md` (no
network access from the builder role that authored this section) — stated here as
an open gap rather than an asserted order (I16).

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

## Commands: `subtask: true` on leaves only (task 5.3)

Every generated `.opencode/commands/<name>.md` for a leaf specialist
(`build-this`, `curate-this`, `orchestrate-this`, `plan-this`, `qa-this`,
`refine-this`, `review-this`) carries `subtask: true`, so OpenCode may run it as a
subtask instead of only in the primary context. `e2e` and `e2e-resume` deliberately
do **not** carry `subtask: true`: both must run as the main agent (README /
`agents/orchestrator.md` Identity hard rule — a nested orchestrator loses context
and forks a second E2E brain), so they are excluded by name in
`install/opencode.ps1`, not inferred from any other field.

`orchestrate-this` is the one exception worth naming: it maps to `agents/orchestrator.md`
but is the documented single-step advisory fallback (`plan.v3.md` §1.4a) — a
one-shot recommendation for the parent conversation to act on, not a pipeline run
that dispatches further work — so it is safe as a subtask, unlike `e2e`/`e2e-resume`.

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
