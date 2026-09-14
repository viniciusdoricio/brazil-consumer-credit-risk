# br-credit-monitor

**Who falls behind in Brazil — and does it depend more on what you earn, or on how you're employed?**

A credit portfolio monitoring analysis built on Banco Central do Brasil public data. It rebuilds, at national scale and from open sources, the kind of monitoring pack a credit-risk analyst produces every month for a risk committee.

> **Status: reconnaissance.** No findings yet. The question above is provisional and may change once the data has been profiled — see `docs/v1-decision.md`, which is currently a stub.

---

## Why this question

Delinquency is usually reported in aggregate, which hides the thing a lender actually needs to know: *where does risk concentrate, and who do you contact first?* Brazil's SCR.data publishes credit portfolio and arrears aggregates segmented by occupation type and income band, monthly, back to June 2012. That is enough to ask whether employment structure — a *aposentado* with payroll-deducted credit versus an *autônomo* at the same income — matters more than income itself.

## The trap this project is built around

**SCR.data has a definitional break at January 2025, and it is not economic.**

Until December 2024, an *ativo problemático* meant a credit rated **E–H** under Resolução CMN 2.682/1999. From January 2025, **Resolução CMN 4.966/2021** — Brazil's IFRS 9 equivalent — replaced the rating ladder with an expected-loss model in which each institution classifies its own problem assets.

A series plotted straight through that date contains a discontinuity caused by a change in definition, not by borrower behaviour. This project detects it, quantifies it, and builds its core measure on the **overdue bands** (*atraso 15–90 dias*, *atraso acima de 90 dias*), which are defined by days past due and stay consistent across the whole series.

There is a dbt test that asserts the break exists — it documents the finding in code and fails loudly if a future BCB revision changes it.

## What this data cannot do

Stated up front so nothing downstream implies otherwise:

- **It is aggregated.** There is no account-level public credit data in Brazil — bank secrecy and LGPD forbid it. Every conclusion is about segments, never individuals.
- **No true vintage analysis.** There is no origination-cohort dimension, so vintage curves are not possible from this source.
- **No observed roll rates.** The data is stock by arrears band, not tracked accounts. Month-to-month movement is *inferred* flow and is labelled as such wherever it appears.

## Running it

```bash
make setup     # uv sync + install git hooks
make fetch     # download the reconnaissance sample (3 months)
make build     # dbt models + schema tests
make test      # python tests
make report    # render the Quarto write-up
```

Requires [uv](https://docs.astral.sh/uv/), [Quarto](https://quarto.org/), and a Mac or Linux box. No database server — DuckDB runs in process. Nothing here needs a cloud warehouse, and saying so is a judgement call rather than a gap.

## Layout

```
scripts/fetch_scr.py     discover + download monthly archives from the BCB portal
models/                  dbt: staging → intermediate → marts
analysis/                Quarto write-up
tests/                   pytest (python layer); data assertions live in dbt
docs/                    the research, committed as it was done
```

`docs/` is not scaffolding. A reviewer reading it should be able to see how the
thinking was done, not only what it concluded:

| | |
|---|---|
| `project-brief.md` | the design, the deliverable it imitates, scope discipline |
| `research-prompt.md` | the reconnaissance brief this repo started from |
| `data_dictionary.md` | every column, its meaning, and when it changed |
| `data-landscape.md` | what public Brazilian credit data exists and how it joins |
| `analysis-design.md` | mix-vs-rate decomposition, supply-side confound, lag structure |
| `v1-decision.md` | the locked question, and the alternatives that lost |

## Sources

- [BCB SCR.data](https://dadosabertos.bcb.gov.br/dataset/scr_data) — monthly aggregated credit operations, Jun 2012–
- [BCB SGS](https://dadosabertos.bcb.gov.br/) — Selic, concessões, comprometimento de renda, endividamento das famílias
- [Resolução CMN 4.966/2021](https://www.bcb.gov.br/) — the accounting change behind the January 2025 break

## Licence

Code MIT. Data belongs to the Banco Central do Brasil under its open data policy — check current terms before republishing derived data.
