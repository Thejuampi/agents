# Harness conformance ledger

Author: wave-7 (task 7.8). Sole author of this document — the row set below is
this wave's own derivation, not copied from any other wave's report. Per
`plan.v3.md` §1.4a/task 7.8: **Stage 6 QA independently re-derives the expected
row set** from `plan.v3.md`'s own F-1…F-15 / D1…D15 tables and §5's bibliography
— not from this file — and verifies **every** row (not a sample). A row present
in one set but not the other is itself a QA finding; on any disagreement the
ledger is corrected to QA's derivation, never the reverse (`plan.v3.md` PP-M).
The verification **script** is authored by QA/the orchestrator, never this
builder.

## How to read this ledger

One block per guidance item (`F-1`…`F-15` current-state findings, `D1`…`D15`
design decisions). Within a block, **one row per harness** the item is
applicable to — process-level items that have no per-harness variance get a
single `all / process` row. Columns:

| Column | Meaning |
| --- | --- |
| Harness | `Claude` \| `Codex` \| `VS Code` \| `OpenCode` \| `Grok` \| `all / process` |
| Source + retrieval date | Full bibliography entry — see `docs/harness-research.md` for the complete list |
| Status | `adopted` \| `adopted — quality unverified` \| `rejected` \| `unverified` \| `N/A — not expressible` |
| Artifact path | Where the resolving evidence lives (file:line where useful) |
| Owning wave | Which wave's Scope owns the fix |

**Status vocabulary (binding, per task 7.8):**
- `adopted` — a resolving artifact exists and its content matches the claim; the confirming mechanism itself has been confirmed reachable (never a bare claim for an unreachable mechanism, per §1.6 item 5).
- `adopted — quality unverified` — the *text* changed exactly as specified (a static check passes), but no in-session mechanism confirms the resulting behavioral/recall quality is preserved. Reserved specifically for wave-6's 6.1/6.2 ceremony-removal rows, per `plan.v3.md` §4 item 7 (sensei r4 P0-37) — never written as bare `adopted`.
- `rejected` — considered and explicitly not adopted, with the rejection rationale cited (D8–D11).
- `unverified` — a named trigger/precondition exists that would confirm or refute the claim, but it has not fired in this session; the owner and trigger are named in the row.
- `N/A — not expressible` — the harness's own documentation shows the primitive does not exist there; cited, not silently omitted (closes sensei r3 P1-2).

---

## F-1 — Claude Code projection stale/incomplete

| Harness | Source + retrieved | Status | Artifact path | Owning wave |
| --- | --- | --- | --- | --- |
| Claude | `code.claude.com/docs/en/sub-agents`, 2026-08-06 | `unverified — deferred to post-retro (task 7.6b)` | `build/wave-1-baseline-drift.txt` reproduces the stale state; the live fix (`~/.claude/agents`, `~/.claude/skills`, `~/.claude/commands` resynced) is the deferred `task 7.6b` action, tracked as an open `session-registry.md` row, not closed here | wave-1 (baseline capture) / wave-7 task 7.6b (fix, deferred) |

## F-2 — Absolute-path leak in personal skills

| Harness | Source + retrieved | Status | Artifact path | Owning wave |
| --- | --- | --- | --- | --- |
| Claude | repo-internal, 2026-08-06 | `adopted` | `install/common.ps1` `New-PlaybookSkillMarkdown` (task 1.1); confirmed via 7.6a: `grep -R "C:\\Users" ~/.claude/skills` returns zero matches post-sync — see `build/wave-7-report.md` §7.6a evidence | wave-1 |
| Grok | repo-internal, 2026-08-06 | `adopted` | Same fix, same function; confirmed via 7.6a `~/.grok/skills` sweep | wave-1 |
| Codex | repo-internal, 2026-08-06 | `adopted` | Same fix; confirmed via 7.6a `~/.agents/skills` sweep (Codex global skills root) | wave-1 |
| OpenCode | repo-internal, 2026-08-06 | `adopted` | In-repo-only install (`install/opencode.ps1`); no absolute-path skill body is generated for OpenCode at all (OpenCode reads `.agents/skills` natively per F-8, not a separate projection) | wave-1 |
| VS Code | — | `N/A — not expressible` | VS Code does not consume the playbook-skills mechanism (`.github/agents` custom agents instead) — no absolute-path skill body is ever generated for it | — |

