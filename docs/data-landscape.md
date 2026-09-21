# Brazilian public credit data — the landscape, and the January-2025 break

*Phases 2 and 3 of the reconnaissance (`docs/research-prompt.md`). Part A is the regulatory break,
checked in the data. Part B is every other source worth knowing, bounded to what it joins to.
Evidence tags are the ones defined in `docs/data-dictionary.md`: **[D]** data profiled, **[M2]**
SCR.data V2 methodology, **[3040]** reporting layout, **[R]** regulation text, **[SGS]** BCB series
API. Plus:*

| Tag | Source |
|---|---|
| **[RPM]** | BCB, *Relatório de Política Monetária*, Sep 2025, box "Impacto na taxa de inadimplência decorrente das novas regras de contabilização de instrumentos financeiros" (`bcb.gov.br/content/ri/relatorioinflacao/202509/rpm202509b6p.pdf`) |
| **[REF25]** | BCB, *Relatório de Estabilidade Financeira* v.24 n.2, Nov 2025, box "Mudança na proxy de ativos problemáticos" (`bcb.gov.br/content/publicacoes/ref/202510/RELESTAB202510-refPub.pdf`) |
| **[REF26]** | BCB, *Relatório de Estabilidade Financeira* v.25 n.1, May 2026 (`bcb.gov.br/content/publicacoes/ref/202605/RELESTAB202605-refPub.pdf`) |
| **[PTC]** | BCB, *Pesquisa Trimestral de Condições de Crédito*, results of June 2025 |

---

# Part A — The January-2025 break

## A.1 What changed, in two paragraphs

Until December 2024, Brazilian lenders provisioned under **Res. CMN 2.682/1999**: every credit
operation sat on a nine-step rating ladder, AA to H. Ratings were the lender's judgement, subject
to floors set by days past due: at least B from 15 days, C from 31, D from 61, E from 91, F from
121, G from 151, and H beyond 180 (art. 4). Each rating carried a fixed provision percentage.
Interest stopped accruing to income at 60 days overdue (art. 9). An H-rated operation was written
off after six months in H (art. 7), which BCB describes as "typically nine months after default"
**[R][RPM]**. SCR.data's *ativo problemático* was a BCB proxy on top of that ladder: operations more
than 90 days overdue, plus operations the BCB's own algorithm flagged as restructured and that the
lender rated E–H **[M2][REF25]**. *It was never "everything rated E–H"*: an E-rated loan that was
neither 90 days late nor restructured was not in it.

From 1 January 2025, **Res. CMN 4.966/2021** (with Res. BCB 352/2023 for the institutions BCB
regulates directly) replaced that with an expected-loss framework modelled on IFRS 9 **[R]**. There
is no rating ladder. Each instrument is placed in one of three **stages** (art. 37). Stage 1: credit
risk has not increased significantly since origination, provisioned for 12-month expected loss.
Stage 2: significant increase in credit risk, lifetime expected loss. Stage 3: **problem assets**,
lifetime expected loss given default (art. 47). A *problem asset* is now defined in the regulation
itself (art. 3): more than 90 days overdue, **or** any indication the obligation will not be paid in
full without recourse to collateral. Examples include restructuring, judicial recovery, breach of
material covenants, and a counterparty that no longer has the capacity to pay. The lender must use
a shorter delinquency trigger if evidence warrants it. Once one instrument of a counterparty is in
stage 3, all of that counterparty's instruments move there (art. 37 §5). Accrual stops when an
asset becomes a problem asset (art. 17), not at 60 days. Write-off happens when recovery is no
longer probable (art. 49), with no fixed timetable. Minimum *incurred-loss* provision floors rise
month by month after default by portfolio type C1–C5 and reach 100% only after 15 to 21 months
(Res. BCB 352, Anexo I) **[R][RPM]**. So in SCR.data from January 2025, `ativo_problematico` is the
lender's own stage-3 flag (*característica especial 19* in doc 3040) plus the 90-day and
restructuring components **[M2][REF25]**. **The biggest effect on the numbers comes from the change
in write-off dynamics, not from the definition.** Defaulted loans now stay in the portfolio longer,
which raises every stock-based >90 measure **[RPM][REF25]**.

## A.2 The break, in the data

