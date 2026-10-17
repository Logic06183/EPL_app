# Common tasks. `make help` lists them.
PY ?= python3
VENV ?= .venv
BIN := $(VENV)/bin

.PHONY: help install dev frontend test lint e2e check deploy-backend deploy-frontend

help:  ## Show this help
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-16s %s\n", $$1, $$2}'

$(BIN)/activate:
	$(PY) -m venv $(VENV)

install: $(BIN)/activate  ## Create .venv and install dev dependencies
	$(BIN)/pip install -r requirements-dev.txt

dev:  ## Run the API on :8001 with reload (the SPA expects this port on localhost)
	set -a; [ -f .env ] && . ./.env; set +a; \
	LOG_FORMAT=$${LOG_FORMAT:-text} $(BIN)/uvicorn app.main:app --reload --port 8001

frontend:  ## Serve the SPA on :3000
	$(PY) -m http.server 3000 --directory frontend

test:  ## Run backend tests
	$(BIN)/pytest -q

lint:  ## Lint backend + static-check frontend
	$(BIN)/ruff check .
	node scripts/check-frontend.mjs

e2e:  ## Browser regression tests (needs playwright + chromium)
	node scripts/e2e.mjs

check: lint test  ## Everything CI runs (except docker + e2e)

deploy-backend:  ## Build + deploy the API with Cloud Build
	gcloud builds submit --config cloudbuild.yaml

deploy-frontend:  ## Deploy the SPA to Firebase Hosting
	cd frontend && npx --yes firebase-tools@13 deploy --only hosting
