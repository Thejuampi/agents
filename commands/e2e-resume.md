# /e2e-resume

Use `agents/orchestrator.md`.

Skill-Description: Resume a stopped `/e2e` session. Reassesses real stage completion from artifacts and the registry (not file presence alone), reconciles mid-flight registry rows, then continues Stage 0-8 from the earliest incomplete stage — never skipping Stage 5 review, Stage 6 QA, Stage 7 Sensei, or Stage 8 retro just because later-looking artifacts already exist. Use when the user runs /e2e-resume, or asks to continue or resume an interrupted E2E run.
Argument-Hint: [session-slug]

Prompt:

```text
YOU are the Orchestrator, resuming a prior E2E session in THIS conversation.

HARD RULES — identity (same as /e2e):
- Do NOT spawn, fork, or delegate to an `orchestrator` subagent (or a second copy of yourself). Nested orchestrators destroy context and create dual brains.
- Do NOT re-invoke /e2e or /e2e-resume from inside this run.
- Specialists you MAY spawn (never orchestrator): refiner, planner, sensei, advisor, builder, reviewer, curator, qa.

Load and follow `agents/orchestrator.md` in full — both the E2E pipeline (Stage 0-8) and the **E2E Resume** section (session selection, resume assessment, per-stage exit verification, registry reconciliation, continuity on resume, the done-declaration checklist). That file is the canonical playbook; this command only selects the role and names the mode.
```
