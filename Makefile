.PHONY: architecture ci compat compatibility diagrams-preview diagrams-test diagrams-validate fast-check format integration mermaid-sync mutation-contract package-check pytest quality

UV := uv
RUN := $(UV) run --no-sync
PYTHON := $(RUN) python

architecture:
	@$(RUN) lint-imports

compat:
	@PYTHONPATH=src $(PYTHON) -m mermaiden.cli compat

mermaid-sync:
	@mermaid_version="$$(PYTHONPATH=src $(PYTHON) -c 'from mermaiden import Application; print(Application.create().mermaid_version)')"; \
	PUPPETEER_SKIP_DOWNLOAD=true npm install --save-dev --save-exact "@mermaid-js/mermaid-cli@$$mermaid_version"

format:
	@$(RUN) ruff format .
	@$(RUN) ruff check --fix .

mutation-contract:
	@PYTHONPATH=src $(PYTHON) scripts/render_mutation_contract.py --write

package-check:
	@set -eu; \
	temporary=$$(mktemp -d); \
	trap 'rm -rf "$$temporary"' EXIT; \
	artifacts="$$temporary/artifacts"; \
	mkdir -p "$$artifacts"; \
	$(UV) build --out-dir "$$artifacts"; \
	$(PYTHON) -m twine check "$$artifacts"/*; \
	cd "$$temporary"; \
	$(UV) run --isolated --with "$$artifacts"/*.whl python -I "$(CURDIR)/scripts/smoke_installed_wheel.py" "$$artifacts"/*.tar.gz

quality:
	@$(RUN) ruff format --check .
	@$(RUN) ruff check .
	@$(RUN) pyright
	@$(MAKE) architecture

pytest:
	@$(RUN) pytest

fast-check:
	@$(MAKE) --jobs=3 quality pytest compat

integration:
	@PUPPETEER_SKIP_DOWNLOAD=true npm ci
	@PATH="$(CURDIR)/node_modules/.bin:$$PATH" $(PYTHON) -m pytest -m integration

diagrams-validate: integration

diagrams-preview:
	@PYTHONPATH=. $(PYTHON) scripts/render_preview.py

diagrams-test: diagrams-preview
	@open .dev/preview/index.html

compatibility:
	@$(MAKE) compat
	@$(MAKE) diagrams-preview
	@$(MAKE) diagrams-validate

ci:
	@$(UV) lock --check
	@$(UV) sync --locked --group dev
	@$(MAKE) --jobs=4 quality pytest compatibility package-check
