# VS Code Adapter

VS Code + GitHub Copilot load **custom agents**, **prompt files**, and **instructions files** from well-known directories under `.github/`. As of wave-4 (plan.v3.md D6/F-5), the 9 roles project to native **custom agents** (`.github/agents/<role>.agent.md`) — not to 9 always-on instruction files.

**Verified against VS Code docs 2026-08-06/07:** `code.visualstudio.com/docs/copilot/customization/custom-agents`, `.../custom-instructions`, `.../prompt-files`, `code.visualstudio.com/docs/agents/concepts/tools`, `.../run/tools` — all fetched live during this wave (dated `8/5/2026` on the pages themselves); every field name, location, and tool/toolset identifier below is quoted or paraphrased from that fetch, not guessed.

## Automated install (copy + sync)

```pwsh
make install-vscode TARGET=C:/code/myproject
make sync-vscode  TARGET=C:/code/myproject   # re-run after editing agents/ or commands/
make uninstall    TARGET=C:/code/myproject
```

Generates:

- `agents/*.md` → `<target>/.github/agents/<role>.agent.md` — custom agents (task 4.1)
- `commands/*.md` → `<target>/.github/prompts/<name>.prompt.md` — prompt files with real frontmatter (task 4.3)
- `README.md`'s Principles section → `<target>/.github/instructions/agent-playbook.instructions.md`, `applyTo: "**"` — the **one** surviving always-on file (task 4.2)

Re-running `sync-vscode` refreshes all three from `agents/`, `commands/`, and `README.md`. The canonical text stays in this repo; `.github/` files are generated adapters. `Get-VSCodeAgentTools` / `Get-VSCodeModelsForTier` live in `install/vscode.ps1` (wave-4's own scope, per plan.v3.md §1.4a's ownership matrix — not `install/common.ps1`).

## Custom agents (`.github/agents/*.agent.md`)

### Field list used

| Field | Source | Notes |
| --- | --- | --- |
| `name` | `Get-DisplayAgentName` | Capitalized role name (`QA` stays uppercase — ≤2 chars). |
| `description` | `Get-AgentDescription` (existing wave-1 helper — reused, not reinvented) | First non-empty line under `## Purpose` in `agents/<role>.md`. Shown as chat-input placeholder text. |
| `tools` | **Pure function** of `Get-RoleMeta`'s `(capabilityIntent, pathPolicy)` pair — `Get-VSCodeAgentTools` | See derivation table below. `orchestrator` is the sole hand-authored exception (carve-out, below). |
| `model` | Pure function of `tier` — `Get-VSCodeModelsForTier` | A **prioritized array**, not a single vendor lock — VS Code "tries each model in order until an available one is found." Mirrors Claude's opus/sonnet tier split (D4); model names are the exact examples used in VS Code's own docs (`'Claude Opus 4.5'` / `'GPT-5.2'` for Highest tier; `'Claude Sonnet 4.5'` / `'GPT-5'`, from the docs' own paired `handoffs.model` example, for High/Mid). Declared default, not a verified optimum (D5) — same honesty stance as `adapters/claude.md`'s `effort`. |
| `agents` | Orchestrator only | Fixed 8-leaf allowlist — see carve-out. |
| `disable-model-invocation` | Orchestrator only | See carve-out. |
| `handoffs` | 4 of the 9 roles (planner, builder, reviewer, qa) | See stage-chain diagram below. |

### `tools` derivation (pure function, task 4.1 / §1.4a)

VS Code's own tool/toolset names, as attested in its docs (not invented): `search/codebase`, `search/usages` (read/search), `edit` (file edits), `read/terminalLastCommand` + `terminal` (shell), `agent` (subagent dispatch tool — see carve-out, never granted to a derived leaf role either).

| `capabilityIntent` | Roles | Derived `tools` |
| --- | --- | --- |
| `noRepoAccess` | sensei, refiner | `[]` — no tools at all |
| `docsReadOnly` | advisor | `['search/codebase', 'search/usages']` |
| `curatorReadOnly` | curator | `['search/codebase', 'search/usages']` |
| `shellReadOnly` | planner, reviewer, qa | `['search/codebase', 'search/usages', 'read/terminalLastCommand', 'terminal']` |
| `shellEdit` | builder | `['search/codebase', 'search/usages', 'edit', 'read/terminalLastCommand', 'terminal']` |

**`pathPolicy` note (qa):** `qa` is the only `pathPolicy: noProductSource` role, but VS Code — like Claude (`adapters/claude.md`) — has **no path-scoped tool primitive**: there is no "search docs but not product source" toolset. Faking a distinction here (e.g. withholding `search/codebase` from `qa`) would break `qa`'s genuine, contract-required need to read documentation (`agents/qa.md`), for no real containment gain, since the same tool also indexes docs. `Get-VSCodeAgentTools` accepts `pathPolicy` (interface symmetry with the pure-function pair) but does not branch on it for this reason, exactly like Claude's generator; the product-source read denial for `qa` stays enforced as **policy in `agents/qa.md`** (degraded-detect if a path is opened anyway), not as a tool-level grant difference.

**Fail-closed empty-list note (F-4 lesson applied preemptively):** `tools: []` is always emitted **explicitly** for `sensei`/`refiner`, never omitted. This repo's own F-4 finding showed Claude's `tools: ''` (empty string) silently omitted the whole `tools:` line, which Claude then resolved as "inherit every tool" — the opposite of the intended zero-tool grant. VS Code's docs do not document an equivalent default-on-omission behavior, but there is also no documented guarantee against it; emitting `tools: []` explicitly is the fail-closed choice regardless of which way that default actually resolves. **Implementation pitfall found and fixed during this wave:** PowerShell coerces a `$null` argument bound to a `[string[]]` parameter into `@('')` (a one-element array holding an empty string), not an empty array — an early version of the generator emitted `tools: ['']` for `sensei` instead of `tools: []`. Fixed by using an untyped parameter plus an explicit `Where-Object { $null -ne $_ }` + count-check in `ConvertTo-YamlFlowList` (`install/vscode.ps1`). Verified in the regenerated output (see Evidence, below) — this is exactly the class of silent-tool-leak bug F-4 first found on a different harness.

### Orchestrator carve-out (matches wave-2's Claude carve-out; plan.v3.md §1.4a)

`orchestrator`'s `tools`/`agents` grant is **hand-authored and fixed**, never derived from `capabilityIntent: dispatch` — applying the pure-function rule literally would re-derive an `agent`-bearing grant (VS Code's dispatch tool, the `SendMessage`/`Agent` equivalent), directly contradicting README's Identity hard rule ("✗ NEVER spawn orchestrator").

