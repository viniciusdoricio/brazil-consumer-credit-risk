.PHONY: setup fetch build test lint report all

setup:          ## install deps and git hooks
	uv sync
	uv run pre-commit install

fetch:          ## download SCR.data monthly archives (see scripts/fetch_scr.py --help)
	uv run python scripts/fetch_scr.py --recon

build:          ## run dbt models and tests
	uv run dbt build --project-dir . --profiles-dir .

test:           ## python tests
	uv run pytest -q

lint:
	uv run ruff check . && uv run ruff format --check .

report:         ## render the Quarto write-up
	quarto render analysis/

all: setup fetch build test report
