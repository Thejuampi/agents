# VS Code Adapter

VS Code + GitHub Copilot use prompt files and instruction files under `.github/`.

## Automated install (copy + sync)

```pwsh
make install-vscode TARGET=C:/code/myproject
make sync-vscode  TARGET=C:/code/myproject   # re-run after editing agents/ or commands/
make uninstall    TARGET=C:/code/myproject
```

Generates:

- `commands/*.md` -> `<target>/.github/prompts/<name>.prompt.md` (reusable chat prompts)
- `agents/*.md`   -> `<target>/.github/instructions/<name>.instructions.md` with `applyTo: "**"`

Re-running `sync-vscode` refreshes them from `agents/` and `commands/`. The canonical text stays in this repo; the `.github/` files are generated adapters.

## Native surfaces

- **Path-specific instructions**: `.github/instructions/NAME.instructions.md` (filename must end in `.instructions.md`), with frontmatter `applyTo: "<glob>"`. Verified against docs.github.com.
- **Reusable prompts**: `.github/prompts/NAME.prompt.md`. This is the established convention; verify it matches your Copilot/VS Code version before relying on it.
- **Repository-wide**: `.github/copilot-instructions.md` (single file; not generated here — the target project owns it).

## Caveats

- Copilot has **no native per-"agent" surface**. Mapping role behaviors (`agents/*.md`) to path-scoped instructions is a best-effort approximation.
- `applyTo: "**"` injects every role definition into all Copilot requests, which can be heavy. Narrow `applyTo` per file (e.g. `"src/**"`) if you only want a role to apply in part of the repo, or trim the set of agents you install.
- This adapter is **best-effort**: confirm the exact filenames and frontmatter against your installed Copilot version.
- **Stage 6:** black-box policy + degraded source-citation fail; product-tree writes by QA are forbidden (session `qa/` only).

## DRY Rule

The canonical prompt stays in `agents/*.md` and `commands/*.md`. VS Code-specific files are adapters only.

## Resume / session continuity

| Field | Value |
| --- | --- |
| **Spawn path** | Copilot/VS Code has **no native multi-agent Continuity surface**. Install maps `commands/*.md` → `.github/prompts/*.prompt.md` and `agents/*.md` → `.github/instructions/*.instructions.md`. “Spawning” a specialist is user/orchestrator-driven prompt selection, not a subagent runtime. |
| **`resume_supported`** | **`false`** |
| **Why** | There is no documented Copilot API to resume a prior specialist session by id. Role instructions are path-scoped context injection, not live agent chains. Do **not** invent resume APIs. |
| **`session_ref`** | Unsupported / `none`. Chat thread ids (if any) are product-internal and not playbook Continuity roots unless promoted and recorded by the human/orchestrator. |
| **Dead session** | Always treat a new chat/prompt invocation as a new leaf unless the operator re-attaches prior packages manually. |
| **When resume unsupported** | **`reconstituted`** from e2e session artifacts on disk (checklist green) or **`cold_start_waived`** / **BLOCK**. Silent cold start on dependent edges is forbidden. |

See `agents/orchestrator.md` **Global Continuity**. This adapter is best-effort for Continuity: prefer process reconstitution over claiming harness resume.