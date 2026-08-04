# Agent Playbook Instructions

This repository contains reusable agent definitions and command prompts.

Rules for editing this repo:

- Keep agent behavior in `agents/*.md`.
- Keep command entrypoints in `commands/*.md`.
- Full multi-stage pipelines (e.g. E2E) live in the orchestrator agent; commands only select the agent and name the mode.
- Do not duplicate full agent prompts inside command files.
- Do not ask an agent to read or paste guidance that is already automatically attached to the conversation, such as `AGENTS.md`, agent definitions, or command prompts. Use attached context as the source, and provide extra files only when the needed content is missing.
- Prefer plain Markdown over scripts, generators, schemas, or package tooling.
- Add automation only when the same manual step must be repeated more than three times across unrelated changes, or when a manual error has already caused an inconsistency.
- Keep prompts direct, operational, and testable.
- `install/` + `Makefile` generate native adapters for other harnesses (.opencode/, .codex/, .claude/, .grok/, .github/). `agents/*.md` and `commands/*.md` are the source of truth; edit there and re-run `make sync` / `make sync-personal` (or the harness-specific `make sync-*`). Never hand-edit generated adapters. If generated adapters appear out of sync with source files, do not hand-edit them. Run `make sync` (or `sync-personal`) to regenerate. If the sync command is unavailable, flag the inconsistency in a comment or issue rather than editing the adapter directly.
- After editing `agents/` or `commands/`, re-project personal harnesses with **`make sync-personal`** so Claude, Grok, and Codex do not keep stale process law.
- `/e2e` session artifacts live under `.agents/workspace/tmp/e2e/<slug>/` (including `plan-review/p0-ledger.md` and `LESSONS-LEARNED.md`). Do not treat harness-internal task logs as the only review record.
