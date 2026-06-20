# Agent Playbook Instructions

This repository contains reusable agent definitions and command prompts.

Rules for editing this repo:

- Keep agent behavior in `agents/*.md`.
- Keep command entrypoints in `commands/*.md`.
- Do not duplicate full agent prompts inside command files.
- Prefer plain Markdown over scripts, generators, schemas, or package tooling.
- Add automation only after manual maintenance becomes a real problem.
- Keep prompts direct, operational, and testable.
- Keep compatibility notes in `adapters/*.md`.

