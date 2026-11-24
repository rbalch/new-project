.PHONY: help build init sync shell up down views views-check governance ledger preferences entries-check controls lint test check tasks

.DEFAULT_GOAL := help

# --- Container ---------------------------------------------------------------

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Build Docker images
	docker compose build

# Path to the private key to install as the container's GitHub identity. Only read the
# first time; afterwards the key lives in the dev-ssh volume and this is ignored.
# Installed by piping its contents, not `docker compose cp`, which copies a symlink
# verbatim and lands a dangling link in the volume.
KEY ?= $(HOME)/.ssh/id_github

init: ## First-run setup: credential volumes, ssh key, gh login, code graph (run on the HOST)
	@test ! -f /.dockerenv || { echo "run 'make init' on the host, not inside the container"; exit 1; }
	@docker volume create dev-ssh >/dev/null && docker volume create dev-gh >/dev/null
	@echo "volumes    dev-ssh, dev-gh ready"
	@docker compose up -d >/dev/null
	@if docker compose exec -T dev test -f /home/dev/.ssh/id_github 2>/dev/null; then \
		echo "ssh key    already installed, left alone"; \
	else \
		test -f "$(KEY)" || { \
			echo "ssh key    no key at $(KEY)"; \
			echo "           pass one: make init KEY=~/.ssh/your-github-key"; \
			exit 1; \
		}; \
		docker compose exec -T dev rm -f /home/dev/.ssh/id_github; \
		docker compose exec -T dev sh -c 'cat > /home/dev/.ssh/id_github' < "$(KEY)"; \
		docker compose exec -T dev chmod 600 /home/dev/.ssh/id_github; \
		echo "ssh key    installed from $(KEY)"; \
	fi
	@# `ssh -T` to github always exits 1 (no shell access), so match the banner instead.
	@docker compose exec -T dev ssh -o StrictHostKeyChecking=accept-new -T git@github.com 2>&1 \
		| grep -q 'successfully authenticated' \
		&& echo "github ssh ok" \
		|| { echo "github ssh FAILED — is this key registered on GitHub?"; exit 1; }
	@if docker compose exec -T dev gh auth status >/dev/null 2>&1; then \
		echo "gh         already authenticated"; \
	else \
		echo "gh         starting interactive login"; \
		docker compose exec dev gh auth login; \
	fi
	@docker compose exec -T dev codegraph init
	@echo "codegraph  indexed"
	@echo
	@echo "Setup complete. Restart Claude Code so it picks up the codegraph MCP server."

sync: ## Sync uv dependencies
	uv sync

shell: ## Open shell in dev container
	docker compose exec dev /bin/zsh

up: ## Start services
	docker compose up

down: ## Stop services
	docker compose down

# --- Governance --------------------------------------------------------------

views: ## Regenerate governance/views/RULES.md + registry.json
	uv run python governance/scripts/build_views.py

views-check: ## Fail if the generated files are stale or hand-edited
	uv run python governance/scripts/build_views.py --check

governance: ## Integrity + drift check (the linchpin)
	uv run python governance/scripts/check_governance.py

# The ledger and the preferences are one file per entry (docs/ledger, docs/preferences); log_entries.py builds the views.
# REFS=origin also counts the entries on every fetched origin branch (fetch first); the views are never a gate.
REFS ?=

ledger: ## Build build/ledger.md from docs/ledger (REFS=origin counts every fetched branch)
	@case "$$REFS" in *[!A-Za-z0-9._/-]*) echo "REFS must be a remote name" >&2; exit 1;; esac
	uv run python governance/scripts/log_entries.py view $(if $(REFS),--refs $(REFS))

preferences: ## Build build/preferences.md from docs/preferences (REFS=origin adds every fetched branch); read it before deciding a fork
	@case "$$REFS" in *[!A-Za-z0-9._/-]*) echo "REFS must be a remote name" >&2; exit 1;; esac
	uv run python governance/scripts/log_entries.py view --kind preferences $(if $(REFS),--refs $(REFS))

entries-check: ## Validate docs/ledger and docs/preferences (file names, fields, no duplicate id, every id named has its file)
	uv run python governance/scripts/log_entries.py check
	uv run python governance/scripts/log_entries.py check --kind preferences

controls: lint ## Run every fitness control, then lint
	@for c in controls/fitness/*.py; do \
		echo "control: $$c"; \
		uv run python "$$c" || exit 1; \
	done

lint: ## Ruff lint + format check + ty type check
	uv run ruff check .
	uv run ruff format --check .
	uv run ty check

test: ## Run the test suite
	uv run pytest -q

check: ## The single gate: controls -> views --check -> governance -> ledger entries -> tests
	$(MAKE) controls
	$(MAKE) views-check
	$(MAKE) governance
	$(MAKE) entries-check
	$(MAKE) test

PLAN ?=
tasks: ## Task status derived from PR state (make tasks PLAN=tasks/<slug>; every plan if unset)
	@uv run python scripts/task-status.py $(PLAN)
