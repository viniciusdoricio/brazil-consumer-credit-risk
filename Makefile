.PHONY: setup fetch build test lint report all

setup:          ## install deps and git hooks
	uv sync
	uv run pre-commit install

fetch:          ## download and stage SCR.data and the SGS series (see uv run fetch-data --help)
	uv run fetch-data

build:          ## build the dbt models and run their data tests (needs make fetch first)
	uv run dbt deps --project-dir . --profiles-dir .
	uv run dbt build --project-dir . --profiles-dir .

test:           ## python tests
	uv run pytest -q

lint:
	uv run ruff check . && uv run ruff format --check .

report:         ## render the Quarto write-up
	quarto render analysis/

all: setup fetch build test report
