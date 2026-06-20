# VS Code Adapter

VS Code and GitHub Copilot can use prompt and instruction files.

## Recommended Simple Setup

Copy command prompts from `commands/` into `.github/prompts/` when you want slash-style reusable prompts in a project.

Copy durable guidance into `.github/instructions/` only when it should apply broadly.

## Agent Files

If using agent files, keep them thin:

```markdown
---
description: Review implementation against plan and architecture.
---

Use the behavior defined in agents/reviewer.md.
```

If VS Code cannot access this repo from the target project, copy the needed `agents/*.md` file into the project.

## DRY Rule

Do not maintain separate VS Code versions of every agent unless the platform requires a real behavioral difference.

