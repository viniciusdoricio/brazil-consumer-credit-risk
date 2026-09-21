# brazil-consumer-credit-risk

**At the same income, does the kind of work you do change how often your debts go bad, or is it the kind of credit your work lets you get?**

*Com a mesma renda, o tipo de ocupação muda o risco de inadimplência, ou o que muda é o tipo de crédito a que cada ocupação tem acesso?*

An analysis of household credit risk in Brazil, built on Banco Central do Brasil public data. It rebuilds, at national scale and from open sources, the segment view a credit-risk team reviews every month: where delinquency concentrates, and whether that comes from the borrowers or from the products they hold.

> **Status:** the data has been profiled and the design is fixed ([`docs/v1-decision.md`](docs/v1-decision.md)). The data pipeline and the dbt models, including the ones that compute the analysis, are built and tested, and the six charts are drawn from them. The write-up, in Portuguese, is drafted in [`analysis/ocupacao-ou-produto.qmd`](analysis/ocupacao-ou-produto.qmd); until it is reviewed, this README states no findings on the question.

## Why this question

Delinquency is usually reported in aggregate, which hides what a lender needs to know: where risk concentrates, and who to contact first. Brazil's SCR.data publishes credit balances and arrears by occupation and income band, every month since 2012. That is enough to ask whether the kind of job matters once income is held fixed.

The comparison needs care. A retiree with payroll-deducted credit and a self-employed borrower at the same income look very different on paper, but much of that gap may come from the loans each can get rather than from how each repays. So the analysis splits each occupation gap into a same-product part and a product-mix part before drawing conclusions.

## The trap this project is built around

**SCR.data has a definitional break at January 2025, and it is not economic.**

Until December 2024, SCR.data's *ativo problemático* was loans more than 90 days overdue plus loans that were restructured *and* rated **E–H** under Resolução CMN 2.682/1999. It was not every E–H loan. From January 2025, **Resolução CMN 4.966/2021**, Brazil's IFRS 9 equivalent, replaced the rating ladder with an expected-loss model. The restructured-and-E–H component was replaced by each institution's own problem-asset flag.

A series plotted straight through that date contains a discontinuity caused by accounting rules, not by borrower behaviour.

**The overdue bands don't fully escape it.** Their definition, days past due, is unchanged. But under 4.966 lenders write defaulted loans off later, so balances more than 90 days overdue stay in the portfolio longer and the 90-day rate rises on its own. The Banco Central estimates that about 70% of the rise in 90-day delinquency in the first half of 2025 came from this change ([Relatório de Política Monetária, Sep 2025](https://www.bcb.gov.br/content/ri/relatorioinflacao/202509/rpm202509b6p.pdf)). Only the 15–90-day bucket runs through January 2025 unaffected.

So this project uses the 90-day rate only through December 2024 and the 15–90-day rate for anything after. Segment comparisons start in January 2017. The reporting threshold fell from R$1,000 to R$200 in June 2016, and occupations were substantially reclassified in January 2017. The evidence is in `docs/data-landscape.md` and `docs/data-dictionary.md`.

A dbt test asserts that the break exists ([`assert_january_2025_break_exists.sql`](tests/dbt/assert_january_2025_break_exists.sql)): in January 2025 household problem assets and the 90-day rate step up far beyond the previous January's move, while the 15–90-day rate doesn't. The test documents the finding in code and fails if a future BCB revision changes it.

## What the research found

Before any modelling, every month of SCR.data was profiled: July 2012 to July 2026, 43 million rows. The findings that shape the design:

- **Occupation and income can be crossed.** They form a genuine joint table, and all 72 occupation-by-income cells for individuals are populated in every month from January 2016.
- **Comparisons start in January 2017.** The reporting threshold fell from R$1,000 to R$200 in June 2016, and occupations were reclassified in January 2017, when the 90-day rate of every named occupation jumped while the national rate didn't move.
- **Income bands are compared within calendar years only.** They move every January with the minimum wage, and at several reporting events, including a permanent step in July 2025.
- **Rural credit has to be separated out.** It is 52% of the top income band's balances and 42% of the self-employed's, against 16% for all individuals (2024).

Every figure traces to a script and a source in [`docs/data-dictionary.md`](docs/data-dictionary.md).

## Assumptions

The results depend on each of these. The ones marked *could be wrong* are tested, or shown both ways, rather than taken on trust.

