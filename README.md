# Agent Playbook

A personal repository for reusable agents, prompts, and workflows used across projects.

Principles:

- Keep it simple.
- Do not repeat yourself.
- YAGNI: no scripts, generators, or tooling until manual maintenance becomes a real problem.
- One agent = one canonical Markdown file.
- Commands point to agents; they do not duplicate full prompts.
- Tool compatibility is documented as setup guidance, not generated artifacts.

## Structure

```text
agents/
  refiner.md
  planner.md
  builder.md
  reviewer.md
  qa.md
  curator.md
  orchestrator.md
commands/
  refine-this.md
  plan-this.md
  build-this.md
  review-this.md
  qa-this.md
  curate-this.md
  orchestrate-this.md
adapters/
  codex.md
  opencode.md
  vscode.md
AGENTS.md
```

## Agents

- `refiner`: turns vague requests into actionable specifications without reading files.
- `planner`: explores the project in read-only mode and produces an implementable plan.
- `builder`: implements the plan with a focus on quality and maintainability.
- `reviewer`: reviews design, data flow, component boundaries, risks, and coverage.
- `qa`: performs black-box testing as a technical end user, without reading source code.
- `curator`: reviews sessions and proposes learning candidates without persisting them automatically.
- `orchestrator`: coordinates the workflow and delegates without influencing each agent's judgment.

## Suggested Commands

- `/refine-this`
- `/plan-this`
- `/build-this`
- `/review-this`
- `/qa-this`
- `/curate-this`
- `/orchestrate-this`

The `-this` suffix avoids collisions with native tool commands.

## Usage

To use this repo in another project, copy or reference the Markdown files you need.

The source of truth is always `agents/*.md`. If a tool needs frontmatter, TOML, JSON, or a specific path, document that adaptation in `adapters/`.

## Install / sync

A Makefile converts this repo into the native format of each harness without
duplicating content. The canonical files in `agents/` and `commands/` are the
single source of truth; generated adapters only reference or copy them.

```pwsh
make install-opencode            # reference-only: .opencode/opencode.json + thin command files (this repo)
make sync-opencode               # re-run after editing agents/ or commands/
make install TARGET=C:/some/app  # copy-based: codex + vscode into that project (validated native surfaces)
make sync TARGET=C:/some/app     # re-run to replicate edits to that project
make uninstall TARGET=C:/some/app
make install-claude TARGET=...   # opt-in / best-effort (not validated)
make list
make help
```

- **opencode** uses references (`{file:../agents/X.md}` and `@commands/X.md`), so
  edits here take effect on the next OpenCode restart with no copy.
- **codex** copies `agents/*.md` into `<target>/.codex/agents/*.toml` (TOML with
  `developer_instructions`). Codex CLI has no custom slash-command surface, so
  `commands/*.md` are not installed; `AGENTS.md` is owned by the target project.
- **vscode** copies `commands/*.md` -> `.github/prompts/*.prompt.md` and
  `agents/*.md` -> `.github/instructions/*.instructions.md` (with `applyTo`).
  Best-effort: verify filenames against your Copilot version.
- **claude** is opt-in/best-effort (not in the default `install` path).
- Each generated file carries a header pointing back to its source; `make sync`
  refreshes them.
- For another OpenCode project to use this repo, add it as a `reference` (see
  `adapters/opencode.md`) — no install needed there.
- Adding a harness: drop a script in `install/` and a target in `Makefile`
  (see `install/README.md`).
