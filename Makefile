.PHONY: setup fetch build charts test lint report all

setup:          ## install deps and git hooks
	uv sync
	uv run pre-commit install

fetch:          ## download and stage SCR.data and the SGS series (see uv run fetch-data --help)
	uv run fetch-data

build:          ## build the dbt models and run their data tests (needs make fetch first)
	uv run dbt deps --project-dir . --profiles-dir .
	uv run dbt build --project-dir . --profiles-dir .

charts:         ## draw the six charts into analysis/figures (needs make build first)
	uv run make-charts

test:           ## python tests
	uv run pytest -q

lint:
	uv run ruff check . && uv run ruff format --check .

report:         ## render the Quarto write-up (needs Quarto: brew install --cask quarto)
	@if ls analysis/*.qmd >/dev/null 2>&1; then quarto render analysis/; \
	else echo "no Quarto documents in analysis/ yet"; fi

all: setup fetch build charts test report