- **`tools`**: `['search/codebase', 'search/usages', 'edit', 'read/terminalLastCommand', 'terminal']` — the same read/write/search/shell grant as `builder` (mirrors Claude's carve-out giving orchestrator the full non-dispatch grant, not a stripped-down one), with `agent` (the dispatch tool) **explicitly excluded**.
- **`agents`**: `['refiner', 'planner', 'sensei', 'advisor', 'builder', 'reviewer', 'curator', 'qa']` — exactly the 8 leaves, `orchestrator` absent (I13).
- **`disable-model-invocation: true`** — a VS Code-native feature with **no direct Claude equivalent**: it prevents `orchestrator` from being invoked as a **subagent by any other agent**, a stronger backstop for "NEVER spawn orchestrator" than tool exclusion alone provides. Genuinely new capability this wave found and used, not carried over from wave-2 by rote.

**A disclosed tension, not a silent gap:** VS Code's own docs state, for the `agents` field: *"If you specify `agents`, ensure the `agent` tool is included in the `tools` property."* This repo's generated `orchestrator.agent.md` violates that guidance **on purpose** — `agents:` lists the 8 leaves (satisfying I13/W4-N02: display/documentation of what this role coordinates) while `tools` omits `agent` (satisfying W4-N04: nothing that could invoke another agent/mode). The practical consequence, stated honestly: if `orchestrator.agent.md` is ever selected in the VS Code agent picker, its `agents:` allowlist is **functionally inert** — there is no tool available to actually dispatch a subagent through it. That inertness *is* the carve-out's intent (an orchestrator-flavored custom agent that can display/describe its role but cannot itself fan out), not an oversight; it mirrors Claude's carve-out where a spawned orchestrator subagent "must not itself dispatch further work" and can only return a recommendation.

| | Claude (`adapters/claude.md`) | VS Code (this wave) |
| --- | --- | --- |
| Dispatch tool excluded | `Agent`, `SendMessage` | `agent` |
| Non-dispatch grant | `Read, Write, Edit, Grep, Glob, Bash, Skill` | `search/codebase, search/usages, edit, read/terminalLastCommand, terminal` |
| Subagent list | n/a (Claude has no `agents:`-style allowlist on the definition itself) | `agents:` = 8 leaves, present but inert (see above) |
| Extra backstop | none | `disable-model-invocation: true` |

## Handoffs (`handoffs`, task 4.4)

Models the stage chain from `agents/orchestrator.md`'s Stage map. Each edge carries `label` + `agent` + `prompt` + `send: false` (never auto-submits — a human or the orchestrator reviews before advancing, matching Stage 3/5/6's own gates):

