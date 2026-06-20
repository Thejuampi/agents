# VS Code Adapter

VS Code and GitHub Copilot can use prompt and instruction files.

## Recommended Simple Setup

Copy command prompts from `commands/` into `.github/prompts/` when you want slash-style reusable prompts in a project.

Copy durable guidance into `.github/instructions/` only when it should apply broadly.

## Agent Files

If using agent files and the canonical definition is already attached, keep them thin:

```markdown
---
description: Review implementation against plan and architecture.
---

Use the reviewer behavior already attached to this conversation.
```

If the canonical definition is not already attached or accessible, copy the needed `agents/*.md` file into the project.

When the agent definition is already part of the conversation context, do not paste or request it again.

## DRY Rule

Do not maintain separate VS Code versions of every agent unless the platform requires a real behavioral difference.