PF, SCR.data V2, December→January against the prior year **[D]** (`scripts/recon/control.py`,
`scripts/recon/break.py`):

| % of PF portfolio | Dec-23 | Jan-24 | Δ control | Nov-24 | Dec-24 | Jan-25 | **Δ break** | Feb-25 | Jul-26 |
|---|---|---|---|---|---|---|---|---|---|
| 15–90 days overdue (`vencido_de_15_ate_90_dias`) | 0.854 | 0.864 | +0.010 | 0.935 | 0.876 | 0.902 | **+0.026** | 0.986 | 1.284 |
| >90 days overdue amounts (`vencido_acima_de_90_dias`) | 1.852 | 1.849 | −0.003 | 1.851 | 1.854 | 2.066 | **+0.212** | 2.161 | 3.176 |
| 90-day delinquency, full balance (`carteira_inadimplencia`) | 3.742 | 3.771 | +0.029 | 3.710 | 3.661 | 3.970 | **+0.309** | 4.086 | 5.815 |
| Problem assets (`ativo_problematico`) | 7.454 | 7.417 | −0.037 | 6.946 | 6.909 | 7.577 | **+0.668** | 7.580 | 9.360 |
| Problem assets beyond 90-day delinquency | 3.712 | 3.646 | −0.066 | 3.235 | 3.248 | 3.607 | **+0.359** | — | 3.546 |
| PF portfolio, R$ bn | 3,582 | 3,618 | +0.99% | 3,999 | 4,044 | 4,087 | +1.05% | 4,117 | 4,680 |

For PJ, problem assets moved 5.90% → 6.13% (+0.23 pp) against a control of +0.16 pp, and the PJ
portfolio fell 3.1% in the month against −1.7% in the control **[D]**.

**What the numbers say**

1. **Problem assets jumped +0.67 pp of the PF portfolio in one month.** In the control January they
   moved −0.04 pp. Of the jump, **+0.36 pp is outside the 90-day component**, which is the new lender
   flag replacing "restructured and E–H". It is clearly definitional in size and timing.
2. **The 90-day measures also stepped up** (+0.31 pp full balance, +0.21 pp overdue amounts, against
   roughly zero in the control). The official SGS 21084 shows January rises before 2025 between −0.06
   and +0.21 pp, and +0.26 pp in January 2026 when nothing changed **[SGS]** (`scripts/recon/sgs.py`),
   so part of January is seasonal. But the write-off change *by construction* shows up as an
   accumulation over months, not a one-month step. The January step understates the break in these
   measures (A.3).
3. **15–90 days barely moved** (+0.026 pp vs +0.010 pp). It is the one delinquency measure where
   January 2025 is indistinguishable from an ordinary January.
4. **The break is not uniform across segments.** Every PF occupation's 90-day rate rose by
   +0.19 to +0.41 pp, so rankings are preserved **[D]**. Problem assets by modality moved in
   *different directions*. PF real-estate financing went from R$45.7 bn to R$57.7 bn (+26%), while
   "Outros créditos", where card purchases sit, fell from R$4.7 bn to R$2.8 bn **[D]**. That matches
   BCB's finding of upward level breaks in real estate, payroll, vehicles and rural, and downward
   breaks in cards and non-payroll personal credit **[REF25]**. **A problem-asset comparison across
   segments before and after January 2025 is biased by product mix, not just shifted.**
5. **Income-band data broke in the same month for a different reason.** "Sem rendimento" rose from
   0.13% to 2.86% of PF balances and fell back to 0.27% in February **[D]** (`docs/data-dictionary.md`
   §2.1). That is a reporting artefact coinciding with the regulatory date, and it must not be read
   as part of the 4.966 effect.

## A.3 Which measures survive