```
planner  --[Start Implementation]--> builder
builder  --[Request Review]--------> reviewer
reviewer --[Run Black-box QA]------> qa
qa       --[Final Sensei Pass]-----> sensei
```

`send: false` on every edge is deliberate, not the VS Code default carried over by accident: this repo's Stage 3/5/6 gates already require an explicit approve/revise decision before advancing (`agents/orchestrator.md`), and an auto-submitting handoff button would silently bypass that gate the first time an operator clicks it without reading the prompt.

## Prompt files (`.github/prompts/*.prompt.md`, task 4.3 / F-14)

| Field | Emitted for | Source |
| --- | --- | --- |
| `name` | all 9 | command file base name |
| `description` | all 9 | `Get-CommandSkillDescription` (existing wave-1 helper, reused — same fallback rules, same 1024-char ceiling, same no-`$`-sigil rule as every other harness) |
| `agent` | all 11 (all 11 commands reference a role) | `Get-CommandAgent` |
| `argument-hint` | `e2e`, `e2e-resume` only | `Get-CommandArgumentHint` — `$null` for the other 7, so **no key is emitted at all** for them (I4: an absent hint is never rendered as an empty `argument-hint:` line) |

Before this wave, `install/vscode.ps1` wrote only a generated-comment + raw command body — no frontmatter, so nothing beyond a filename appeared in the `/` picker and no prompt routed to a role (F-14). Fixed.

## The one surviving always-on instructions file (task 4.2 / D6, I11)

`.github/instructions/agent-playbook.instructions.md`, `applyTo: "**"`, contains **only** README.md's `## Principles` table — extracted live at generation time (`Get-ReadmePrinciplesSection` in `install/vscode.ps1`), not duplicated by hand, so it can never drift from the single source of truth. The table's 4th row (`**Main agent is the brain on `/e2e`** | Never nest a second orchestrator`) already **is** the required "main agent is the brain on `/e2e`" identity rule — no second copy needed.

**Byte budget (I11, W4-P03 — measured, not estimated):**

| | Bytes | How measured |
| --- | --- | --- |
| Raw `agents/*.md` source sum (the ~123 KB figure cited in F-5/plan.v3.md) | **123,784 B** | `(Get-ChildItem agents -Filter *.md \| Measure-Object Length -Sum).Sum` on this wave's base SHA — 717 B above the plan's cited 123,067 B, a disclosed, immaterial variance (checkout/line-ending normalization; both numbers describe the same "9 role files at ~123 KB" order of magnitude, not a contradiction). |
| **Before** — actual generated `.github/instructions/` payload from the pre-wave-4 generator (9× `applyTo: "**"`-wrapped role files) | **125,062 B** | `pwsh install/vscode.ps1 -Target <temp>` against the **unmodified** wave-1-base generator, then `(Get-ChildItem -Recurse .github/instructions \| Measure-Object Length -Sum).Sum`. This is the number I11 actually gates (the real request-injection payload), not the raw source sum. |
| **After** — this wave's generated `.github/instructions/` payload (1 file) | **662 B** | Same measurement, against this wave's generator. |

662 B < 2,000 B (I11 satisfied, ~189× smaller than the before figure).

## Agent Host / skills migration (task 4.5)

### Location tables

**Custom agents:**

