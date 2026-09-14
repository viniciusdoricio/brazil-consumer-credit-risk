# v1 — the locked decision

*Phase 5 of the reconnaissance. This is a decision, not a menu. It rests on
`docs/data_dictionary.md` (what the data is), `docs/data-landscape.md` (the break and the
landscape) and `docs/analysis-design.md` (method).*

---

## First, the direct answer about the proposed v1

**Occupation × income is supported by the data. The proposed measure and period are not.**

- **Supported:** SCR.data V2 publishes occupation and income as a genuine joint distribution. The
  grain is unique, there are no subtotal rows, and all 72 PF cells are populated in every month profiled
  from 2016 to 2026 (12 months; 70 of 72 in June 2013).
- **Not supported as written:** "*atraso acima de 90 dias* as a share of the portfolio, June 2012 –
  present". It fails in two places:
  1. **After January 2025 the 90-day stock is inflated by an accounting change.** BCB estimates
     about 70% of the first-half-2025 rise in 90-day delinquency was regulatory (write-offs
     delayed under Res. CMN 4.966), not borrower behaviour. The brief's premise that the overdue
     bands are consistent across the break holds for the definitions, not for the numbers.
  2. **Before June 2016 the population is different.** The SCR reporting threshold fell from R$1,000
     to R$200. PF operations rose a third in one month and the "Até 1 SM" portfolio a fifth.
- **Also not defensible as written:** comparing raw rates across occupations. A risk manager's first
  question would be "isn't that just payroll-deducted loans?" Retirees and public servants get
  *consignado*; the self-employed mostly don't. Without splitting product mix out, the comparison
  can't be defended in an interview.

So v1 keeps the question and changes the measure, the period and the method. Nothing below is a
weaker question under the old name. The additions make the original question answerable.

---

## 1. The question

> **At the same income, does the kind of work you do change how often your debts go bad — or is
> it the kind of credit your work lets you get?**

*Em português (README):* **Com a mesma renda, o tipo de ocupação muda o risco de inadimplência — ou
o que muda é o tipo de crédito a que cada ocupação tem acesso?**

## 2. Why this question, and the alternatives that lost

