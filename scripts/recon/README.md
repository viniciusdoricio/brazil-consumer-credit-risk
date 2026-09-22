# Research scripts

Each script answers one question from the research and prints its result. The document that uses
the answer cites the script, so every figure in `docs/` can be traced back and rerun. The analysis
itself doesn't run these scripts: the pipeline in `src/` and the dbt models in `models/` compute
everything the report quotes.

Run them from the repository root after `uv sync`. Downloads and derived data go to `data/`, which is
gitignored. Scripts that read `data/recon.duckdb` take a different path from the `RECON_DB`
environment variable. Usage is at the top of each file.

For the full history, run `uv run fetch-data` (which replaced `fetch_years.py` and `to_parquet.py`),
then `panel.py`, then the script for the question at hand. The sampled-month scripts read
`data/recon.duckdb`, so they need all 18 months in section 8 of the data dictionary fetched with
`fetch_member.py` and loaded with `load_months.py` first; the exact commands are in its section 9.
A script whose months aren't loaded stops with an error rather than printing an empty table.

## Find and fetch the files

| Script | What it does | Used in |
|---|---|---|
| `remote_zip_index.py` | Lists every member of every yearly archive, with sizes, by reading only each ZIP's central directory | [`data-dictionary.md`](../../docs/data-dictionary.md) |
| `header_scan.py` | Reads the header and first row of every monthly file, V1 and V2, to date schema changes without a bulk download | [`data-dictionary.md`](../../docs/data-dictionary.md) |
| `fetch_member.py` | Downloads single monthly CSVs out of the yearly archives by range request, checking CRC32 and size | [`data-dictionary.md`](../../docs/data-dictionary.md) |
| `fetch_years.py` | Downloads the full yearly archives, resumably, verifies them and writes a manifest | [`data-dictionary.md`](../../docs/data-dictionary.md), [`v1-decision.md`](../../docs/v1-decision.md) |

## Load and stage

| Script | What it does | Used in |
|---|---|---|
| `load_months.py` | Loads sampled monthly CSVs into DuckDB with typed measures, keeping the raw text next to the trimmed text | [`data-dictionary.md`](../../docs/data-dictionary.md) |
| `to_parquet.py` | Converts every V2 month to typed Parquet, with a conversion log | [`data-dictionary.md`](../../docs/data-dictionary.md), [`v1-decision.md`](../../docs/v1-decision.md) |

## Profile the sampled months

| Script | What it does | Used in |
|---|---|---|
| `structure_checks.py` | Grain, values per dimension, cross-tab completeness, accounting identities and sentinels; V1 against V2 for the same month | [`data-dictionary.md`](../../docs/data-dictionary.md) |
| `crosstab_cells.py` | Occupation x income cells populated, and the shares of the unstable categories, for each loaded month | [`data-dictionary.md`](../../docs/data-dictionary.md) |
| `category_presence.py` | Dimension values missing from some of the five sampled months | [`data-dictionary.md`](../../docs/data-dictionary.md) |
| `v1_structure.py` | V1 structure by month, and V1 against V2 totals | [`data-dictionary.md`](../../docs/data-dictionary.md) |
| `threshold_2016.py` | What moved when the reporting threshold fell in June 2016 | [`data-dictionary.md`](../../docs/data-dictionary.md) |

## The January 2025 break

| Script | What it does | Used in |
|---|---|---|
| `jan2025_break.py` | The break side by side: June 2024, December 2024, January 2025, July 2026 | [`data-dictionary.md`](../../docs/data-dictionary.md), [`data-landscape.md`](../../docs/data-landscape.md) |
| `jan2025_control.py` | The same December-to-January move a year earlier, as a seasonal control | [`data-dictionary.md`](../../docs/data-dictionary.md), [`data-landscape.md`](../../docs/data-landscape.md) |

## Full history

| Script | What it does | Used in |
|---|---|---|
| `panel.py` | Month-by-month profile of all V2 months, and a scan for candidate breaks | [`data-dictionary.md`](../../docs/data-dictionary.md) |
| `vintage_diff.py` | What changed between two releases of the same months, when BCB republishes an archive | [`data-dictionary.md`](../../docs/data-dictionary.md) |
| `breaks_context.py` | Context for each candidate break: January shifts, moves in "Outros", income recodings | [`data-dictionary.md`](../../docs/data-dictionary.md) |

## Official series and other sources

| Script | What it does | Used in |
|---|---|---|
| `sgs.py` | SGS series names from BCB's metadata service, their coverage, and the seasonal baseline for January | [`data-dictionary.md`](../../docs/data-dictionary.md), [`data-landscape.md`](../../docs/data-landscape.md) |
| `sgs_scope.py` | Whether the gap to SGS 21084 comes from SGS leaving out cooperatives (it doesn't) | [`data-dictionary.md`](../../docs/data-dictionary.md) |
| `receita_natocup.py` | Receita Federal income-tax filers by occupation, 2008-2020: the lead on the 2016-17 occupation breaks | [`data-dictionary.md`](../../docs/data-dictionary.md) |

## Income bands

| Script | What it does | Used in |
|---|---|---|
| `income_shift_drivers.py` | Splits each income-band shift by lender segment, product and state | [`data-dictionary.md`](../../docs/data-dictionary.md) |
| `minimum_wage_test.py` | Tests the minimum-wage reading of the January shifts using the two mid-year increases | [`data-dictionary.md`](../../docs/data-dictionary.md) |
| `income_step_2025_07.py` | Tests explanations for the July 2025 step in the top income band | [`data-dictionary.md`](../../docs/data-dictionary.md) |
