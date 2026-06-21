# Agent Playbook Instructions

This repository contains reusable agent definitions and command prompts.

Rules for editing this repo:

- Keep agent behavior in `agents/*.md`.
- Keep command entrypoints in `commands/*.md`.
- Do not duplicate full agent prompts inside command files.
- Do not ask an agent to read or paste guidance that is already automatically attached to the conversation, such as `AGENTS.md`, agent definitions, or command prompts. Use attached context as the source, and provide extra files only when the needed content is missing.
- Prefer plain Markdown over scripts, generators, schemas, or package tooling.
- Add automation only after manual maintenance becomes a real problem.
- Keep prompts direct, operational, and testable.
- Keep compatibility notes in `adapters/*.md`.
- `install/` + `Makefile` generate native adapters for other harnesses (.opencode/, .codex/, .github/). `agents/*.md` and `commands/*.md` are the source of truth; edit there and re-run `make sync` (or `make sync-opencode`). Never hand-edit generated adapters.
