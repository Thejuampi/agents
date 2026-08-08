# Harness research bibliography

Sole author: wave-7 (task 7.4, `plan.v3.md` §1.4a — task 6.1a, the other would-be
writer under `plan.v1.md`, was cut in the `plan.v3.md` consolidation). This is the
shared bibliography for every capability claim made in `adapters/*.md` and every
finding/decision (`F-1`…`F-15`, `D1`…`D15`) in
`.agents/workspace/tmp/e2e/harness-prompting-alignment/plan.v3.md`.

Every entry: **doc title**, **URL**, **retrieval date**, **finding(s)/claim(s) it
supports**. Retrieval dates below are as recorded by the plan/adapters at the time
each page was fetched — wave-7 itself did not re-fetch any page (see "Verification
method" at the bottom): this document consolidates citations already made, it does
not assert new ones.

## Anthropic — prompt engineering

| Doc | URL | Retrieved | Supports |
| --- | --- | --- | --- |
| Prompt engineering overview | https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/overview | 2026-08-06 | Wave-6 ceremony-removal baseline (I17/I18) |
| Prompting Claude Opus 5 | https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/prompting-claude-opus-5 | 2026-08-06 | **F-11(a)/(b)** — "at least three times" / "Anticipatory pass count" over-verification removal; "report everything, filter separately" (D13, task 6.2/6.7) |
| Prompting Claude Sonnet 5 | https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/prompting-claude-sonnet-5 | 2026-08-06 | Cross-model prompt-craft baseline for wave-6's length-calibration line (task 6.3) |
| Use XML tags to structure your prompts | https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/use-xml-tags | 2026-08-06 | Non-goal: blanket XML conversion rejected (§1 Non-goals) |
| Be clear and direct | https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/be-clear-and-direct | 2026-08-06 | General prompt-craft baseline, wave-6 |
| Giving Claude a role with a system prompt | https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/system-prompts | 2026-08-06 | Role-file structure baseline, wave-6 |

## Anthropic — Claude Code

| Doc | URL | Retrieved | Supports |
| --- | --- | --- | --- |
| Documentation index | https://code.claude.com/docs/llms.txt | 2026-08-06 | Research entry point for all Claude Code citations below |
| Create custom subagents | https://code.claude.com/docs/en/sub-agents | 2026-08-06 | **F-3** (resume via `SendMessage`, agent ID, transcript persistence — `adapters/claude.md` "Resume / session continuity"); **F-4** (`tools: ''` inherits everything, not "no tools" — `adapters/claude.md` "Sensei and Refiner (F-4, closed)"); **F-15** (PowerShell on-by-default on Windows without Git Bash — `adapters/claude.md` "PowerShell (F-15)") |
| Agent Skills | https://code.claude.com/docs/en/skills | 2026-08-06 | **F-13** (description truncation at 1,536 chars, front-load the use case — `install/common.ps1` `Get-CommandSkillDescription`) |
| Orchestrate teams of Claude Code sessions | https://code.claude.com/docs/en/agent-teams | 2026-08-06 | **D10** (agent teams rejected: experimental, off by default, session-resumption limitations) |
| Output styles | https://code.claude.com/docs/en/output-styles | 2026-08-06 | **D10** (output styles rejected: wrong layer — global overlay vs. 9 distinct roles) |
| Worktrees | https://code.claude.com/docs/en/worktrees | 2026-08-06 | **D9** (`isolation: worktree` rejected: branches from default branch, not parent `HEAD` — breaks builder's exact-base-SHA law) |
| Settings / Permissions / Hooks / Memory / Context window / Best practices | https://code.claude.com/docs/en/settings, /permissions, /hooks, /memory, /context-window, /best-practices | 2026-08-06 | **D8** (`memory:` rejected — would auto-persist curator learnings, contradicting "candidates only"); **D11** (hooks rejected — per-user shell config, not projectable Markdown) |

## Anthropic — engineering blog (multi-agent guidance)

| Doc | URL | Retrieved | Supports |
| --- | --- | --- | --- |
| Building effective agents | https://www.anthropic.com/engineering/building-effective-agents | 2026-08-06 | **D1** (orchestrator-worker pattern endorsed, not replaced — §1.5 "recommendation = NO redesign") |
| How we built our multi-agent research system | https://www.anthropic.com/engineering/multi-agent-research-system | 2026-08-06 | **D1** (lead agent decomposes + spawns specialists + filesystem persistence — matches this repo's `.agents/workspace/tmp/e2e/<slug>/` design); writer-verifier pattern (Sensei/Advisor/Reviewer/QA) |
| Effective context engineering for AI agents | https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents | 2026-08-06 | Context-budget rationale behind wave-4's VS Code always-on-instructions reduction (F-5, I11) |
| Equipping agents for the real world with Agent Skills | https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills | 2026-08-06 | Skills progressive-disclosure design baseline — **D3** (no baked absolute paths) |

## Open standard

| Doc | URL | Retrieved | Supports |
| --- | --- | --- | --- |
| Agent Skills specification | https://agentskills.io/specification | 2026-08-06 | **D2** (agentskills.io six-field spec: `name`, `description`, `license`, `compatibility`, `metadata`, `allowed-tools` — the safe default for non-Claude harnesses); **I3** (fail-closed six-field enforcement, `install/common.ps1` `Install-PlaybookSkillsTo`) |
| AGENTS.md | https://agents.md/ | 2026-08-06 | Baseline for this repo's own `AGENTS.md` convention and Codex's `AGENTS.md` discovery (task 3.7) |

## OpenAI Codex

| Doc | URL | Retrieved | Supports |
| --- | --- | --- | --- |
| Documentation index | https://learn.chatgpt.com/llms.txt | 2026-08-06 | Research entry point for Codex citations |
| Subagents | https://learn.chatgpt.com/docs/agent-configuration/subagents | 2026-08-06 | **F-6** (`model`/`model_reasoning_effort` supported in custom-agent TOML — task 3.1); **task 3.2** (reserved built-in agent names `default`/`worker`/`explorer`) |
| Custom instructions with AGENTS.md | https://learn.chatgpt.com/docs/agent-configuration/agents-md | 2026-08-06 | **task 3.7** (`project_doc_max_bytes` = 32 KiB default, `project_doc_fallback_filenames` — `adapters/codex.md` "AGENTS.md discovery, precedence, and byte cap") |
| Build skills | https://learn.chatgpt.com/docs/build-skills | 2026-08-06 | **F-13** cross-vendor confirmation (front-load use case + trigger words) |
| Custom Prompts | https://learn.chatgpt.com/docs/custom-prompts | 2026-08-06 | **F-12** ("Custom prompts are deprecated. Use skills for reusable instructions." — task 3.3 deprecation banner) |
| Prompting Codex | https://learn.chatgpt.com/docs/prompting | 2026-08-06 | §1.5 point 3 ("narrow and opinionated" custom agents — supports the 9-role, non-collapsed contract) |
| `developers.openai.com/codex` (native-surfaces confirmation) | https://developers.openai.com/codex | 2026-08-06 | `adapters/codex.md` "Native surfaces" — TOML key table (I9), `sandbox_mode` enum (task 3.6), reserved-name collision guard (task 3.2) |

## OpenCode

| Doc | URL | Retrieved | Supports |
| --- | --- | --- | --- |
| Agents | https://opencode.ai/docs/agents | 2026-08-06 | **F-7** (`permission.task`, deny removes the subagent from the Task tool description entirely — task 5.1); **I14** (no agent's `permission.task` names `orchestrator`) |
| Agent Skills | https://opencode.ai/docs/skills | 2026-08-06 | **F-8** (OpenCode reads `.claude/skills`, `~/.claude/skills`, `.agents/skills`, `~/.agents/skills` natively — task 5.4, "document, don't duplicate") |
| Commands | https://opencode.ai/docs/commands | 2026-08-06 | **task 5.3** (`subtask: true` on leaf command files) |
| Rules | https://opencode.ai/docs/rules | 2026-08-06 | **F-8** (`CLAUDE.md`/`~/.claude/CLAUDE.md` read natively) — precedence order vs. `AGENTS.md` when both exist left `unverified` by wave-5 (no network access; see `adapters/opencode.md`) |
| Config (JSON Schema) | https://opencode.ai/config.json | 2026-08-06 | **I15** — `.opencode/opencode.json`'s `$schema` field; full schema conformance left `unverified` by wave-5 (no network access) |

## VS Code / GitHub Copilot

| Doc | URL | Retrieved | Supports |
| --- | --- | --- | --- |
| Custom agents in VS Code | https://code.visualstudio.com/docs/copilot/customization/custom-agents | 2026-08-06/07 (wave-4 live fetch) | **F-5/D6** (`.github/agents/*.agent.md`, `tools`/`agents`/`model`/`handoffs` fields — task 4.1/4.4); the `agents:`+`agent`-tool coupling note (`adapters/vscode.md` "disclosed tension") |
| Use custom instructions in VS Code | https://code.visualstudio.com/docs/copilot/customization/custom-instructions | 2026-08-06/07 | **F-5** (instructions without `applyTo` are not applied automatically — task 4.2, single always-on file) |
| Use prompt files in VS Code | https://code.visualstudio.com/docs/copilot/customization/prompt-files | 2026-08-06/07 | **F-14** (prompt-file frontmatter fields — task 4.3); Agent Host migration note (`adapters/vscode.md` W4-E02) |
| Create and manage agent customizations | https://code.visualstudio.com/docs/copilot/customization/overview | 2026-08-06/07 | Location-table baseline (`adapters/vscode.md` task 4.5) |
| Tools concepts | https://code.visualstudio.com/docs/agents/concepts/tools | 2026-08-06/07 | `tools`/toolset identifier vocabulary used in `Get-VSCodeAgentTools` (`install/vscode.ps1`) |

## xAI Grok Build

| Doc | URL | Retrieved | Supports |
| --- | --- | --- | --- |
| Documentation index | https://docs.x.ai/llms.txt | 2026-08-06 | Research entry point for Grok citations |
| Skills, Plugins & Marketplaces | https://docs.x.ai/build/features/skills-plugins-marketplaces | 2026-08-06 | **F-8** ("Grok is fully compatible with Claude Code with zero configuration needed... reads Claude Code marketplaces, plugins, skills, MCPs, agents, hooks, and instruction files"; also `~/.agents/skills/` + `~/.agents/commands/` — `adapters/grok.md` "What Grok reads for free") |
| Subagents | https://docs.x.ai/build/features/subagents | 2026-08-06 | **F-9** (`.grok/agents/`/`~/.grok/agents/` is the documented subagent location, but the on-disk file format is undocumented — **D7 spike verdict, reconfirmed by wave-5**: "not documented as of 2026-08-06"); task 5.5 removal-only disposition |
| Sessions | https://docs.x.ai/build/features/sessions | 2026-08-06 | **task 5.7** (main-session resume via `--resume`/`-c`/`/resume`/`--fork-session` documented; leaf-subagent resume explicitly undocumented — `adapters/grok.md` Resume section) |
| AGENTS.md (project rules) | https://docs.x.ai/build/features/project-rules | 2026-08-06 | Cross-vendor `AGENTS.md` discovery confirmation |
| Worktrees / Permissions | https://docs.x.ai/build/features/worktrees, /permissions | 2026-08-06 | Cross-vendor confirmation, no Grok-specific finding attached |

## Repo-internal sources (not externally retrievable; cited for completeness)

`AGENTS.md`, `README.md`, `docs/findings.md`, `agents/*.md` (9), `commands/*.md` (9),
`adapters/*.md` (5), `install/*.ps1` (6), `Makefile`, and the live projections under
`~/.claude`, `~/.grok`, `~/.codex`, `~/.agents` on this machine (evidence for **F-1**,
**F-2**, reproduced by wave-1's `build/wave-1-baseline-drift.txt` and wave-7's
`build/wave-7-report.md` before/after 7.6a sync listings).

## Verification method (task 7.4 acceptance, stated honestly)

Task 7.4's acceptance criterion is: "a spot check of 5 random claims resolves to a
live page." **This builder role has no `WebFetch`/`WebSearch` tool** — the tool
surface available to this wave-7 dispatch is Read/Write/Edit/Grep/Glob/Bash only.
Every URL above is therefore a **consolidation of citations already made** by the
plan's own §5 bibliography and by waves 2-5's adapter research (each of which
recorded its own live-fetch retrieval date at build time — see `adapters/vscode.md`'s
explicit "Verified against VS Code docs 2026-08-06/07... all fetched live during this
wave" line as the clearest example), not a set of fresh fetches by wave-7. A live
5-URL spot check therefore could not be performed by this builder and is recorded
here as **`unverified — requires a role/session with web-fetch access, not available
to this builder role`**, per the same honesty standard `plan.v3.md` §1.6 item 5
requires for every other unreachable-mechanism claim in this session. This is
disclosed as a real, named gap in `docs/harness-conformance.md`'s row for this
task — not silently passed.

Every URL cited above was cross-checked, by this builder, against at least one of
the following: (a) the plan's own §5 bibliography text, (b) an `adapters/*.md` file's
own citation of the same URL, or (c) a wave report's evidence block quoting or
paraphrasing that page's content. No URL above was invented by wave-7; each is a
restatement of an already-made citation, mapped explicitly to the finding/claim it
supports (closing the "which claim does this URL actually back" gap the original
per-adapter citations left implicit).