1. **The 90-day rate is comparable from January 2017 to December 2024, and only then.** Occupations were reclassified in January 2017, and write-offs changed in January 2025. dbt tests enforce both ends.
2. **The 15–90-day rate is unaffected by the January 2025 change.** It rose 0.026 pp that January, against 0.010 pp a year earlier. *Could be wrong* if lenders changed how they report early arrears in ways one month can't show.
3. **The recorded occupation describes the borrower.** It is a registry attribute, not necessarily the current job, and "Outros" (other) holds about a quarter of household credit. *Could be wrong:* a gap that changes sign when "Outros" is included is reported as fragile, not as a finding.
4. **An income band means the same thing within a calendar year, not across years.** Bands are multiples of the minimum wage, which resets every January, so every income comparison stays inside one year.
5. **Seven product groups are enough to separate product from occupation.** They come from a hand-built mapping of 68 modality and sub-modality pairs. *Could be wrong* for the ones whose group is a judgement call, such as card balances and unlabelled loans. So every split is re-run with those moved to their other plausible group and card purchases separated from card credit, and a split that shifts by more than a quarter of the gap is reported as unstable.
6. **A segment's rate describes the portfolio lenders built for it, not the people in it.** Rates are weighted by balance, one borrower can appear in several cells, and lenders decide who gets credit. Public data can't separate that choice from borrower behaviour, so no claim here is about how a group behaves.
7. **A cell needs R$1 bn of balance before its rate is ranked.** The threshold is a judgement. In 2024 it removes 16 of the 72 occupation-by-income cells, none of them in the headline comparisons.
8. **A share that moves more than 0.5 pp of household credit in one month is a reclassification, not lending.** Every documented reclassification since 2017 moves that much, except three minimum-wage resets. *Could be wrong* the other way: in nine months since 2017 a share moved that much with no documented cause, which may be real lending. Those months are flagged rather than read either way.
9. **The release used is final enough.** BCB republishes history. The analysis uses the release pinned in `data/raw/zips/MANIFEST.tsv`, and the September 2026 republication moved the household 90-day rate by at most 0.001 pp.

## What this data cannot do

Stated up front so nothing downstream implies otherwise:

- **It is aggregated.** There is no account-level public credit data in Brazil, because bank secrecy and the LGPD forbid it. Every conclusion is about segments, never individuals.
- **No true vintage analysis.** There is no origination-cohort dimension, so vintage curves are not possible from this source.
- **No observed roll rates.** The data is stock by arrears band, not tracked accounts. Month-to-month movement is *inferred* flow and is labelled as such wherever it appears.

## Reproducing the research

Requires [uv](https://docs.astral.sh/uv/) on macOS or Linux. DuckDB runs in process, so there is no database server to set up.

```bash
uv sync
uv run fetch-data
uv run python scripts/recon/panel.py data/parquet/scrdata data/recon/panel
```

`fetch-data` downloads every yearly SCR.data archive, checks each one against its CRC, records its size, date and SHA-256, converts each month to typed Parquet and fetches the SGS series. It skips whatever is already there. The first run takes about 15 minutes to download and 10 to convert; [`data/README.md`](data/README.md) has the details. Each script in `scripts/recon/` answers one research question, and [the index](scripts/recon/README.md) says which document uses it. The scripts that read single sampled months need those months fetched first; section 9 of the [data dictionary](docs/data-dictionary.md) has the commands.

For development, `make setup` installs the environment and the git hooks, `make fetch` runs `fetch-data`, `make build` builds the dbt models and runs their data tests, `make charts` draws the six charts into `analysis/figures/`, `make report` renders the write-up with [Quarto](https://quarto.org), and `make lint` and `make test` run the Python checks. CI runs all of them, with the dbt tests on the 2023 to 2025 data.

## Layout

```
scripts/recon/   the research scripts behind every figure in docs/
src/             the pipeline package; fetch-data downloads, verifies and stages the data
models/          dbt: staging, intermediate, marts, and the analysis models behind the charts
seeds/           dbt lookup tables: product groups, classification events, windows, occupation pairs
macros/          dbt macros
analysis/        the Quarto write-up, and the charts in analysis/figures/
tests/           pytest, and the dbt data tests in tests/dbt/
docs/            the research
```

| Document | What it covers |
|---|---|
| [`data-dictionary.md`](docs/data-dictionary.md) | every column, what it means, and every break in the series with its cause where one is documented |
| [`data-landscape.md`](docs/data-landscape.md) | the January 2025 break measured in the data, and what other public credit data exists and how it joins |
| [`analysis-design.md`](docs/analysis-design.md) | the decomposition, the confounds, the denominators, and what the data can't support |
| [`v1-decision.md`](docs/v1-decision.md) | the question, measures, windows and charts, and the alternatives that lost |

## Sources

- [BCB SCR.data](https://dadosabertos.bcb.gov.br/dataset/scr_data): monthly aggregated credit operations from July 2012
- [BCB SGS](https://www3.bcb.gov.br/sgspub/): official credit, delinquency and macro series
- [Resolução CMN 4.966/2021](https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo?tipo=Resolu%C3%A7%C3%A3o%20CMN&numero=4966): the accounting change behind the January 2025 break

## Licence

Code: MIT, see [LICENSE](LICENSE). Data: published by the Banco Central do Brasil under the Open Database License (ODbL). Charts and reports built from it need attribution, and any derived dataset published from this repository must also be released under the ODbL. Details in [`data/README.md`](data/README.md).
