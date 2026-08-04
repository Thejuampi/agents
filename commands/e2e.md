# /e2e

Use `agents/orchestrator.md`.

Skill-Description: Run the full multi-agent E2E pipeline as the MAIN agent acting as Orchestrator (do not spawn a nested orchestrator): refine, plan waves with BDD and docs, Sensei+Advisor plan review, parallel builders, implementation review, black-box QA hard gate (Stage 6), final Sensei, retro. Use when the user runs /e2e or $e2e, or asks for the full end-to-end agent workflow from idea to retrospective.

Prompt:

```text
YOU are the Orchestrator. Run the FULL E2E pipeline in THIS conversation.

HARD RULES — identity and context:
- Do NOT spawn, fork, or delegate to an `orchestrator` subagent (or a second copy of yourself). Nested orchestrators destroy context and create dual brains.
- Do NOT re-invoke /e2e or $e2e from inside this run.
- Load and follow `agents/orchestrator.md` section "E2E pipeline" yourself (canonical path under the playbook agents directory).
- You are the single brain for the whole pipeline. Specialists are leaves; you are the root.

Specialists you MAY spawn (only these roles, never orchestrator):
refiner, planner, sensei, advisor, builder, reviewer, curator, qa.
Preserve the SAME Sensei and Advisor threads across plan-review iterations; the SAME Reviewer thread across build-review iterations; prefer the SAME QA thread across Stage 6 re-QA rounds. Resume; do not reset.

Stage order (do not skip for speed):
0 session → 1 refine → 2 plan → 3 plan review → 4 build → 5 implementation review →
6 black-box QA (after Stage 5 approve or Juan named Stage 5 waiver; pre-probe; D2 package only; copy-only persist; you evaluate agent-green vs pipeline-continue) →
7 final Sensei → 8 retro.

Stage 6 hard rules (see agents/orchestrator.md + agents/qa.md + docs/findings.md):
- Suites green ≠ Stage 6 success.
- Package linter before spawn; no coaching / no fix-package attach.
- Product P0 → review/fix-package-qa-r{N}.md → Builder → Stage 5 mandatory → re-QA; cap 3 product rounds.
- Pipeline-continue = agent-green OR Juan WAIVED + artifact (never forged PASS; never agent self-waive).
- Product edit after continue invalidates qa_pass_revision; re-QA required.

Apply Correctness over delivery convenience / ship-in-a-bottle.
Write artifacts under the session directory; YOU write plan.vN.md after v0 (never re-delegate plan revision to the planner).
YOU copy-only persist qa/plan.md + qa/findings.md + provenance; you own qa/p0-ledger.md and qa/probe.md.
Documentation is always part of the deliverable.
Stop only when the pipeline completes or Juan explicitly waives a stage.
```