| Measure | Survives Jan-2025? | Why |
|---|---|---|
| `vencido_de_15_ate_90_dias` / `carteira_ativa` | **Yes, with one small unquantified caveat** | Day-count definition unchanged; write-off never touches loans under 90 days under either regime. Caveat, documented in the reporting rule: since January 2025, doc 3040 overdue values include accrued contractual interest until an asset is a problem asset, whereas before accrual stopped at 60 days (IN BCB 414/2023; Carta Circular 3.869/2018 art. 6 §2). So balances 60–90 days overdue can be marginally higher. Data: Jan-25 step equals an ordinary January |
| `carteira_inadimplencia` / `carteira_ativa` (official 90-day rate) | **No** | Numerator accumulates loans that would previously have been written off. BCB counterfactual: **~70% of the 0.78 pp rise in SFN 90-day delinquency Jan–Jun 2025 is regulatory (0.53 pp)**, with a similar share for PF and PJ **[RPM]**. The effect "may vary over time" and was estimated only to June 2025 **[RPM]** |
| `vencido_acima_de_90_dias` / `carteira_ativa` | **No** | Same mechanism |
| `ativo_problematico` | **No** | Definition changed (A.1) and write-off dynamics changed. Breaks differ in sign by modality **[REF25]** |
| `carteira_ativa` (denominator) | **Scope and identity unchanged; level slightly inflated from 2025** | Same maturity-sum identity **[D]**; no visible level shift for PF (+1.05% vs +0.99%). It now includes the defaulted stock that stays longer. Whether 4.966 amortised-cost measurement changed reported balances is unknown |
| Cross-sectional *rankings* of 90-day rates across occupations within a month | **Plausibly yes, not provably** | All occupations moved the same direction in January 2025. The write-off effect differs by portfolio type (C1–C5 floors differ by product and collateral), so occupations with different product mixes are affected differently. Not testable with public data |

## A.4 Did BCB publish a restatement, bridge, or guidance?

| What exists | What it covers | Usable here? |
|---|---|---|
| **No restatement** of SCR.data under a common definition | The V2 methodology notes the definitional change and nothing more **[M2]** | — |
| Res. CMN 4.966 **art. 79**: institutions are *exempt* from presenting 2025 figures comparatively with prior periods **[R]** | Financial statements | Confirms no institution-level bridge is required |
| **Counterfactual 90-day delinquency** **[RPM]** | SFN, PF, PJ aggregates, Jan–Jun 2025. Method: average months-in-portfolio of defaulted operations by months since default, Jun-2023 to Dec-2024, applied to 2025 defaults. Explicitly ignores changes in modality or lender mix | Aggregate only. It can be *quoted* to size the break but cannot be applied to occupation or income cells |
| **Problem-asset proxy decomposition** into 90-day delinquency / restructuring / lender flag, with counterfactual lines by firm size and PF modality **[REF25]** | Charts to Jun 2025 | Same granularity limit. BCB's own guidance: pre/post comparisons "devem ser vistas com ressalvas" |
| **Comef minutes (62nd meeting)**, quoted in REF25 footnote 50: lower write-off volume "resultou em uma mensuração de inadimplência com valores mais altos do que os anteriormente calculados" | Qualitative | Citable statement of the mechanism |
| **REF May 2026** keeps the counterfactual framing: PF delinquency "ainda teria se elevado" even with unchanged write-off practice **[REF26]** | Qualitative for H2-2025 | Confirms part of the rise is real |
| REF statistical annex: the REF states chart data are published alongside it **[REF26]** | Possibly the counterfactual series by modality | **Unknown** whether the counterfactual lines are in the downloadable annex. To find out: open the annex workbook for REF Nov-2025 and May-2026 |

**Bottom line for the project.** No bridge exists at the granularity this project needs. The
defensible treatment is to (a) run break-sensitive measures only through December 2024, (b) use
15–90 days as the measure that runs through the present, and (c) quote BCB's aggregate
counterfactual to size the 2025 break rather than attempt to construct one.

---

# Part B — The landscape

## B.0 Summary