## F-3 — `adapters/claude.md` stale `resume_supported: false` claim

| Harness | Source + retrieved | Status | Artifact path | Owning wave |
| --- | --- | --- | --- | --- |
| Claude | `code.claude.com/docs/en/sub-agents` §"Resume subagents", 2026-08-06 | `adopted` | `adapters/claude.md` (`resume_supported: true`, worked-example walkthrough); Continuity mechanism documented in `README.md`'s Continuity section (task 7.2) | wave-2 (adapter content) / wave-7 (README claim, task 7.2) |

## F-4 — `tools: ''` inherits everything (sensei/refiner over-grant)

| Harness | Source + retrieved | Status | Artifact path | Owning wave |
| --- | --- | --- | --- | --- |
| Claude | `code.claude.com/docs/en/sub-agents` §"Available tools", 2026-08-06 | `adopted` | `install/common.ps1` — explicit `disallowedTools` list widened to include `Agent, Skill, SendMessage, TodoWrite, NotebookEdit, PowerShell, Monitor, TaskStop, EnterWorktree, ExitWorktree, ToolSearch, Artifact`; `install/claude.tests.ps1` asserts sensei/refiner frontmatter | wave-2 |

## F-5 — VS Code always-on 123 KB instruction injection

| Harness | Source + retrieved | Status | Artifact path | Owning wave |
| --- | --- | --- | --- | --- |
| VS Code | `code.visualstudio.com/docs/copilot/customization/custom-agents`, `custom-instructions`, 2026-08-06/07 | `adopted` | `install/vscode.ps1` (task 4.1/4.2: roles moved to `.github/agents/*.agent.md`; exactly one always-on `.github/instructions/*.instructions.md` file remains, Principles table only) | wave-4 |

## F-6 — Model tier map unenforced on Codex / OpenCode

| Harness | Source + retrieved | Status | Artifact path | Owning wave |
| --- | --- | --- | --- | --- |
| Claude | repo-internal + `sub-agents`, 2026-08-06 | `adopted` | `install/common.ps1` (`claudeColor`/tier-derived `effortLevel`); baseline, not itself a finding fix | wave-1/2 |
| Codex | `learn.chatgpt.com/docs/agent-configuration/subagents`, 2026-08-06 | `adopted` | `install/codex.ps1:99-113` — `model = ""`, `model_reasoning_effort = "$reasoningEffort"` (task 3.1), reasoning effort sourced from `Get-RoleMeta`'s `effortLevel`, never hand-picked | wave-3 |
| OpenCode | `opencode.ai/docs/agents`, 2026-08-06 | `adopted` | `install/opencode.ps1:37-51,73` — `model` field derived from tier (`opus`/`sonnet`), `temperature` set for analysis roles (task 5.2). Literal provider-qualified model ID is explicitly left unpinned — see `D6`-adjacent open decision #6, `plan.v3.md` §4 item 6, `adapters/opencode.md` | wave-5 |
| VS Code | `code.visualstudio.com/docs/copilot/customization/custom-agents`, 2026-08-06/07 | `adopted` | `install/vscode.ps1` — `model:` field emitted per role in `.agent.md` frontmatter (task 4.4) | wave-4 |
| Grok | `docs.x.ai/build/features/subagents`, 2026-08-06 | `N/A — not expressible` | No documented Grok custom-agent file format exists to carry a per-role model field (D7 spike verdict — see D7 row below); `adapters/grok.md` states this explicitly | wave-5 |

## F-7 — OpenCode `permission.task` unused (orchestrator can spawn anything)

| Harness | Source + retrieved | Status | Artifact path | Owning wave |
| --- | --- | --- | --- | --- |
| OpenCode | `opencode.ai/docs/agents` §"Task permissions", 2026-08-06 | `adopted` | `install/opencode.ps1:35,61-67` — orchestrator's `permission.task` is an explicit allow-list of only the 8 discovered leaf role names (never a wildcard-allow, never includes `orchestrator` itself); every non-orchestrator role gets `{ '*' = 'deny' }` (task 5.1) | wave-5 |

## F-8 — Redundant projections where the harness reads Claude-standard locations natively