| Scope | Default location |
| --- | --- |
| Workspace (this repo's generated form) | `.github/agents/` |
| Workspace (Claude format) | `.claude/agents/` |
| User profile | `~/.copilot/agents/` |

**Instructions files:**

| Scope | Default location |
| --- | --- |
| Workspace (this repo's generated form) | `.github/instructions/` |
| Workspace (Claude format) | `.claude/rules/` |
| User profile | `~/.copilot/instructions/` or `~/.claude/rules/` |

Both tables are configurable (`chat.agentFilesLocations`, `chat.instructionsFilesLocations`); this repo only ever writes the first row of each (workspace, this repo's own generated path) — it never writes into `.claude/agents`/`.claude/rules` or the user profile from `install/vscode.ps1` (that overlap belongs to `install/claude.ps1`, a different wave/file).

### Prompt-files → skills migration note (W4-E02)

> "Agents running on the **Agent Host** don't use prompt files. To use an existing prompt with the Copilot agent, convert it to an agent skill. The Agent Customizations editor offers a **one-time migration** that converts your prompt files to skills (experimental). Prompt files continue to work with **local agents that run in the VS Code extension host**."

Practical effect for this repo: `.github/prompts/*.prompt.md` (this wave's task 4.3 output) works today for local/extension-host Copilot agents. If an operator runs Copilot on the **Agent Host** (a separate, newer execution mode — not the default as of this writing), the prompt files this repo generates are invisible to it; the operator-facing fix is VS Code's own one-time prompt→skill migration inside the Agent Customizations editor, not a second generator this repo would need to maintain. Not attempted here — no live Agent Host session was available to verify against in this wave (documented, not silently skipped).

### `tools` entry unavailable in this VS Code version (W4-E01)

> "If a given tool is not available when using the custom agent, it **is ignored**."

Quoted directly from the custom-agents doc's Body section. A generated `.agent.md` referencing a tool/toolset name the operator's VS Code build doesn't yet ship (e.g. an older build without `search/usages`) degrades gracefully — the agent still runs with whatever subset resolves, not a hard error. No live test needed for this row (documentation-only per the plan).

## AGENTS.md interaction (task 4.6)

VS Code **automatically detects an `AGENTS.md` file at the workspace root** and applies it as always-on instructions to every chat request in the workspace — same mechanism class as `.github/copilot-instructions.md`, no install step required from this repo. This repo's own `AGENTS.md` is **2,399 B** as of this wave's base SHA (within the plan's cited 2,196–2,399 B range) — small enough to leave as-is; it is **not** duplicated into `.github/instructions/` by `install/vscode.ps1`, and does not count against the I11 budget above (I11 only gates *this repo's own generated* instructions payload, not VS Code's independent, native AGENTS.md pickup — which every VS Code workspace gets regardless of anything this repo generates).

## Caveats

- Copilot has **no native per-"agent" surface for instructions** the way `.agent.md` now provides for behavior/tools — instructions remain path/glob-scoped (`applyTo`), which is exactly why task 4.2 shrank always-on instructions to the Principles table only, and moved role behavior to custom agents instead.
- This adapter is **best-effort**: confirm the exact filenames and frontmatter against your installed Copilot version. `chat.agentFilesLocations` / `chat.instructionsFilesLocations` can be reconfigured by the operator; this repo only targets the documented default paths.
- **Stage 6:** black-box policy + degraded source-citation fail; product-tree writes by QA are forbidden (session `qa/` only) — see the `pathPolicy` note above for how that's enforced here (policy, not a tool grant).
- A real synced VS Code workspace (agent picker rendering all 9 roles, a handoff button actually appearing and functioning) is **not verified within this wave** — deferred to wave-7 task 7.6a/W7-CONF-4, which runs against a real install with no sandbox needed (this harness does not host the `/e2e` session driving this plan, so there is no self-hosting hazard to defer around; the deferral here is purely "wave-4 has no real VS Code runtime available to it," not a hazard-avoidance deferral).

## DRY Rule

The canonical prompt stays in `agents/*.md`, `commands/*.md`, and README.md's Principles table. VS Code-specific files under `.github/` are generated adapters only — never hand-edited.

## Resume / session continuity

| Field | Value |
| --- | --- |
| **Spawn path** | Copilot/VS Code has **no native multi-agent Continuity surface**. Install maps `agents/*.md` → `.github/agents/*.agent.md` (custom agents), `commands/*.md` → `.github/prompts/*.prompt.md`, and README's Principles table → one `.github/instructions/agent-playbook.instructions.md`. "Spawning" a specialist is user/orchestrator-driven agent selection (or a handoff button), not a resumable subagent runtime with a returned session/agent id. |
| **`resume_supported`** | **`false`** |
| **Why** | There is no documented Copilot API to resume a prior specialist session by id. Custom agents and handoffs are configuration + guided navigation, not live agent chains with a persisted, addressable transcript the way Claude's `SendMessage`-by-agent-ID mechanism works (`adapters/claude.md`). Do **not** invent resume APIs. |
| **`session_ref`** | Unsupported / `none`. Chat thread ids (if any) are product-internal and not playbook Continuity roots unless promoted and recorded by the human/orchestrator. |
| **Dead session** | Always treat a new chat/agent invocation as a new leaf unless the operator re-attaches prior packages manually. |
| **When resume unsupported** | **`reconstituted`** from e2e session artifacts on disk (checklist green) or **`cold_start_waived`** / **BLOCK**. Silent cold start on dependent edges is forbidden. |

See `agents/orchestrator.md` **Global Continuity**. This adapter is best-effort for Continuity: prefer process reconstitution over claiming harness resume.
