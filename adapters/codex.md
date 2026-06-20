# Codex Adapter

Codex should use the Markdown files in this repo as source material.

## Recommended Simple Setup

Use this repo as reference material. If the relevant agent definition is already attached to the conversation, invoke it directly:

```text
Use the planner agent definition already attached to this conversation and plan this request.
```

If the definition is not attached, provide or reference exactly one source for it. Do not both attach the content and ask Codex to read the same file.

## Repo Guidance

Copy or reference `AGENTS.md` from this repo when you want these conventions available in a project.

Codex automatically reads `AGENTS.md` files in a repository, so keep that file concise.

When `AGENTS.md` or an agent definition is already loaded into context, do not ask Codex to read it again. That duplicates tokens without adding information.

## Custom Agents

If you want Codex subagents, create Codex-native agent files from the corresponding `agents/*.md` manually.

Do not duplicate behavior in multiple places. If the canonical definition is already attached, the Codex-native file can stay thin:

```text
Use the reviewer behavior already attached to this conversation.
```

If the canonical definition is not attached or accessible, copy the specific agent Markdown file into that project instead of asking Codex to rediscover it each time.

## Slash Commands

Codex custom prompts can be used for `/refine-this`, `/plan-this`, and similar commands, but commands should stay thin.

Each command should point to the matching file in `commands/` or `agents/`.
