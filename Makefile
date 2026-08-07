TARGET ?= .
PS := pwsh -NoProfile -File

.PHONY: help list install-opencode sync-opencode uninstall-opencode
.PHONY: install-codex sync-codex install-codex-global sync-codex-global install-vscode sync-vscode
.PHONY: install-claude sync-claude install-claude-global sync-claude-global
.PHONY: install-grok sync-grok install-grok-global sync-grok-global
.PHONY: install-personal sync-personal verify-sync
.PHONY: install sync uninstall all clean

help:
	@$(PS) install/help.ps1

list:
	@$(PS) install/list.ps1

# opencode: reference-only, in-repo (the primary target).
install-opencode sync-opencode:
	@$(PS) install/opencode.ps1 -Target $(TARGET)

uninstall-opencode:
	@$(PS) install/uninstall-opencode.ps1

# Default copy-based install = codex + vscode (validated native surfaces).
install sync: install-codex install-vscode
	@echo "Installed codex+vscode into $(TARGET). Re-run after editing agents/ or commands/ (make sync TARGET=$(TARGET))."

install-codex sync-codex:
	@$(PS) install/codex.ps1 -Target "$(TARGET)"

install-codex-global sync-codex-global:
	@$(PS) install/codex.ps1 -Global

install-vscode sync-vscode:
	@$(PS) install/vscode.ps1 -Target "$(TARGET)"

# Claude Code: project (.claude/) or personal (~/.claude/)
install-claude sync-claude:
	@$(PS) install/claude.ps1 -Target "$(TARGET)"

install-claude-global sync-claude-global:
	@$(PS) install/claude.ps1 -Global

# Grok Build: project (.grok/skills/) or personal (~/.grok/skills/)
install-grok sync-grok:
	@$(PS) install/grok.ps1 -Target "$(TARGET)"

install-grok-global sync-grok-global:
	@$(PS) install/grok.ps1 -Global

# Personal harnesses used day-to-day (Codex + Claude Code + Grok)
install-personal sync-personal: install-codex-global install-claude-global install-grok-global
	@echo "Personal install complete: codex + claude + grok skills/agents."

# Drift detector (D12): regenerates the personal projections into a temp root
# and diffs them against ~/.claude, ~/.grok, ~/.codex, ~/.agents (read-only).
# Exits non-zero on drift. Not a wave-level gate (see install/common.ps1 header).
verify-sync:
	@$(PS) install/verify-sync.ps1

uninstall:
	@$(PS) install/uninstall.ps1 -Target "$(TARGET)"

all: install-opencode install

clean: uninstall-opencode
	@$(PS) install/clean.ps1