| Source | What | Grain | Freq. | History | Access | Licence | Joins to SCR.data on |
|---|---|---|---|---|---|---|---|
| **SCR.data V2** | Credit stock, overdue, problem assets | UF × segment × PF/PJ × occupation-or-CNAE × income-or-size × modality × sub-modality × origin × index | Monthly | 2012-07 → | Yearly ZIPs (no API) | **ODbL** | — |
| **BCB SGS** | Macro-credit series | National (some by modality/UF) | Monthly/daily | 2005–2011 → | REST JSON API | BCB open data | **month only** |
| **BCB REF** | Stability assessment from SCR microdata | Aggregates + charts | Semiannual | 2002 → | PDF + annex | Reproduction with attribution **[REF26]** | narrative/benchmark only |
| **BCB PTC** | Lender survey: credit standards and demand | 4 segments | Quarterly | 2011 → | xlsx series | BCB | **quarter × broad product** |
| **IBGE PNAD Contínua** | Employment, unemployment, income | National/UF × position in occupation | Monthly (moving quarter) / quarterly | 2012 → | SIDRA API | IBGE open | **month/quarter × UF**. **Occupation does not reconcile** |
| **IBGE IPCA** | Inflation | National | Monthly | 1980 → | SGS 433 / SIDRA | IBGE open | month (deflator) |
| **Novo CAGED / RAIS** | Formal hires/separations; formal job stock | UF × CNAE × CBO | Monthly / annual | Novo CAGED 2020 → | PDET microdata | Government open data | **month × UF**; CNAE to PJ only |
| **CNC PEIC** | Household survey: indebted / overdue / can't pay | Capitals, families | Monthly | 2010-01 → | Reports | not stated | **month only**; different unit |
| **Serasa / Boa Vista** | People with negative bureau records | Counts | Monthly | ~2016 → | Press releases; detail paid | proprietary | **none** |

The one-line answer: **nothing joins to SCR.data below the national-month or UF-month level, and
nothing joins on occupation or income at all.** Every external source is context, validation, or a
macro regressor, never a denominator for a segment rate.

## B.1 SCR.data — licence note

The CKAN record carries **Open Database License (ODbL)** **[D: CKAN API]**. ODbL requires
attribution and, for a *derived database* made public, release under the same licence. A published
report or chart is a "produced work" and needs attribution only. **Implication:** if the project
publishes its marts (CSV/Parquet) or a Tableau data source, they must carry ODbL and attribution.
The repo README currently says "check current terms". It should say ODbL.

## B.2 BCB SGS — the ten series that matter

Names are the official metadata strings from the SGS web service, not recalled codes **[SGS]**
(`scripts/recon/sgs.py`).

| # | Code | Official name (SGS metadata) | Unit | Coverage | Role in this project |
|---|---|---|---|---|---|
| 1 | **21084** | Percent of 90 days past due loans of credit operations outstanding – Households – Total | % | 2011-03 → 2026-07 | **Validation anchor.** Reconciles to SCR.data PF: median gap +0.02 pp over all 169 months, within 0.2 pp every month 2017–2024, widening to 0.23–0.33 pp in March–June 2026 (`docs/data-dictionary.md` §10). Longest consistent official read of the same concept |
| 2 | **21112** | Percent of 90 days past due loans of nonearmarked credit operations outstanding – Households – Total | % | 2011-03 → 2026-07 | Free-market (non-earmarked) PF delinquency. Closest official analogue of SCR `origem = Sem destinação específica` |
| 3 | **20541** | Credit operations outstanding – Households – Total | R$ mn | 2007-03 → 2026-07 | Denominator check. Built from doc 3050, not 3040, so it differs in scope **[RPM fn 6]** |
| 4 | **20633** | New operations – Households – Total | R$ mn | 2011-03 → 2026-07 | **Only public flow of new lending** (concessões). National; no occupation or income split |
| 5 | **20716** | Average interest rate of new credit operations – Households – Total | % p.y. | 2011-03 → 2026-07 | Price of credit |
| 6 | **20785** | Average spread of new credit operations – Households – Total | p.p. | 2011-03 → 2026-07 | Risk premium lenders charge; a supply-side proxy |
| 7 | **4189** | Interest rate – Selic accumulated in the month in annual terms (basis 252) | % p.y. | 1986-08 → 2026-09 | Monetary cycle (monthly). Code 432 is the daily target |
| 8 | **29034** | Household debt service ratio – Seasonally adjusted data (Households gross disposable national income) | % | 2005-03 → 2026-06 | Transmission channel Selic → debt service. **One month shorter** than SCR.data |
| 9 | **29037** | Household debt to income (Households gross disposable national income) | % | 2005-01 → 2026-06 | Leverage |
| 10 | **24369** | Unemployment rate – PNADC | % | 2012-03 → 2026-07 | Labour-market shock (IBGE, carried in SGS) |

Two technical series needed for normalisation, not analysis: **1619** *Minimum wage* (R$678 in
Jan-2013, R$1,412 Jan-2024, R$1,518 Jan-2025, R$1,621 Jan-2026). It fixes the R$ value of every
income band. And **433** *IPCA* monthly change, for real deflation **[SGS]**.

