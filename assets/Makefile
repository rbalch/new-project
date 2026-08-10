.PHONY: help build sync shell up down views views-check governance controls lint test check

.DEFAULT_GOAL := help

# --- Container ---------------------------------------------------------------

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Build Docker images
	docker compose build

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

check: ## The single gate: controls -> views --check -> governance -> tests
	$(MAKE) controls
	$(MAKE) views-check
	$(MAKE) governance
	$(MAKE) test
