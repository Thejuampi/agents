# Agent Playbook

A personal repository for reusable agents, prompts, and workflows used across projects.

Principles:

- Keep it simple.
- Do not repeat yourself.
- YAGNI: no scripts, generators, or tooling until manual maintenance becomes a real problem.
- One agent = one canonical Markdown file.
- Commands point to agents; they do not duplicate full prompts.
- Tool compatibility is documented as setup guidance, not generated artifacts.

## Structure

```text
agents/
  refiner.md
  planner.md
  builder.md
  reviewer.md
  qa.md
  curator.md
  orchestrator.md
commands/
  refine-this.md
  plan-this.md
  build-this.md
  review-this.md
  qa-this.md
  curate-this.md
  orchestrate-this.md
adapters/
  codex.md
  opencode.md
  vscode.md
AGENTS.md
```

## Agents

- `refiner`: turns vague requests into actionable specifications without reading files.
- `planner`: explores the project in read-only mode and produces an implementable plan.
- `builder`: implements the plan with a focus on quality and maintainability.
- `reviewer`: reviews design, data flow, component boundaries, risks, and coverage.
- `qa`: performs black-box testing as a technical end user, without reading source code.
- `curator`: reviews sessions and proposes learning candidates without persisting them automatically.
- `orchestrator`: coordinates the workflow and delegates without influencing each agent's judgment.

## Suggested Commands

- `/refine-this`
- `/plan-this`
- `/build-this`
- `/review-this`
- `/qa-this`
- `/curate-this`
- `/orchestrate-this`

The `-this` suffix avoids collisions with native tool commands.

## Usage

To use this repo in another project, copy or reference the Markdown files you need.

The source of truth is always `agents/*.md`. If a tool needs frontmatter, TOML, JSON, or a specific path, document that adaptation in `adapters/`.