Considered and left out: 21082/21083 (total, PJ), because v1 is PF. 29035/29038 (ex-mortgage
variants) are worth a sensitivity check only. 20575 (*Nonearmarked… Personal credit –
renegotiation*) is relevant to restructuring but is a stock of one product.

**Trap — modality taxonomies.** SGS credit statistics come from doc 3050 (aggregate by modality),
SCR.data from doc 3040 (operation-level), with scope differences such as receivables prepayments
for firms **[RPM fn 6]**. SGS "modality" series do not map 1:1 onto SCR.data `modalidade` or
`submodalidade`.

## B.3 BCB Relatório de Estabilidade Financeira — the deliverable being imitated

**How section 1.2.2 *Crédito* is built (REF May 2026)** **[REF26]**. The same order is used in the
Nov-2025 edition:

1. **Introduction**: five bold, sentence-long headlines that *state findings* ("A materialização
   de risco aumentou no crédito às famílias…"), each followed by one paragraph of support.
2. **Broad credit and its long-run trend**: credit/GDP gap, bank credit vs capital markets.
3. **Firms**: capacity to pay (net debt/EBITDA, interest cover) → lenders' risk appetite (growth,
   origination-score quality, PTC) → **risk materialisation** (problem assets by size) →
   forward-looking PD of the performing stock by size.
4. **Households**: capacity to pay (individual income commitment, *CRI*, distribution by income;
   individual indebtedness) → risk appetite (growth of higher- vs lower-risk products; share of
   unsecured non-payroll credit) → risk materialisation (problem assets by modality and by lender
   segment, with the 4.966 counterfactual) → PD of the stock by modality.
5. **Provisions vs BCB's expected-loss estimates**, and capital to absorb any shortfall.

