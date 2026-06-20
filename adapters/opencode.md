# OpenCode Adapter

OpenCode supports project or global agents as Markdown files with frontmatter.

## Recommended Simple Setup

Copy the relevant file from `agents/` into the OpenCode agents directory and add only minimal frontmatter when OpenCode needs a native agent file.

Example:

```markdown
---
description: Plan implementation work without modifying files.
mode: subagent
permission:
  edit: deny
---

Use the planner behavior already attached to this conversation.
```

If the planner definition is not already attached or accessible, paste the full contents of `agents/planner.md` below the frontmatter.

When the agent definition is already part of the conversation context, do not paste or request it again.

## Commands

Use `commands/*.md` as the command text.

Keep commands thin. They should invoke an agent role, not redefine it.

## DRY Rule

The canonical prompt stays in `agents/*.md`.

OpenCode-specific files are adapters only.