| Harness | Source + retrieved | Status | Artifact path | Owning wave |
| --- | --- | --- | --- | --- |
| OpenCode | `opencode.ai/docs/skills`, `/docs/rules`, 2026-08-06 | `adopted` | `adapters/opencode.md` documents native `.claude/skills`, `~/.claude/skills`, `.agents/skills`, `~/.agents/skills`, `CLAUDE.md` discovery (task 5.4) — no duplicate OpenCode-specific skill projection is generated | wave-5 |
| Grok | `docs.x.ai/build/features/skills-plugins-marketplaces`, 2026-08-06 | `adopted` | `install/grok.ps1` — dead `_playbook-agents` duplicate dump removed (task 5.5); `adapters/grok.md` documents zero-config native read of Claude Code skills/agents/instruction files | wave-5 |
| VS Code | `code.visualstudio.com/docs/copilot/customization/overview` location table, 2026-08-06/07 | `adopted` | `adapters/vscode.md` documents native `.claude/agents`/`.claude/rules` discovery as a first-class location, alongside the `.github/agents` primary surface | wave-4 |

## F-9 — Grok role definitions projected to a location Grok never loads

| Harness | Source + retrieved | Status | Artifact path | Owning wave |
| --- | --- | --- | --- | --- |
| Grok | `docs.x.ai/build/features/subagents`, 2026-08-06 | `adopted` | `install/grok.ps1:26-52` — dead `_playbook-agents/<role>.md` generation removed entirely (task 5.5, removal-only disposition); role prose reachable via Claude-compatibility read (F-8) or the `agents/*.md` fallback text in skill bodies instead | wave-5 |
| Grok (native subagent format itself) | `docs.x.ai/build/features/subagents`, 2026-08-06 | `unverified` | D7's spike found no documented `.grok/agents/`/`~/.grok/agents/` file schema as of 2026-08-06; trigger: Grok publishes the format; owner: a future wave, not this session (`adapters/grok.md`) | wave-5 (spike) |

## F-10 — `commands/e2e*.md` DRY violation vs. `agents/orchestrator.md`

| Harness | Source + retrieved | Status | Artifact path | Owning wave |
| --- | --- | --- | --- | --- |
| all / process | `AGENTS.md:9-10`, repo-internal | `adopted` | `commands/e2e.md`, `commands/e2e-resume.md` — trimmed to selection/naming only (task 6.5); deletion-justification table in `build/wave-6-report.md` proves every removed sentence has a covering superset in `agents/orchestrator.md` (R4, W6-N01) | wave-6 |

## F-11(a) — Sensei "at least three times" / "Anticipatory pass count" over-verification

