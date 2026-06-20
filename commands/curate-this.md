# /curate-this

Use `agents/curator.md`.

## Context to provide before curating

1. The session transcript or summary (required).
2. Current project guidance, only if it is not already attached to the conversation.
3. Relevant agent definitions or command prompts, only if the session touched them and they are not already attached.
4. Previous curation reports for this project, only if available and not already attached.

Do not duplicate context. If a file such as `AGENTS.md` or an agent prompt is already automatically attached, use that existing context instead of asking to read or paste it again.

Prompt:

```text
Act as the Curator. Review the provided session transcript or summary and produce a curation report.
Do not persist knowledge or edit files. Produce candidates only.
Check current guidance for duplicates or conflicts when it is provided.
Do not request guidance files that are already attached to the conversation.
If the session is not worth curating, return only the Curation Verdict and stop.
For each knowledge candidate, include confidence, risk if wrong, conflicts with, expiration, and revalidation trigger.
```
