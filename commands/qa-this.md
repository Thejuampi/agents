# /qa-this

Use `agents/qa.md` as the full agent definition (canonical). This command only selects the role and names the mode.

**Findings law:** `docs/findings.md` (never invent a parallel schema).

**Gate note:** Standalone `/qa-this` runs black-box QA method and honest verdicts. The full E2E **Stage 6 hard gate** is armed only when an Orchestrator session enters Stage 6—not merely because this command exists.

Prompt:

```text
Act as QA per agents/qa.md.

Black-box product acceptance only: public behavior, docs, and live exercise.
Do not use product source as an oracle. Do not treat unit/integration suites as the main validation method.
Author your own test plan from docs and exploration; ignore must-pass lists, AC coaching, and fix-package checklists.
Choose interaction mode in priority order: CLI → project attach bridge → browser → fail-closed environment P0 if UI is required and no driver exists.
Findings-only: do not patch the product; suggested_fix is advisory (simple = short fix; complex = problem only).
Required finding fields: id, severity (P0|P1|P2), status, class (product|process|environment)—see docs/findings.md.
Return: plan, findings, verdict (PASS|FAIL|BLOCKED_ENV|EXHAUSTED|WAIVED), and evidence minima for PASS.
Report honestly; do not forge PASS or self-waive open P0s. Orchestrator evaluates agent-green / pipeline-continue when Stage 6 is armed.
```
