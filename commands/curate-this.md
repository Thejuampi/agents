# /curate-this

Use `agents/curator.md`.

## Context to inject before curating

1. The session transcript or summary (required).
2. Current `AGENTS.md` or equivalent project guidance (required).
3. Relevant agent definitions or command prompts (optional, if the session touched them).
4. Previous curation reports for this project (optional, last N).

Prompt:

```text
Act as the Curator. Review the provided session transcript or summary and produce a curation report.
Do not persist knowledge or edit files. Produce candidates only.
Check current guidance for duplicates or conflicts when it is provided.
If the session is not worth curating, return only the Curation Verdict and stop.
For each knowledge candidate, include confidence, risk if wrong, conflicts with, expiration, and revalidation trigger.
```