**What it publishes that SCR.data does not have:** individual-level income commitment and
indebtedness distributions (median, IQR, by modality), which BCB computes from microdata. Also PD
and LGD of the performing stock by modality. Also the problem-asset decomposition (delinquency /
restructuring / lender flag) with the write-off counterfactual. Also origination quality ("score
contratação"), lender segments (private S1, public, digital, other private, cooperatives), and stress
tests. Its credit numbers come from "saldo de carteira ativa dos clientes identificados no SCR", so
they differ from SGS **[REF26 fn 18]**.

**What that means for the project:** the professional version is ordered **capacity to pay →
appetite → materialisation → forward look → loss absorption**, and every chart carries a headline
that is a finding. Public data can support *materialisation* by segment (SCR.data), and *capacity
to pay* and *appetite* only nationally (SGS 29034/29037, 20633, PTC). It cannot support PD, LGD or
provisions at all.

## B.4 IBGE — PNAD Contínua and IPCA

Tables verified through the SIDRA metadata API (`servicodados.ibge.gov.br/api/v3/agregados/{id}/metadados`):

| Table | Content | Frequency | Coverage |
|---|---|---|---|
| 6320 | Employed persons 14+ by *posição na ocupação e categoria do emprego* | Monthly (moving quarter) | 2012-03 → 2026-07 |
| 4097 | Same classification | Quarterly | 2012-Q1 → 2026-Q2 |
| 5436 | Average real monthly income from work | Quarterly | 2012-Q1 → 2026-Q2 |
| 5434 | Employed persons by activity group | Quarterly | 2012-Q1 → 2026-Q2 |
| 4093 | Labour force, employed, unemployed, informality, by sex | Quarterly | 2012-Q1 → 2026-Q2 |

**Does PNAD's occupation taxonomy map onto SCR.data's? No.**

| SCR.data PF occupation (Receita Federal registry, main occupation) | PNAD *posição na ocupação* (survey, current main job) | Reconciles? |
|---|---|---|
| Servidor ou empregado público | Empregado no setor público (incl. militar e estatutário) | **Roughly**. PNAD includes informal public employees |
| Empregado de empresa privada | Empregado no setor privado, exclusive doméstico (com / sem carteira) | **Partly**. PNAD includes informal employees, and domestic workers are separate; unclear where SCR puts domestic workers |
| Empregado de entidades sem fins lucrativos | *(no category)*, inside private-sector employees | **No** |
| Aposentado/pensionista | *(no category)*. Retirees are mostly outside the labour force; PNAD position describes a job | **No** |
| Autônomo | Conta própria (com / sem CNPJ) | **Partly** |
| Empresário | Empregador (com / sem CNPJ) | **Partly**; "empresário" in a tax registry is not the same as "employer" |
| MEI | *(no category)*. Split across conta própria com CNPJ and empregador com CNPJ | **No** |
| Outros | *(no category)* | **No** |
| — | Trabalhador doméstico; Trabalhador familiar auxiliar | **No SCR counterpart** |

Beyond the labels, the units differ. SCR is R$ of credit exposure attached to a registry attribute;
PNAD is people from a household survey. **PNAD can supply UF-month labour-market context (e.g.
unemployment, share of *conta própria*) but must never be used as a denominator for an SCR
occupation rate.** The income side doesn't reconcile either. SCR bands are lender-reported
individual gross income, "presumed or estimated" allowed, in minimum wages **[3040]**. PNAD income
is survey-reported work income.

## B.5 CAGED / RAIS

- **Novo CAGED** (Ministério do Trabalho e Emprego, PDET): formal hires and separations by UF,
  CNAE, and CBO occupation code, monthly. Since January 2020 it is generated from eSocial/CAGED/
  Empregador Web with imputation. The **old CAGED series ends December 2019 and the new one starts
  January 2020**; they are not one series. (Source: MTE's "O que é o Novo Caged" page; the details
  of the imputation have not been verified here.)
- **RAIS**: annual stock of formal jobs, published with a lag of over a year.
- **Joins to SCR.data:** UF × month for formal net job creation as a regional shock. CNAE section
  matches only SCR **PJ** rows. CBO occupation *titles* have nothing to do with SCR's *natureza da
  ocupação*. **No PF occupation join.** For a national PF v1, CAGED adds little that PNAD
  unemployment does not.

## B.6 BCB Pesquisa Trimestral de Condições de Crédito (PTC) — the only public supply-side read

- Lenders assess credit standards (supply) and demand over the past and next three months, plus
  the factors behind them. Four segments: **PJ large firms; PJ micro-small-medium; PF consumer
  credit; PF housing**. Answers on a five-level scale are converted to −2…+2 and published as
  **unweighted means** **[PTC]**.
- Respondents in June 2025: PF Consumo 17, PF Habitacional 7, PJ Grandes 22, PJ MPMEs 28 **[PTC]**.
  The results "represent only the view of the institutions surveyed", not BCB's **[PTC]**.
- Time series: the report prints `…/ptc/xls/Series PTC.xlsx`, which **returned HTTP 404 on
  2026-09-14**. The working file is **`bcb.gov.br/content/publicacoes/ptc/xls/Series_PTC.xlsx`**
  (underscore), opened for this document **[D]**. It holds a dictionary sheet plus one sheet per
  segment (`GE`, `MPME`, `Consumo`, `Habitacional`). It is **quarterly from 2011-03 to 2026-06** and
  was "atualizados em 20/08/2026".
- **PF consumer standards are published by product** **[D]**: `PFC_oferta_geral`, `…_cartao`,
  `…_cheque` (overdraft), `…_consignado`, `…_semconsignacao` (non-payroll personal), `…_veiculos`.
  Each comes as last-3-months and next-3-months, plus demand and the factors behind it (employment,
  income commitment, confidence, rates, terms).
- The dictionary sheet says the headline indices are also in SGS: PF consumer supply **21393**,
  demand **21385**; PF housing supply **21395**, demand **21387**; large firms 21389/21381; MSMEs
  21391/21383. The product-level indices are workbook-only. Those codes come from BCB's workbook and
  have not been cross-checked against SGS metadata.
- **Joins to SCR.data:** quarter × product group. The PTC products (card, overdraft, payroll,
  non-payroll, vehicles, housing) line up with the PF product groups proposed in
  `docs/analysis-design.md` §1.4 far better than SGS modalities do. **Still no occupation or income
  split, and still national.** It is the best public evidence of the *direction* of supply by
  product.

## B.7 CNC — PEIC

- Survey of **about 18,000 consumers in all state capitals and the Federal District, monthly since
  January 2010**. Seven indicators: share of families with debt; main debt types; self-assessed
  level of indebtedness; debt horizon; **share with overdue bills**; share that will not be able to
  pay; days overdue (up to 30, 30–90, over 90) (`pesquisascnc.com.br/pesquisa-peic/`).
- Income or occupation breakdowns, access format and licence: **not stated** on the methodology
  page. PEIC reports have been published with income splits, but that isn't verified here.
- **Joins to SCR.data: month only.** The unit is families, not R$. "Overdue bills" includes
  non-financial creditors. The sample is capital cities only. Directionally useful as a sentiment
  lead; **not comparable** with SCR's 90-day rate.

## B.8 Serasa Experian / Boa Vista (Equifax)

- **Serasa, *Mapa da Inadimplência*:** counts of individuals with negative records. 81.7 million in
  February 2026 per Serasa's press page. It includes non-financial creditors (utilities, telecoms,
  retail). Public: headline counts and breakdowns in press releases. Detail sits behind commercial
  products.
