TARGET ?= .
PS := pwsh -NoProfile -File

.PHONY: help list install-opencode sync-opencode uninstall-opencode
.PHONY: install-codex sync-codex install-vscode sync-vscode install-claude
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

install-vscode sync-vscode:
	@$(PS) install/vscode.ps1 -Target "$(TARGET)"

# Opt-in / best-effort (not validated here; not in the default install path).
install-claude:
	@$(PS) install/claude.ps1 -Target "$(TARGET)"

uninstall:
	@$(PS) install/uninstall.ps1 -Target "$(TARGET)"

all: install-opencode install

clean: uninstall-opencode
	@$(PS) install/clean.ps1
