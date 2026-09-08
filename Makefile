.PHONY: ci compat fast-check format integration mutation-contract package-check

VENV := .venv
PYTHON := $(VENV)/bin/python

$(PYTHON):
	python3 -m venv $(VENV)

compat: $(PYTHON)
	@PYTHONPATH=src $(PYTHON) -m mermaiden.cli compat

format: $(PYTHON)
	@$(PYTHON) -m ruff format .
	@$(PYTHON) -m ruff check --fix .

mutation-contract: $(PYTHON)
	@PYTHONPATH=src $(PYTHON) scripts/render_mutation_contract.py --write

package-check: $(PYTHON)
	@set -eu; \
	temporary=$$(mktemp -d); \
	trap 'rm -rf "$$temporary"' EXIT; \
	artifacts="$$temporary/artifacts"; \
	environment="$$temporary/environment"; \
	mkdir -p "$$artifacts"; \
	$(PYTHON) -m build --outdir "$$artifacts"; \
	$(PYTHON) -m twine check "$$artifacts"/*; \
	$(PYTHON) -m venv "$$environment"; \
	"$$environment/bin/python" -m pip install --no-cache-dir "$$artifacts"/*.whl; \
	"$$environment/bin/python" -m pip check; \
	cd "$$temporary"; \
	"$$environment/bin/python" -I "$(CURDIR)/scripts/smoke_installed_wheel.py"

fast-check: $(PYTHON)
	@$(PYTHON) -m ruff format --check .
	@$(PYTHON) -m ruff check .
	@$(PYTHON) -m pyright
	@$(PYTHON) -m pytest
	@$(MAKE) compat

integration: $(PYTHON)
	@PUPPETEER_SKIP_DOWNLOAD=true npm ci
	@PATH="$(CURDIR)/node_modules/.bin:$$PATH" $(PYTHON) -m pytest -m integration

ci: $(PYTHON)
	@$(PYTHON) -m ensurepip --upgrade
	@$(PYTHON) -m pip install -e ".[dev]"
	@$(MAKE) fast-check
	@$(MAKE) integration
	@$(MAKE) package-check
