# Codex Adapter

Codex should use the Markdown files in this repo as source material.

## Recommended Simple Setup

Use this repo as reference material and invoke agents explicitly:

```text
Use the agent definition in agents/planner.md and plan this request.
```

## Repo Guidance

Copy or reference `AGENTS.md` from this repo when you want these conventions available in a project.

Codex automatically reads `AGENTS.md` files in a repository, so keep that file concise.

## Custom Agents

If you want Codex subagents, create Codex-native agent files from the corresponding `agents/*.md` manually.

Do not duplicate behavior in multiple places. The Codex-native file should say:

```text
Use the behavior defined in agents/reviewer.md.
```

If Codex cannot access this repo from the target project, copy the specific agent Markdown file into that project.

## Slash Commands

Codex custom prompts can be used for `/refine-this`, `/plan-this`, and similar commands, but commands should stay thin.

Each command should point to the matching file in `commands/` or `agents/`.

