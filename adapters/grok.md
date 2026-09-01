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

## What Grok reads for free (F-8, task 5.6)

Grok Build is documented as fully Claude-Code-compatible with zero configuration:
"Grok is fully compatible with Claude Code with zero configuration needed. Grok
automatically reads Claude Code marketplaces, plugins, skills, MCPs, agents,
hooks, and instruction files" (`docs.x.ai/build/features/skills-plugins-marketplaces`).
It additionally reads the harness-neutral `~/.agents/` tree.

| Source | Grok reads it via | This repo already populates it? |
| --- | --- | --- |
| `~/.claude/skills/<name>/SKILL.md` | Claude Code compatibility (zero config) | Yes — `make install-claude-global` / `make sync-claude-global` |
| `~/.claude/agents/<role>.md` | Claude Code compatibility (zero config) | Yes — same Claude installer |
| `CLAUDE.md` / `~/.claude/CLAUDE.md` | Claude Code compatibility (zero config) | N/A — this repo does not generate a `CLAUDE.md` |
| `~/.agents/skills/` | Native, harness-neutral (`docs.x.ai/build/features/skills-plugins-marketplaces`) | Not yet projected by this repo's installers |
| `~/.agents/commands/` | Native, harness-neutral | Not yet projected by this repo's installers |
| `AGENTS.md` (project rules) | Native (`docs.x.ai/build/features/project-rules`) | Yes — this repo's own root `AGENTS.md` |

**Why the dedicated `~/.grok/skills/` projection is retained anyway (not just
relying on the Claude Code compatibility path above):** a Grok-only operator —
someone who has never run `make install-claude-global` and has no `~/.claude/`
tree at all — would otherwise get zero skills. `make sync-grok-global` is kept so
`/e2e`, `/plan-this`, etc. work standalone on a Grok-only machine (this is
`plan.v3.md` §4 open decision #2, still pending Juan: keep-with-rationale is the
position this wave ships; dropping it in favor of pure compatibility remains an
option for a future cycle).

## Agent references — 5.5 spike verdict: format not documented (F-9)

**Verdict, stated as fact-or-unknown per this wave's acceptance criteria: Grok's
`.grok/agents/` / `~/.grok/agents/` subagent-file format is not documented as of
2026-08-06.** `docs.x.ai/build/features/subagents` documents that Grok *has* a
subagent concept and *reads* agent definitions, but this session found no
citable schema for the on-disk file format at that location (frontmatter keys,
required fields, discovery rules). Per this wave's explicit instruction,
**guessing a format is not acceptable**, so no `~/.grok/agents/` projection is
shipped.

The prior `_playbook-agents` reference dump (`~/.grok/skills/_playbook-agents/<role>.md`,
never auto-loaded by Grok — F-9) is **removed**, not replaced with an unverified
guess. `install/grok.ps1` no longer generates it, and running the installer
against a target that still has the old dump purges it automatically (`Clear-ManifestHarness`
runs before regeneration — see the upgrade-path note below).

**Fallback: Claude Code compatibility.** Since Grok already reads `~/.claude/agents/`
with zero configuration (see the table above), the 9 canonical roles are already
reachable as real Grok subagent-equivalent definitions on any machine that also
runs `make install-claude-global` — no separate Grok-native projection is needed
to reach that outcome today. Each generated skill body
(`New-PlaybookSkillMarkdown` in `install/common.ps1`) already instructs Grok to
spawn the named role or, if no named-agent concept resolves, load
`agents/<role>.md` directly — this fallback instruction is unchanged by this wave.

**Upgrade path (W5-R02):** `install/grok.ps1` now calls `Clear-ManifestHarness`
for the `'grok'` harness before regenerating, so a target directory that still
has a manifest entry for the old `_playbook-agents` dump has those files deleted
on the next `make sync-grok` / `make sync-grok-global` run — the stale directory
does not outlive the code that produced it, and no error is raised whether or not
the old entry exists.

## Invoking

```text
/e2e
/plan-this
/sensei-this
/advisor-this
$e2e
```

## Resume / session continuity (task 5.7 — corrected)

Grok Build documents **session-level** resume for the main CLI conversation
(`docs.x.ai/build/features/sessions`): `grok --resume`, `-c` (continue most
recent), `/resume` (interactive picker), and `--fork-session` (branch a session
without mutating the original). None of that page documents resuming an
individual **leaf subagent** run by id — `docs.x.ai/build/features/subagents`
describes spawning subagents but not a resume-by-id API for one. The previous
revision of this adapter conflated the two and asserted a `resume_from` /
`session_ref` leaf-resume mechanism that is **not** citable against either page —
that claim is retracted here.

| Field | Value |
| --- | --- |
| **Spawn path** | Main agent runs `/e2e` (or `$e2e`) as Orchestrator in the main Grok session. Leaf specialists are spawned via `spawn_subagent` (or equivalent general-purpose subagent) with the agent prompt from `agents/*.md` / the Claude Code compatibility fallback (`~/.claude/agents/`). There is no separate named-agent registry like Claude's `~/.claude/agents/` that Grok itself defines (it borrows Claude's). |
| **Documented: main-session resume** | **`grok --resume` / `-c` / `/resume` / `--fork-session`** restore or fork the **main CLI session** (`docs.x.ai/build/features/sessions`). This supports Global Continuity's session-level re-entry — e.g. reopening a stopped `/e2e` run in the same main conversation — but is orthogonal to resuming any one leaf subagent. |
| **Undocumented: leaf-subagent resume** | No citable API resumes a specific prior leaf subagent run by id. Do **not** invent a `resume_from` / `session_ref` mechanism (retracted above). |
| **`resume_supported`** | **Qualified: `true` for the main-session hop (documented), `false` for any individual leaf-subagent hop (undocumented).** Record which one applies per Continuity edge, never a bare `true`. |
| **`session_ref`** | Only meaningful for the main-session resume mechanisms above (`grok --resume <id>` / `/resume` picker). Not a per-leaf-subagent handle — there is none. |
| **Dead session** | Main session unresumable, or a leaf subagent's continuation cannot be verified from artifacts → run Global Continuity's reconstitution checklist (or `cold_start_waived` / **BLOCK**). Never silent cold start on a dependent edge. |
| **When leaf resume is needed** | Outcome is **`reconstituted`** from session artifacts under `.agents/workspace/tmp/e2e/<slug>/` (checklist green) or **`cold_start_waived`** / **BLOCK** — never label reconstituted leaf work as `resumed`; `resumed` is reserved for the documented main-session mechanisms above. |

Orchestrator still owns Continuity law (`agents/orchestrator.md`); this adapter only states harness honesty.

Stage 6 black-box QA (`qa`) has no native path deny on Grok — follow `agents/qa.md` policy (docs OK, product source not an oracle) and orchestrator degraded-mode integrity.
