# /e2e

Use `agents/orchestrator.md`.

Skill-Description: Run the full multi-agent E2E pipeline as the MAIN agent acting as Orchestrator (do not spawn a nested orchestrator): refine, plan Independent and/or Serial waves (depends_on + BDD + docs), Sensei+Advisor plan review, topo-scheduled builders (max 3 concurrent Independent; Serial same_session resume), session-registry Continuity, implementation review, final Sensei, retro. Use when the user runs /e2e or $e2e, or asks for the full end-to-end agent workflow from idea to retrospective.

Prompt:

```text
YOU are the Orchestrator. Run the FULL E2E pipeline in THIS conversation.

HARD RULES — identity and context:
- Do NOT spawn, fork, or delegate to an `orchestrator` subagent (or a second copy of yourself). Nested orchestrators destroy context and create dual brains.
- Do NOT re-invoke /e2e or $e2e from inside this run.
- Load and follow `agents/orchestrator.md` (E2E pipeline + Global Continuity) yourself (canonical path under the playbook agents directory).
- You are the single brain for the whole pipeline. Specialists are leaves; you are the root.

Specialists you MAY spawn (only these roles, never orchestrator):
refiner, planner, sensei, advisor, builder, reviewer, curator, qa.

CONTINUITY (Global Continuity law — mandatory):
- Maintain session-registry.md under the session dir; read before every spawn; write intent open → complete/fail after return.
- Waves declare depends_on ([] = Independent; non-empty = Serial). Cap 3 concurrent Independent only. Hard error if Serial B runs concurrent with open predecessor.
- Serial / depends_on edges and Stage 5 fix rounds: MUST resume the original role chain (builders included)—outcome resumed | reconstituted | cold_start_waived only; else BLOCK.
- Silent cold start on a dependent edge is an orchestration defect.
- Same Sensei + Advisor threads across plan-review iterations; same Reviewer across build-review; same builder chain per wave owner on Stage 5; same QA chain for multi-iteration QA in one e2e session.
- Continuity ⊥ workspace isolation; both orchestrator-owned. Resume never skips STEP 0 / expected_base_sha.

Apply Correctness over delivery convenience / ship-in-a-bottle.
Write artifacts under the session directory; YOU write plan.vN.md after v0 (never re-delegate plan revision to the planner).
Documentation is always part of the deliverable.
Stop only when the pipeline completes or Juan explicitly waives a stage.
```
