# OpenCode Adapter

OpenCode supports project or global agents as Markdown files with frontmatter.

## Recommended Simple Setup

Copy the relevant file from `agents/` into the OpenCode agents directory and add only minimal frontmatter.

Example:

```markdown
---
description: Plan implementation work without modifying files.
mode: subagent
permission:
  edit: deny
---

Use the behavior defined in agents/planner.md.
```

If OpenCode cannot access this repo from the target project, paste the full contents of `agents/planner.md` below the frontmatter.

## Commands

Use `commands/*.md` as the command text.

Keep commands thin. They should invoke an agent role, not redefine it.

## DRY Rule

The canonical prompt stays in `agents/*.md`.

OpenCode-specific files are adapters only.

