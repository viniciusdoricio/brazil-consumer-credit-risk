# Analysis design

*How the analysis is done, decided before any model or chart exists. Every constraint cited
comes from `docs/data-dictionary.md` or `docs/data-landscape.md`.*

---

## Recommendations in one screen

| Problem | Recommendation |
|---|---|
| **Mix vs rate** | Exact two-level midpoint (Kitagawa-style) decomposition. Aggregate change = **borrower mix** (occupation × income weights) + **product mix** within each cell + **pure rate** within cell × product. The same algebra, applied cross-sectionally, splits an occupation gap at a fixed income into "same-product gap" and "product-mix gap". **That split is the test v1 depends on.** |
| **Supply-side confound** | Can't be controlled: no origination flow by segment exists publicly. Present it instead. (1) Report every segment rate next to that segment's real portfolio growth. (2) Show a **lagged-denominator** rate as a mandatory sensitivity, so fast-growing segments can't look safe just by being new. (3) National PTC credit standards as context. (4) Write every claim as "the portfolio lenders built for group X performed Y", never "group X behaves Y". |
| **Lags / early warning** | Not in v1. At cell level the consistent window (2017-01 → 2024-12) contains **one** clean tightening episode (2021–22). Nationally, SGS 21084 adds a second (2013–15). Prewhitened cross-correlation at national level is the ceiling. Anything more is unjustifiable. The only segment-level leading signal is 15–90 → 90+ progression, and it is *inferred*, so label it that way. |
| **Denominators** | Rates within cells, weights as shares of PF portfolio, volumes in real R$ (IPCA). Seasonality handled year-over-year. Minimum cell size before a rate is shown. Income bands treated as *multiples of the minimum wage*, comparable within a month, never "the same income" across years. |
| **Measures** | **D90** = `carteira_inadimplencia / carteira_ativa` (BCB's 90-day concept; reconciles to SGS 21084) for **2017-01 → 2024-12** (start set by the January-2017 occupation reclassification, data dictionary §10); D15 from 2017-01. **D15** = `vencido_de_15_ate_90_dias / carteira_ativa` as the measure that runs through January 2025 to the present. Problem assets: **not used** as a time series. |

---

## 0. Units and notation

- **Cell** `c` = (occupation `o`, income band `b`) for PF, national. SCR rows are summed over UF,
  `segmento`, `origem`, `indexador` and `submodalidade`. 8 × 9 = 72 cells.
- **Product** `p` = PF product group built from `modalidade` + `submodalidade` (section 1.4). Around 7
  groups.
- For month `t`: `N_{cp,t}` = numerator (R$), `A_{cp,t}` = `carteira_ativa` (R$).
  - Rate: `r_{cp,t} = N/A`.
  - Product weight within cell: `v_{p|c,t} = A_{cp,t} / A_{c,t}`.
  - Cell weight in PF: `W_{c,t} = A_{c,t} / A_{PF,t}`.
  - Cell rate: `R_{c,t} = Σ_p v_{p|c,t} r_{cp,t}`. Aggregate: `R_t = Σ_c W_{c,t} R_{c,t}`.
- Bars denote midpoints between the two months compared: `x̄ = (x_0 + x_1)/2`. Δ denotes `x_1 − x_0`.

---

## 1. Mix versus rate

### 1.1 Why it is needed here specifically

The PF portfolio's composition moves a lot, and some of that movement is classification rather
than behaviour **[D]**:

- Occupation is reclassified in January: "Outros" −7.8 pp (2016), **−11.3 pp (2017, which also
  shifts named-occupation 90-day rates up by 0.4–2.2 pp)**, −2.3 pp (2018), −2.1 pp (2021), −0.6 pp
  (2023). MEI appears in 2016 and reaches 1.8% (data dictionary §10).
- Income bands move every January as the minimum wage resets: the top band typically loses
  0.5–0.8 pp and the lowest gains 0.4–1.8 pp.
- Income "Sem rendimento" 2.1% and "Indisponível" 0.01% in 2016-06, against 0.13% and 1.60% in
  2024-12: missing income apparently recoded from one band to the other. Plus a one-month "Sem
  rendimento" spike to 2.86% in 2025-01 (data dictionary §2.1).
- Portfolio ×4.1 in nominal R$ over the period.

A national delinquency series moves with those weights even if no cell's rate changes.

### 1.2 One-level decomposition (borrower mix vs within-cell rate)

For any two months `0 → 1`:

```
ΔR = Σ_c W̄_c · ΔR_c      (within-cell: groups got better or worse)
   + Σ_c R̄_c · ΔW_c      (borrower mix: weight moved between groups)
```

This is **exact**. For each cell, `W_1R_1 − W_0R_0 = W̄·ΔR + R̄·ΔW` holds algebraically, so there is
no interaction residual to allocate arbitrarily. The midpoint weighting makes the result
independent of which month is called the base.

### 1.3 Two-level decomposition (adds product mix)

Apply the same identity inside each cell:

```
ΔR_c = Σ_p v̄_{p|c} · Δr_{cp}      (pure rate: same group, same product, paid worse)
     + Σ_p r̄_{cp}  · Δv_{p|c}     (product mix: group shifted towards riskier products)
```

Substituting gives three additive terms that sum exactly to `ΔR`:

| Term | Formula | Reading |
|---|---|---|
| Pure rate | `Σ_c W̄_c Σ_p v̄_{p|c} Δr_{cp}` | Borrowers in the same group and product repaid worse |
| Product mix | `Σ_c W̄_c Σ_p r̄_{cp} Δv_{p|c}` | Groups moved into riskier products (e.g. from payroll loans to cards) |
| Borrower mix | `Σ_c R̄_c ΔW_c` | Lending moved towards riskier groups |

**Cells for time decompositions: occupation × product, not income.** Income-band membership
shifts mechanically every January (data dictionary §10), so across years an income "mix effect"
is mostly the minimum-wage reset, not a change in who borrows. Income stays in the
*cross-sectional* analysis (§1.4), where comparisons sit inside one calendar year.

**Comparison windows.** (a) Year-over-year for every month (`t` vs `t−12`), which removes January
seasonality, excluding pairs that span January 2017. (b) Fixed episodes that each start in a
January after a reclassification, so none contains one: **2018-01→2020-12** (pre-pandemic and
pandemic), **2021-01→2022-12** (tightening), **2023-01→2024-12** (high rates before the accounting
change). D15 adds 2025-01→latest by occupation. **No D90 window crosses 2025-01.**

### 1.4 Cross-sectional version: the test the v1 question needs

"Are *aposentados* safer than *autônomos* at the same income?" is a gap between two cells in the
same band `b`, in the same month. Apply the identity across groups instead of across time
(Oaxaca–Blinder with midpoint weights):

```
R_{A,b} − R_{B,b} = Σ_p v̄_p · (r_{A,b,p} − r_{B,b,p})     (same-product gap)
                  + Σ_p r̄_p · (v_{p|A,b} − v_{p|B,b})     (product-mix gap)
```

where `v̄_p` and `r̄_p` average the two groups. If most of the occupation gap is **product mix**, the
honest finding is "occupation matters because it decides which products you can get". The obvious
case is payroll-deducted credit, available mainly to retirees and public servants. If most is
**same-product gap**, occupation matters within products. **v1 should report both terms, not the raw
gap.**

**Rural credit makes this unavoidable.** In 2024 rural credit was 52.4% of "Acima de 20 SM" PF
balances and 42.3% of "Autônomo", against 16.0% of all PF **[D]**. Rural 15–90-day delinquency has
run far above its history since 2024, on top of a May seasonal rise (data dictionary §10). Without
the product split, the "high-income" and "self-employed" rates are largely rural-credit rates.

**Product groups (crosswalk built from `submodalidade`, documented as a seed table in dbt):**
Imobiliário (`modalidade = Financiamentos imobiliários`) · Consignado (`Crédito pessoal - com
consignação em folha de pagam.`) · Pessoal não consignado (`Crédito pessoal - sem consignação…`) ·
Cartão (`Cartão de crédito - *`, `Crédito rotativo vinculado a cartão de crédito`) · Veículos
(`Aquisição de bens - veículos automotores`, vehicle leasing) · Rural (`Financiamentos rurais…`) ·
Cheque especial / outros. The crosswalk must include the 2013 labels that were split later
(`Cheque especial e conta garantida` etc., data dictionary §2.1). This roughly matches REF's PF
groups, which makes the result comparable with BCB's framing. **The whitespace trap in
`submodalidade` must be trimmed before the join.**

### 1.5 Residual and unstable categories

- "Outros", "Indisponível" and "Sem rendimento" stay in as **explicit cells**, so the decomposition
  always sums to the published total. Every headline is re-run **excluding** them (weights
  renormalised) and both are shown if they differ materially.
- **Reclassification flag:** any cell whose weight moves by more than 0.5 pp of PF in a single month
  is flagged. Its mix contribution in that month is labelled "classification event" rather than
  borrower mix. January 2025 income bands trip this by a wide margin (+2.7 pp for "Sem
  rendimento").
- **Known classification events** (full history, data dictionary §10): occupation 2017-01 (breaks
  rates; before the window), 2018-01, 2021-01, 2023-01; income every January plus 2018-11, 2019-03,
  2020-08, 2021-09, 2025-01, 2025-07, 2026-05. The 0.5 pp flag catches all of them. The rule is
  kept to catch revisions in future releases.
- MEI is reported from 2018-01, the first month after which its weight grows gradually rather than
  in January jumps (0.38% in 2016, 0.68% in 2017, 1.06% from 2018-01).

### 1.6 Tests (dbt)

- `pure_rate + product_mix + borrower_mix = ΔR` within 1e-9 for every window.
- Weights sum to 1 per month (and per cell for `v`).
- Cell-level numerator and denominator reconcile to the national PF totals, which reconcile to SGS
  21084 within 0.2 pp for every month 2017–2024 (observed on the full history; data dictionary §10).

---

## 2. The supply-side confound

### 2.1 Can concessões observe supply by segment? No.

| Source | New lending? | By occupation / income? | Verdict |
|---|---|---|---|
| SCR.data | **No**. Stock only | yes (stock) | Can't see origination |
| SGS 20633 *New operations – Households – Total* | yes | **no**. National, by modality at best | Aggregate supply only |
| BCB PTC (`Series_PTC.xlsx`) | direction of credit standards, quarterly 2011-03 → | **no**. But PF standards are split **by product**: card, overdraft, payroll, non-payroll, vehicles, housing **[D]** | Qualitative, national. Matches the product groups in §1.4 |
| REF "score contratação" | origination quality | not public by segment | Not available |

So a segment's delinquency rate always mixes **who lenders chose to lend to** with **how those
borrowers repaid**. Tightening on a segment removes marginal borrowers, and the surviving
portfolio's rate falls with no change in behaviour.

### 2.2 What can be shown honestly

1. **Growth next to rate.** Every chart of a segment rate carries that segment's real portfolio
   growth (`A_{c,t}/A_{c,t−12}` deflated by IPCA). A segment whose rate fell while its portfolio
   shrank gets a "possible tightening" annotation, not a "borrowers improved" headline. Income
   bands shift every January, so the grid's cells carry growth within the window instead, from its
   first month to its last (`analysis_grid.real_growth_within_window`).
2. **Lagged-denominator rate (mandatory sensitivity).** New loans don't default in their first
   months, so a fast-growing portfolio looks healthier than a mature one with the same
   underwriting. Show
   `D90^lag_{c,t} = N_{c,t} / A_{c,t−12}` and `D15^lag_{c,t} = N_{c,t} / A_{c,t−3}` alongside the
   contemporaneous rate. When the ranking of two groups flips between the two, the ranking is not
   reported as a finding. This is a crude seasoning adjustment, **not** a vintage analysis, and
   the write-up must say so.
3. **National supply context.** PTC PF-consumo credit-standards index and SGS 20785 PF spread,
   quarterly, on one context chart. Stated as context, not as a control.
4. **Language rule.** "The portfolio lenders extended to *autônomos* earning 2–3 SM had a 90-day
   rate of X." Never "autônomos default at X".

### 2.3 What would falsify a supply story

If a group's rate fall coincides with *faster* real growth and a *looser* PTC reading, tightening
can't explain it. If it coincides with shrinking balances and tighter standards, the fall can't be
attributed to borrowers. The write-up shows which case applies rather than assuming.

---

## 3. Lag structure and early warning

### 3.1 What is observable

| Series | Frequency | Window usable for D90 | Notes |
|---|---|---|---|
| Selic, SGS 4189 | monthly | full | Turning points in monthly SGS 4189 (≥1.5 pp swings): lows 2013-01 (7.11), 2020-09 (1.90), 2024-06 (10.40); highs 2015-08 (14.15), 2022-09 (13.65), 2025-07 (14.90) **[SGS]** |
| Debt service ratio, SGS 29034 | monthly, SA | full, ends one month earlier | National only. Itself a function of rates and debt |
| Unemployment, SGS 24369 | monthly (moving quarter) | 2012-03 → | Smoothed by construction (3-month moving) |
| D90 PF by cell (SCR.data) | monthly | **2017-01 → 2024-12** (January-2017 occupation reclassification; data dictionary §10) | Stock; seasonal Januaries |
| D90 PF national (SGS 21084) | monthly | 2011-03 → 2024-12 | Doc 3050; not subject to the SCR threshold |
| D15 PF by cell | monthly | 2012-07 → present | Break-robust |

At **cell level** (2017-01 → 2024-12) the window starts after the 2015 Selic peak and contains
**one** clean tightening episode, 2021–22. The 2024–25 episode coincides with the accounting change,
and 2020–21 carries the pandemic renegotiation rules. **At national level** SGS 21084 reaches back to
2011 and adds 2013–15. **The effective number of independent tightening episodes is one per cell
and two nationally.**

### 3.2 Defensible method, and its ceiling

- **Prewhitened cross-correlation.** Fit a low-order AR model to monthly changes in Selic, filter
  both Selic and D90 changes with it, then compute the CCF. This avoids spurious lead-lag from
  shared autocorrelation. Report the lag of peak correlation with its approximate ±2/√n band.
  National PF only.
- **Episode alignment.** Plot D90 and D15 in months since each tightening start for the two clean
  episodes. With n = 2, this is description.
- **Not justified:** VARs, distributed-lag regressions by cell, Granger tests, or any claim of a
  segment-specific lag. Two cycles don't identify a lag distribution. All 72 cells face the same
  Selic path, so there is no cross-sectional variation in the shock. The COVID interventions and
  the 2025 break sit inside the sample. A lag number from this data would be false precision.

### 3.3 Early warning

- The only segment-level leading signal the data supports is **D15 → D90 progression**. A balance
  15–90 days overdue today becomes >90 within about three months unless it cures. The ratio
  `D90_{c,t} / D15_{c,t−3}` can be shown as an **inferred progression ratio**, labelled inferred.
  Cures, write-offs, new entries and exits are unobserved, so it is **not** a roll rate.
- After January 2025 this matters more. D15 stays valid while D90 is inflated by the write-off
  change, which makes D15 the right metric for "what is happening now".
- Whether D15 actually leads national D90 turning points can be checked descriptively on the two
  pre-2025 episodes. It can't be validated out of sample. **Recommendation: extension, not v1.**

---

## 4. Denominator and base effects

| Issue | Evidence | Treatment |
|---|---|---|
| What the base is | `carteira_ativa` = performing maturity buckets + overdue ≥15 days, modalities 01–13 of doc 3040, operations above the SCR threshold, all 3040 filers, domestic **[M2][D]** | Use as published. Note the unknown location of 1–14-day overdue amounts (U1) |
| Scope change 2016-06 (R$1,000 → R$200) | **[M2]**. PF operations +33.5% and "Até 1 SM" portfolio +20% in one month **[D]** (data dictionary §5.1) | National context may start 2012-07 with the break marked. Never compare operation counts across it |
| Occupation reclassified 2017-01 | "Outros" −11.3 pp; named-occupation 90-day rates +0.4 to +2.2 pp while the PF total moved +0.04 pp **[D]** (data dictionary §10) | **Cell-level analysis starts 2017-01.** Later January reclassifications (2018, 2021, 2023) are flagged classification events in decompositions |
| 2025 write-off change inflates base slightly | **[RPM][D]** | D90 stops at 2024-12; D15 continues |
| Lender universe changes (payment institutions, fintechs appear) | **[D]** | National PF totals include them. Segment is summed out in v1. Note it |
| 4.1× nominal growth 2013 → 2026 | **[D]** | Rates are scale-free; shares for composition; real R$ (IPCA, SGS 433) for levels |
| Growth dilution of rates | — | Lagged-denominator sensitivity (§2.2) |
| Seasonality (January rises) | **[SGS]** | Year-over-year comparisons; 12-month averages for level charts |
| Income bands move with the minimum wage | R$678 (2013) → R$1,621 (2026) **[SGS 1619]**. In 8 of 10 Januaries 2017–2026 the top band loses ≥0.5 pp of PF portfolio and the lowest gains ≥0.4 pp; recodings in 2018-11, 2019-03, 2021-09, 2025-07, 2026-05 **[D]** | **Compare bands within a calendar year only** (no January inside). The two mid-year minimum-wage resets, 2020-02 and 2023-05, move bands too, but fall outside the chosen windows. Lender reporting events cluster in real-estate and rural credit (data dictionary §10.5). Across years, say "2–3 minimum wages", never "the same income". No re-banding is possible. Post-2025 income cuts need the 2025-07 and 2026-05 recodings handled |
| Thin cells | Cells range from R$0.02 bn to R$433 bn **[D]** | Suppress a cell-month rate below a minimum `carteira_ativa`, to be set from the distribution (e.g. R$1 bn); pool to 12-month sums for thin cells |
| Exposure weighting | Rates weight by R$ balance; one borrower can sit in several income bands across lenders **[3040]** | State that a cell rate is a balance-weighted portfolio rate, not the share of people who defaulted |

---

## 5. What this data cannot do

The write-up must not imply any of these, including by vocabulary ("vintage", "roll rate", "PD",
"migration" are reserved words).

| Technique | Why not |
|---|---|
| **Vintage / cohort curves** | No origination date or cohort dimension. The lagged-denominator rate is a seasoning *proxy*, not a vintage |
| **Observed roll rates, transition matrices, migration** | Stock by bucket, not tracked accounts. Month-to-month bucket changes net inflows, cures, write-offs and new lending. Only *inferred* ratios, labelled as such |
| **PD, LGD, EAD, cure and recovery rates** | No account outcomes, no write-off or recovery flows |
| **Credit losses / charge-offs** | Write-offs leave the stock unrecorded. After 2025 their timing is lender-specific |
| **IFRS 9 / 4.966 staging and provisions** | No stage 1/2/3 distribution or provisions in SCR.data. Problem assets approximate stage 3 only, and only from 2025 |
| **Consistent problem-asset series across Jan-2025** | Definition and write-off dynamics changed; breaks differ by product **[REF25]** |
| **Borrower counts, default *frequency*, per-capita metrics** | Balance-weighted; operation counts suppressed (`-1`); one borrower can be in several cells |
| **Causal effect of occupation or income** | Lender selection, eligibility for payroll credit, lender-reported and presumed income, omitted variables. Descriptive only |
| **New lending, pricing or approval rates by occupation or income** | Not published |
| **Individual debt-service or leverage by segment** | BCB computes it from microdata for the REF; not public by occupation |
| **Lender-level analysis** | V2 has lender *segment* only |
| **Monthly UF × occupation × income rates** | Dimensionally available, statistically too thin without pooling |
