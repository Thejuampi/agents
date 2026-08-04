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