- **Boa Vista SCPC / Equifax BoaVista:** indicators of new default registrations and credit
  recoveries, published as press releases.
- **Joins to SCR.data: none.** People-with-any-registered-overdue-bill is a different unit and scope
  from R$ of financial credit 90 days overdue. Not verified beyond press pages; methodology and
  revisions are not public.

## B.9 Other sources worth knowing

| Source | Why it matters | Join |
|---|---|---|
| **IF.data** (BCB) | Institution-level quarterly credit portfolios. PF/PJ and PJ size breakdowns are equivalent to SCR.data's **[M2]**. Concentration by lender | institution → none at occupation level. Not profiled here |
| **Res. BCB 352/2023 portfolio types C1–C5** | Collateral- and product-based groups that set the new provision floors **[R]**. Explains why the 2025 write-off effect differs by product | a lens for interpreting modality breaks, not a dataset |
| **Res. CMN 4.966 art. 72-A** | Restructurings between 1 May and 31 Dec 2024 caused by the Rio Grande do Sul floods are *not* problem-asset indicators **[R]** | RS × 2024-05…12: a known regional distortion in problem assets |
| **Doc 3040 layout and filling instructions** | The field-level truth behind SCR.data (income band rules, *característica especial 19*) **[3040]** | defines the columns |

Policy events that need verified dates before being overlaid on any chart: the Desenrola Brasil
renegotiation programme (2023–24), caps on revolving card interest, and changes to FGTS
*saque-aniversário* lending. REF26 notes the last one moved unsecured personal credit. **Not
verified here**; don't annotate a chart from memory.

## B.10 Where taxonomies do not reconcile — the list to check before any join

| Dimension | Sources | Reconciles? |
|---|---|---|
| PF occupation | SCR.data (tax registry) ↔ PNAD (survey position in job) ↔ CAGED (CBO title) | **No** (B.4, B.5) |
| PF income | SCR.data (lender-reported, individual, SM bands, presumed allowed) ↔ PNAD (survey income from work) | **No**; different population, unit and definition |
| Credit modality | SCR.data V2 (3040 Anexo 3, 13 groups + sub-modality) ↔ SCR.data V1 (16 IF.data groups) ↔ SGS (doc 3050) ↔ REF (Imobiliário, Consignado, Veículos, Não consignado, Cartão, Rural) ↔ PTC (Consumo, Habitacional) ↔ Res. BCB 352 (C1–C5 by collateral) | **No pair maps 1:1**; crosswalks are lossy and must be hand-built and documented |
| Lender type | SCR.data `segmento` ↔ V1 `tcb`/`sr` ↔ REF (Privado S1, Público, Digital, Privado-outros, SNCC) | **No** |
| Geography | SCR.data UF = borrower's residence (PF) or head office (PJ) **[M2]** ↔ CAGED = establishment ↔ PNAD = household | **Same codes, different meaning** for PJ and employment |
| "Delinquency" | SCR.data 90-day full balance ↔ SCR.data overdue amounts ↔ SGS 21084 (same concept as SCR full balance) ↔ PEIC (families with overdue bills) ↔ Serasa (people with records) | Only SCR full balance ↔ SGS reconcile |
| Problem assets | SCR.data ≤ Dec-24 (90 days + restructured E–H) ↔ SCR.data ≥ Jan-25 (lender stage-3 flag) ↔ REF proxy (90 days + restructuring algorithm + lender flag) | **No** across the break |