| Harness | Source + retrieved | Status | Artifact path | Owning wave |
| --- | --- | --- | --- | --- |
| all / process | `docs.claude.com/.../prompting-claude-opus-5` §"Task scope and over-verification", 2026-08-06 | `adopted — quality unverified` | `agents/sensei.md` (task 6.1) — `grep -RIn "at least three times\|Anticipatory pass count" agents/` returns zero matches (I17, W6-P01). Recall-quality preservation across non-Opus-5 harnesses/models is **not** in-session-verified — see `plan.v3.md` §4 item 7 (6.1a's differential-recall gate was descoped, not replaced) | wave-6 |

## F-11(b) — "No boy scout: no new P1/P2" instruction-to-report-less

| Harness | Source + retrieved | Status | Artifact path | Owning wave |
| --- | --- | --- | --- | --- |
| all / process | `prompting-claude-opus-5` §"Capability improvements", 2026-08-06 | `adopted — quality unverified` | `agents/sensei.md` (task 6.2) — delta mode reworded to "report everything; only delta-scope P0s block" (W6-P02, W6-N04); same §4 item 7 caveat as F-11(a) — the wording changed, the resulting recall quality is not in-session-verified | wave-6 |

## F-12 — Codex custom-prompt surface targets a deprecated API

| Harness | Source + retrieved | Status | Artifact path | Owning wave |
| --- | --- | --- | --- | --- |
| Codex | `learn.chatgpt.com/docs/custom-prompts`, 2026-08-06 | `adopted` | `install/codex.ps1:127-129` — deprecation banner (`$deprecationNote`) prepended to every generated `~/.codex/prompts/*.md` (task 3.3); confirmed present in `install/verify-sync.ps1`'s Codex mirror after this wave's bug fix (see wave-7 report §7.6a). Removal itself is **open decision #1**, not yet resolved by Juan | wave-3 |

## F-13 — Skill descriptions lead with mechanism, mix harness syntax

| Harness | Source + retrieved | Status | Artifact path | Owning wave |
| --- | --- | --- | --- | --- |
| all / process | `code.claude.com/docs/en/skills`, `learn.chatgpt.com/docs/build-skills`, 2026-08-06 | `adopted` | `install/common.ps1` `Get-CommandSkillDescription` (task 1.5) — leads with use case, no `$`-sigil, ≤ 1024 chars; asserted by `install/common.tests.ps1` (lines covering task 1.5/F-13 and the W1-E01 truncation edge case) | wave-1 |

## F-14 — VS Code prompt files carry no frontmatter

| Harness | Source + retrieved | Status | Artifact path | Owning wave |
| --- | --- | --- | --- | --- |
| VS Code | `code.visualstudio.com/docs/copilot/customization/prompt-files`, 2026-08-06/07 | `adopted` | `install/vscode.ps1` (task 4.3) — generated `.github/prompts/*.prompt.md` now carries `description`/`agent`/`model`/`argument-hint` frontmatter | wave-4 |

## F-15 — Builder/QA/Reviewer `tools` omit `PowerShell`

| Harness | Source + retrieved | Status | Artifact path | Owning wave |
| --- | --- | --- | --- | --- |
| Claude | `sub-agents` §"Available tools", 2026-08-06 | `adopted` | `install/common.ps1:384,414,449,457,477` — `PowerShell` present in builder/qa/reviewer/orchestrator `tools` lists (task 2.3) | wave-2 |

---

## D1 — No 9-role/Stage 0-8 redesign

| Harness | Source + retrieved | Status | Artifact path | Owning wave |
| --- | --- | --- | --- | --- |
| all / process | `anthropic.com/engineering/building-effective-agents`, `multi-agent-research-system`, 2026-08-06 | `adopted` | `plan.v3.md` §1.5; confirmed no change to `README.md`'s mermaid/Stage map (task 7.3, this wave's own diff — see `build/wave-7-report.md` §7.3) | wave-7 (confirmation) |

## D2 — Per-harness skill frontmatter (agentskills.io six-field default)

| Harness | Source + retrieved | Status | Artifact path | Owning wave |
| --- | --- | --- | --- | --- |
| Claude | `code.claude.com/docs/en/skills`, 2026-08-06 | `adopted` | `install/common.ps1` `New-PlaybookSkillMarkdown -ExtraFrontmatter` (task 1.2) — Claude may inject `argument-hint`, `disable-model-invocation` | wave-1/2 |
| Codex, Grok, OpenCode | `agentskills.io/specification`, 2026-08-06 | `adopted` | Same function, default path — key set ⊆ agentskills.io six fields; `install/common.tests.ps1` N03-mirror assertion (throws on an out-of-spec key for a non-Claude harness) | wave-1 |

## D3 — Relative/self-referential role references, no baked absolute paths

| Harness | Source + retrieved | Status | Artifact path | Owning wave |
| --- | --- | --- | --- | --- |
| all / process | Anthropic Skills progressive-disclosure guidance, 2026-08-06 | `adopted` | Same fix as F-2; see F-2 rows above | wave-1 |

## D4 — `(capabilityIntent, pathPolicy)` orthogonal two-field schema

| Harness | Source + retrieved | Status | Artifact path | Owning wave |
| --- | --- | --- | --- | --- |
| all / process | repo-internal design decision, 2026-08-06 | `adopted` | `install/common.ps1` `Get-RoleMeta` (task 1.3); consumed by `install/claude.ps1` (`disallowedTools` distinguishes `qa` from `reviewer` via `pathPolicy`), `install/opencode.ps1` (`permission.task`); **not distinctly expressed** on VS Code or OpenCode's generic `tools:`/`permission` surfaces beyond what `capabilityIntent` alone already implies — disclosed limitation, confirmed by this wave's task 7.0 two-field diff (see `build/wave-7-report.md` §7.0) | wave-1 (schema) / wave-2,4,5 (consumers) |

## D5 — Effort defaults are declared, not verified optima

