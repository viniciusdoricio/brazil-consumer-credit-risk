.PHONY: setup fetch build charts test lint report audit all

setup:          ## install deps and git hooks
	uv sync
	uv run pre-commit install

fetch:          ## download and stage SCR.data and the SGS series (see uv run fetch-data --help)
	uv run fetch-data

build:          ## build the dbt models and run their data tests (needs make fetch first)
	uv run dbt deps
	uv run dbt build

charts:         ## draw the six charts into analysis/figures (needs make build first)
	uv run make-charts

test:           ## python tests
	uv run pytest -q

lint:           ## ruff: lint and format check
	uv run ruff check . && uv run ruff format --check .

report: charts  ## render the write-up to analysis/_output (needs Quarto: brew install --cask quarto)
	uv run quarto render analysis/

audit:          ## recompute the report's headline numbers from the raw files and compare
	uv run python scripts/audit.py

all: setup fetch build charts test report audit  ## everything, from a fresh clone