| Alternative | Why it lost |
|---|---|
| **A. The brief's v1 as specified** (90-day overdue, 2012–present, raw rates by occupation × income) | Measure breaks in 2025; low-income cells change population in 2016; raw occupation gaps are confounded with product access. The question survives, the specification doesn't |
| **B. The January-2025 break as v1** | BCB already published the quantification (the ~70% counterfactual). Re-deriving it nationally adds little. The segment-level version is unidentifiable, because no public counterfactual exists below the aggregate. It remains the best *LinkedIn post 1* and is carried in chart 1 |
| **C. Occupation only** (the brief's fallback if the data were marginals) | Not needed: the cross-tab exists. Income is clean *within* a year, and "at the same income" is exactly the control that makes the occupation comparison fair. The January-2025 income anomaly falls outside the 90-day window |
| **D. Product spread (payroll vs card)** | Close to what BCB's Financial Stability Report already publishes by modality, so it differentiates less. It enters v1 anyway, as the decomposition term |
| **E. Regional (UF)** | Cells get thin fast (27 × 72), and the 2024 Rio Grande do Sul flood restructurings are treated specially in the regulation (art. 72-A). Extension |
| **F. Early warning / Selic lag model** | One clean tightening episode inside the consistent cell-level window. No lag estimate from this data would be honest. Extension, descriptive only |
| **G. A full monthly monitoring pack for the latest month** | The closest imitation of the real deliverable, but its core measures (90-day, problem assets) are compromised after January 2025, which leaves only the 15–90 bucket. It becomes chart 6, "the current read" |

## 3. The exact specification

| Item | Locked value |
|---|---|
| Source | SCR.data **V2 only** (`scrdata_*`), yearly ZIPs pinned by SHA-256 (the history is re-published; data dictionary §1.1) |
| Population | PF, national. Sum over UF, lender segment, origin, index and sub-modality |
| Cells | 8 occupations × 9 income bands. **Primary analysis on 7 × 7 = 49 cells**, excluding occupation "Outros" and income "Indisponível"/"Sem rendimento" from comparisons. They stay in totals, and every headline is re-run with them included |
| Products | 7 PF groups built from `modalidade` + trimmed `submodalidade`: Imobiliário, Consignado, Pessoal não consignado, Cartão, Veículos, Rural, Cheque especial/outros (analysis design §1.4) |
| **Primary measure — D90** | `Σ carteira_inadimplencia / Σ carteira_ativa`: the full balance of operations with an instalment >90 days overdue. BCB's own concept, reconciles to SGS 21084 within ~0.1 pp. Sum numerators and denominators, never average rates |
| **Break-robust measure — D15** | `Σ vencido_de_15_ate_90_dias / Σ carteira_ativa` |
| Period, D90 | **2016-06 → 2024-12** (103 months) |
| Period, D15 | **2016-06 → 2026-07** (122 months; extends with each release) |
| Headline cross-sections | 12-month pooled windows: **calendar 2024** (last full year before the break), with **2019** (pre-pandemic) and **2022** (end of tightening) as stability checks |
| Minimum cell size | Cell or cell-product rates suppressed below a minimum pooled `carteira_ativa`, set from the distribution (starting point R$1 bn) |
| Method | Cross-sectional midpoint decomposition of each occupation gap into **same-product gap + product-mix gap**. Balance-weighted **dispersion across occupations within income bands vs across income bands within occupations**. Three-way shift-share of the national D90 change (pure rate / product mix / borrower mix) (analysis design §1) |
| Mandatory sensitivities | Lagged-denominator rates (D90 on `carteira_ativa` 12 months earlier; D15 on 3 months earlier). Including the residual categories. 2019 and 2022 windows |
| Macro overlay (one) | **Unemployment, SGS 24369.** If job type matters, occupation gaps should widen when unemployment rises. Selic works mainly through product pricing, which the decomposition already carries |

## 4. The six charts, each with its headline

Headlines are written as *claims with a slot*, because the findings are not computed yet. Each chart
also names the headline that replaces it if the data says the opposite. No headline gets filled in
by hand. Every number comes from a model.

| # | Chart | Headline it should carry | If the data says the opposite |
|---|---|---|---|
| 1 | **The trap.** National PF D90 (SCR.data and SGS 21084) and D15, 2016-06 → 2026-07. January 2025 marked; BCB's 0.53-of-0.78 pp counterfactual annotated | "Part of the rise in household delinquency since January 2025 is an accounting change, not borrowers; the 15–90-day measure didn't jump" (already supported by BCB's estimate and the Phase 2 data) | — |
| 2 | **The grid.** D90 heatmap, 7 × 7 cells, pooled 2024, cell size shown | "At the same income, 90-day delinquency differs by up to [x] points depending on occupation" | "Within an income band, occupation barely changes delinquency" |
| 3 | **Which matters more.** Balance-weighted spread across occupations within bands vs across bands within occupations, rolling 12 months 2016–2024, unemployment overlaid | "Occupation separates risk [more/less] than income does, and the gap [widened/held] when unemployment rose" | Stated with the reversed comparison |
| 4 | **Job or product?** For the three headline pairs (Aposentado vs Autônomo, Servidor vs Empregado privado, MEI vs Empresário) in two income bands: raw gap split into same-product and product-mix | "[Most/little] of the retiree–self-employed gap comes from access to payroll-deducted credit" | Same chart, reversed claim |
| 5 | **Mix vs rate.** National PF D90 change by episode (2016-06→2019-12, 2019-12→2022-12, 2022-12→2024-12): pure rate / product mix / borrower mix | "The 2022–24 rise in household delinquency was mostly [borrowers paying worse within the same group and product / a shift into riskier products / lending moving to riskier groups]" | — (all three outcomes are publishable) |
| 6 | **The current read.** D15 change, 12 months to 2026-07 vs 2024, by occupation × income, next to each cell's real portfolio growth | "Since the accounting change, early delinquency has risen fastest among [group], while lending to them [kept growing/shrank]" | "Early delinquency has risen evenly across groups" |

**The recommendation section is conditional on chart 4, and both branches are written in advance.**
- *If product mix dominates:* segment collections treatment and credit policy **by product within
  income band**. Occupation adds little once the product is known. Using it would mostly proxy for
  payroll eligibility.
- *If the same-product gap dominates:* occupation belongs in scoring and in collections
  prioritisation **within a product**. Say for which product and income bands the gap is largest.
  That is the "who do you call first" answer.

## 5. Extensions, in priority order, only after v1 is public

1. **Inferred early warning**: D15 → D90 progression ratio by cell, labelled *inferred*. It reuses
   the v1 marts, and it is the useful monitoring metric after 2025.
2. **The January-2025 break as a standalone piece**: BCB's counterfactual, the direction of breaks
   by product, and what anyone plotting SCR.data should do.
3. **Product pricing and supply**: payroll vs card spreads (SGS) against PTC credit standards by
   product (the PTC publishes PF standards by product).
4. **Regional (UF)**, pooled, with Rio Grande do Sul 2024 flagged.
5. **PJ** by CNAE section × firm size.
6. **Tableau Public** version of charts 2, 4 and 6.

This reorders the brief's list. Early warning moves first because it costs least on top of v1 and
is the metric that still works today. Regional drops because of cell thinness.

## 6. Risks to this design, and what would falsify the finding

| Risk | Why it matters | Test / what falsifies |
|---|---|---|
| Occupation is a tax-registry attribute, not the borrower's current job, and "Outros" is 25–28% of PF | Gaps may reflect registry quality | If a headline gap changes sign when "Outros" is included or excluded, it is reported as fragile, not as a finding |
| Product crosswalk from `submodalidade` (labels renamed 2013 → 2024; whitespace) | Misassigned products leak into "same-product gap" | Re-run with the ambiguous sub-modalities (e.g. card "não migrado", overdraft vs guaranteed account) moved between groups. Terms moving >25% of the gap means the split is unstable |
| **Growth dilution** (fast-growing segments look safe) | Rankings driven by portfolio age, not risk | Any ranking that flips under the lagged denominator is not reported |
| **Lender selection** (supply) | Rates reflect who got credit | Not testable with public data. Handled by language rules and growth-next-to-rate (analysis design §2) |
| Income bands drift with the minimum wage | "Same income" isn't the same R$ across years | All comparisons are within-window. If the 2019, 2022 and 2024 cross-sections disagree on the ordering, the claim is limited to 2024 |
| Pandemic period (2020–21 renegotiations and moratoria) | Artificially low D90 | The 2019-12→2022-12 episode is interpreted only net of that; the headline doesn't rest on it |
| Thin cells (MEI × high income; non-profit employees) | Extreme rates from tiny balances | Pooling plus minimum size. No headline rests on a suppressed cell |
| Balance weighting (mortgages dominate high-income cells) | High-income D90 reflects housing and rural credit | Decomposition carries it; chart 4 shows product mix explicitly |
| Data revision (V2 history re-published in 2026) | A later download may move numbers | SHA-256 pinned; the data vintage stated in the write-up |
| **Central claim falsified if…** | — | "Occupation matters more than income" is falsified if the spread across income bands within occupations exceeds the spread across occupations within bands in all three windows (2019, 2022, 2024). "It's the job, not the product" is falsified if the product-mix term is more than half of the raw gap for the headline pairs. Either outcome is publishable, and the write-up states which occurred |

## 7. Hours to a publishable v1

| Work | Hours |
|---|---|
| Rewrite `scripts/fetch_scr.py` (CKAN has no URLs; chunked range downloads; SHA pinning); full V2 download (~2 GB at the host's speed) | 6–8 |
| Fix the toolchain: pin `dbt-core` (current resolve pulls a pre-release that fails to build), commit a working `uv.lock`, CI green | 2–3 |
| Staging to Parquet; dbt staging/intermediate/marts; product crosswalk seed; tests (grain, shares 0–1, reconciliation to SGS 21084, **break assertion on D90 vs D15**, decomposition sums) | 14–18 |
| SGS ingestion (21084, 24369, 1619, 433) | 2–3 |
| Decomposition and dispersion models, sensitivities | 8–10 |
| Six charts in Quarto | 6–8 |
| Write-up in Portuguese: limitations first, then question, data, trap, findings, recommendation | 12–16 |
| README for a hiring manager; clean-machine reproduction; review | 5–7 |
| Contingency (~15%) | 8–10 |
| **Total** | **≈ 63–83 hours** |

The brief's "ships in two weeks" is realistic only at close to full-time. At 15–20 hours a week it
is four to five weeks. **A finished v1 beats an expanded one**, so the extensions list stays closed
until chart 6 is published.