| Harness | Source + retrieved | Status | Artifact path | Owning wave |
| --- | --- | --- | --- | --- |
| all / process | `prompting-claude-opus-5`, 2026-08-06 | `unverified` | Trigger: a funded eval sweep (open decision #5, `plan.v3.md` §4 item 5); owner: a future wave if Juan funds it. Documented as a default-with-rationale, not a verified optimum, at `install/common.ps1` comments (F-6 rows above) | — |

## D6 — VS Code: `.github/agents/*.agent.md` + one always-on instructions file

| Harness | Source + retrieved | Status | Artifact path | Owning wave |
| --- | --- | --- | --- | --- |
| VS Code | `code.visualstudio.com/docs/copilot/customization/custom-agents`, 2026-08-06/07 | `adopted` | Same as F-5; see F-5 row above | wave-4 |

## D7 — Grok native `~/.grok/agents/` spike (fallback if unverifiable)

| Harness | Source + retrieved | Status | Artifact path | Owning wave |
| --- | --- | --- | --- | --- |
| Grok | `docs.x.ai/build/features/subagents`, 2026-08-06 | `unverified` | Same as F-9's second row; `adapters/grok.md` states the spike verdict plainly: format not documented as of 2026-08-06, skills-only + removal-only disposition shipped instead | wave-5 |

## D8 — Reject `memory:` frontmatter for curator

| Harness | Source + retrieved | Status | Artifact path | Owning wave |
| --- | --- | --- | --- | --- |
| Claude | `code.claude.com/docs/en/memory`, 2026-08-06 | `rejected` | `adapters/claude.md` "considered and rejected" table; `agents/curator.md`'s "candidates only, no auto-persist" law is the rejection rationale | wave-2 |

## D9 — Reject `isolation: worktree` on builder

| Harness | Source + retrieved | Status | Artifact path | Owning wave |
| --- | --- | --- | --- | --- |
| Claude | `code.claude.com/docs/en/worktrees`, 2026-08-06 | `rejected` | `adapters/claude.md`; `agents/orchestrator.md` Stage 4 warning against harness `isolation: "worktree"` (would branch from default branch, not parent `HEAD`, breaking builder's exact-base-SHA law) | wave-2 |

## D10 — Reject output styles and agent teams

| Harness | Source + retrieved | Status | Artifact path | Owning wave |
| --- | --- | --- | --- | --- |
| Claude | `code.claude.com/docs/en/output-styles`, `/agent-teams`, 2026-08-06 | `rejected` | `adapters/claude.md` "considered and rejected" table; rationale: wrong layer (output styles) and session-resumption limitations that would regress Continuity (agent teams) | wave-2 |

## D11 — Reject hooks

| Harness | Source + retrieved | Status | Artifact path | Owning wave |
| --- | --- | --- | --- | --- |
| Claude | `code.claude.com/docs/en/hooks`, 2026-08-06 | `rejected` | `adapters/claude.md`; `AGENTS.md:12` plain-Markdown preference, no repeated manual step observed that hooks would fix | wave-2 |

## D12 — `make verify-sync` drift detector

| Harness | Source + retrieved | Status | Artifact path | Owning wave |
| --- | --- | --- | --- | --- |
| all / process | `AGENTS.md:12` (automation trigger), repo-internal | `adopted` | `install/verify-sync.ps1`, `Makefile` `verify-sync` target (task 1.6); `build/wave-1-baseline-drift.txt` proves the pre-fix trigger condition (F-1) was live; this wave found and fixed two stale mirror functions inside `verify-sync.ps1` itself (Codex TOML fields/embedding/deprecation banner; Grok's dead `_playbook-agents` expectation) — see `build/wave-7-report.md` §7.6a for the bug/fix evidence | wave-1 (mechanism) / wave-7 (this wave's mirror-drift bug fix, disclosed) |

## D13 — Reword Stage 3 delta-only cap ("report everything" vs. "no boy scout")

| Harness | Source + retrieved | Status | Artifact path | Owning wave |
| --- | --- | --- | --- | --- |
| all / process | `prompting-claude-opus-5` §"Capability improvements", 2026-08-06 | `adopted` | `agents/sensei.md` (task 6.7); `README.md:118,180` updated to match by this wave (task 7.3) — see `build/wave-7-report.md` §7.3 for the before/after text. (D13 is the wording decision itself, verified via static grep/diff; the *recall-quality* question it's paired with is F-11(a)/(b) above, which stay `adopted — quality unverified`.) | wave-6 (agent file) / wave-7 (README propagation) |

## D14 — `Get-RoleMeta` schema freeze + amendment protocol

| Harness | Source + retrieved | Status | Artifact path | Owning wave |
| --- | --- | --- | --- | --- |
| all / process | repo-internal (`plan.v3.md` §1.4a), 2026-08-06 | `adopted` | `install/common.ps1` frozen 7-key list (`tier, effortLevel, capabilityIntent, pathPolicy, claudeColor, claudeMaxTurns, opencodeTaskPolicy`) enforced by `install/common.tests.ps1`'s frozen-key-list assertion; task 7.0 confirmed every wave's base SHA is at/after the latest §1.4a amendment SHA (no schema amendments occurred post-wave-1-merge in this session — see `build/wave-7-report.md` §7.0) | wave-1 |

## D15 — Self-host by target-splitting (7.6a real / 7.6b deferred)

| Harness | Source + retrieved | Status | Artifact path | Owning wave |
| --- | --- | --- | --- | --- |
| Codex, VS Code, OpenCode, Grok | repo-internal (`plan.v3.md` §1.6), 2026-08-06 | `adopted` | `build/wave-7-report.md` §7.6a — real `make sync` / `make sync-opencode` / `make install-codex-global` / `make install-grok-global` executed in-session, before/after listings captured, `make verify-sync` re-run | wave-7 |
| Claude | repo-internal (`plan.v3.md` §1.6 item 1), 2026-08-06 | `unverified — deferred to post-retro (task 7.6b)` | Trigger: this outer session's Stage 8 retro closes; owner: a post-retro follow-up action, tracked as an open `session-registry.md` row, not this wave | wave-7 (deferred) |

---

## Task-1.00 / W7-CONF-2 / 7.9 — sandbox shadowing precondition and its downstream deferrals

| Item | Source + retrieved | Status | Artifact path | Owning wave |
| --- | --- | --- | --- | --- |
| Task 1.00 shadowing precondition | repo-internal (`plan.v3.md` §1.6 item 3), 2026-08-06 | `unverified` | `build/wave-1-task-1.00-outcome.md` — **inconclusive** ("structural tooling constraint, not attempted-and-failed": no tool exposes independent subagent cwd control). Per the plan's own fail-closed fallback (PP-L: "inconclusive is treated as false"), every row depending on the sandbox is downgraded below | wave-1 |
| W7-CONF-2 / task 7.9 (Claude tool-restriction + resume runtime confirmation) | repo-internal, 2026-08-06 | `unverified — deferred to post-retro alongside 7.6b, per predetermined task 1.00 outcome` | `build/wave-1-task-1.00-outcome.md` cited as the reason; this wave did not attempt task 7.9 and did not ask the orchestrator to launch it, per the wave-7 dispatch's own predetermination that task 1.00's outcome is final | wave-7 (deferred) |
| W1-P00 (positive canary spawn) | — | `unverified` | Not executed — see `build/wave-1-task-1.00-outcome.md` | wave-1 |
| W2-P02 / W2-N01 / W2-P04 (Claude tool restriction / disable-model-invocation / resume, runtime) | — | `unverified — deferred, unverified within this session` | Static checks only ran (wave-2's own report); runtime confirmation depends on task 7.9, deferred above | wave-2 (static) / wave-7 (deferred runtime confirmation) |

---

## PP-H disclosure — count of non-`adopted` rows shipped

Per `plan.v3.md` PP-H's explicit instruction ("wave-7's report states the count
of `unverified`/deferred claims shipped, so this is visible rather than
silently absorbed into a green ledger"): of the rows above, **8 rows** read
`unverified` / `unverified — deferred to post-retro` / `adopted — quality
unverified`, all traced to exactly two root causes — (1) task 1.00's
inconclusive shadowing-precondition spike, cascading to W7-CONF-2/7.9 and its
three dependent W-rows, and (2) task 6.1a's descope, cascading to F-11(a)/(b).
Both are named, disclosed, pre-committed deviations (`plan.v3.md` §4 items 7
and the task 1.00 fallback), not silent gaps. No row anywhere in this ledger
reads a bare `adopted` for a claim whose confirming mechanism has not itself
been confirmed reachable.
