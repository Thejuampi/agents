# Findings convention

Shared law for every finding-reporter in this playbook: **QA**, **Sensei**, **Advisor**, **Reviewer**.  
Keep bodies freeform. Ceremony is not the point—**required fields + honest severity** are.

> **Home of this convention:** `docs/findings.md` only.  
> **Never** put findings law under `agents/` (that path becomes a phantom harness agent).  
> **Instance SSOT for Stage 6 gate evaluation** is the session tree: `qa/findings.md` + Orchestrator `qa/p0-ledger.md` (and provenance). This file is the **convention**; the session holds the **run**.

---

## Severity (P0 / P1 / P2)

| Level | Product meaning (QA / live product) | Process / plan meaning (Sensei · Advisor · Reviewer) |
| --- | --- | --- |
| **P0** | Blocks release or safe use: wrong material behavior, data loss, missing refuse when required, cannot run black-box when the surface requires exercise, security-class break | Build-blocking if shipped or planned as written |
| **P1** | Real defect or gap; Orchestrator may fix now or defer | Improvement; not a Stage 3/5 hard-block once P0s are clear |
| **P2** | Minor polish / nice-to-have | Optional; note lightly or in retro |

**Gate-blocking process classes** (when open, treat like product P0 for Stage 6 success): integrity violation, coaching-detect, stub-plan, source-citation (degraded mode), unparseable findings. Orchestrator enumerates and enforces these when Stage 6 is armed.

---

## Required fields (every finding)

| Field | Values / rule |
| --- | --- |
| `id` | Stable string for the run (e.g. `QA-001`, `S-P0-1`) |
| `severity` | `P0` \| `P1` \| `P2` |
| `status` | `open` \| `fixed` \| `waived` |
| `class` | `product` \| `process` \| `environment` |

Body (summary, evidence, impact, steps) is **freeform**. Format is not a schema tax.

**Parse fail-closed:** a finding missing any required field is incomplete. The run cannot be treated as agent-green / Stage-6-success until repaired. Do **not** map missing fields to “non-blocking process” so a product PASS still proceeds. Prefer re-ask over inventing defaults.

---

## Proactive fix rule

| Complexity | What to include |
| --- | --- |
| **Simple** (clear local fix, no design fork) | Short suggested fix (**1–5 lines**) |
| **Complex** (architecture, multi-module, ambiguous product law) | **Problem + impact + evidence only** — do not invent a full redesign |

QA `suggested_fix` is **advisory** for Orchestrator / Builder only. QA never patches the product.

---

## Who follows

| Role | Obligation |
| --- | --- |
| **QA** | Product acceptance findings; required fields; findings-only (no product edits) |
| **Sensei** | Craft / plan bar findings; P0/P1/P2; simple vs complex fix rule |
| **Advisor** | Doc-grounded plan findings; P0/P1/P2; simple vs complex fix rule |
| **Reviewer** | Implementation findings; map **blocking → P0**, **non-blocking in-scope → P1**, **residual polish → P2**, *or* put an explicit `severity` on each finding; complex = problem-only |
| **Orchestrator** | Persist session findings; own ledger; evaluate gates (when armed)—not rewrite findings to green |

---

## Non-goals

- Rigid templates beyond required fields  
- Duplicate long severity tables inside every agent file (link here)  
- Treating empty findings without evidence as PASS

