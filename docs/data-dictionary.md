# SCR.data data dictionary

*Written from files opened and profiled,
not from documentation alone. Where the data and BCB's documentation disagree, the disagreement is
recorded and the data wins.*

**Evidence tags used throughout**

| Tag | Meaning |
|---|---|
| **[D]** | Observed in a data file profiled for this document (months listed below) |
| **[M2]** | BCB, *Metodologia do SCR.data – Versão 2* (`bcb.gov.br/pda/desig/metodologia_versao2.pdf`) |
| **[M1]** | BCB, *SCR.data – Metodologia* (V1) (`bcb.gov.br/content/estabilidadefinanceira/scr/scr.data/scr_data_metodologia.pdf`) |
| **[3040]** | BCB, *SCR – Instruções de Preenchimento do Documento 3040* (the regulatory reporting layout the dataset is aggregated from) |
| **[R]** | Regulation text, fetched from BCB's normativos API (Res. CMN 2.682/1999, Res. CMN 4.966/2021, Res. BCB 352/2023) |
| **[SGS]** | BCB time-series system, values and metadata fetched via API |
| **unknown** | Not established. Each one says what it would take to find out |

Every number here is reproducible with `scripts/recon/` (section 9).

---

## 0. The six things that change the design

1. **Occupation × income is a genuine cross-tab, not two marginal slices.** V2 has a unique grain
   of ten dimensions, no subtotal rows, and all 72 PF occupation × income cells populated in every
   month from January 2016 to July 2026 (127 months; 68–70 of 72 before 2016) **[D]**. The cross-tab also crosses UF,
   institution segment, modality and sub-modality. The v1 question is *structurally* supported.
   Section 6.
2. **"V1" and "V2" are not a date in the series.** They are two parallel publications with
   different schemas, each covering almost the whole history. File headers never change within
   either version across all 344 monthly files **[D]**. V2 (`scrdata_*`) is the maintained one and
   the only one with separate 15–90 and >90-day overdue columns. Use V2 only. Section 4.
3. **The >90-day measures do not survive January 2025 unchanged.** Their *definition* (days past
   due) is unchanged, but the *stock* depends on when lenders write loans off, and Res. CMN 4.966
   changed that. BCB's own estimate is that about 70% of the rise in 90-day delinquency to June
   2025 was caused by the rule change, not by borrowers. Section 5 and `docs/data-landscape.md`.
4. **The income band has its own breaks.** In January 2025 the PF "Sem rendimento" band went from
   0.13% to 2.86% of the PF portfolio for one month (0.27% in February) **[D]**. Over the longer run,
   missing income seems to have moved between bands: "Sem rendimento" 2.10% and "Indisponível"
   0.01% in June 2016, against 0.13% and 1.60% in December 2024 **[D]**. The bands are also
   measured in minimum wages, which are re-set every January. Section 2, `porte`.
5. **Occupation is reclassified in January, and once badly enough to break the series.** "Outros"
   fell 7.8 pp of PF balances in January 2016 and **11.3 pp in January 2017**. In January 2017 every
   named occupation's 90-day rate jumped (Autônomo 2.89% → 5.13%) while the PF total moved only
   +0.04 pp. Smaller January reclassifications followed in 2018 (−2.3 pp), 2021 (−2.1 pp) and 2023
   (−0.6 pp) **[D]**. **Occupation rates are not comparable across January 2017.** Section 10.
6. **The full V2 history has been profiled: 169 months, 43.1 million rows.** Structure is clean
   throughout. The breaks are in classification, scope and accounting, and each is dated in
   section 10.

---

## 1. Files, access and volume

### 1.1 Where the data is

| Item | Finding |
|---|---|
| Portal | CKAN dataset `scr_data` on `dadosabertos.bcb.gov.br`; licence **ODbL** (`license_id: odc-odbl`) **[D: CKAN API]** |
| **Trap: discovery** | The CKAN resources for the monthly data have **empty `url` fields**. The URL is a pattern written in the resource *description* **[D: CKAN API]**. The first draft of the fetch script assumed resources carry URLs, so it couldn't find the data. The pipeline uses the URL pattern directly (`src/brazil_consumer_credit_risk/scr.py`) |
| V2 files | `https://www.bcb.gov.br/pda/desig/scrdata_{YYYY}.zip`, one ZIP per **year** holding one CSV per month (`scrdata_YYYYMM.csv`) **[D][M2]** |
| V1 files | `https://www.bcb.gov.br/pda/desig/planilha_{YYYY}.zip` holding `planilha_YYYYMM.csv` **[D]** |
| Coverage, V2 | **2012-07 to 2026-07**, 169 months, no gaps, no duplicates **[D]**; the V1 methodology says the series starts June 2012 **[M1]**; V2 has no June 2012 file |
| Coverage, V1 | **2012-01 to 2026-07**, 175 months, no gaps **[D]**. BCB's portal says V1 "is available up to data-base June/2025 and will not be updated". **Disagreement:** V1 files exist through July 2026, with changed structure from July 2025 (section 3) |
| Release lag | "updated on the last business day of the month… 30 days after the close of each period" **[M2]**. On 2026-09-14 the latest month is 2026-07 **[D]** |
| Revisions | The Last-Modified dates of the V2 ZIPs for 2012–2023 are 27 Mar–16 Apr 2026, and for 2024–2026 are 2–12 Sep 2026 **[D: HTTP headers]**. **History is re-published.** BCB also withdrew the 2025 months in April 2025 "para revisão interna" linked to Res. 4.966, and republished them later (LAI answers, §10.4). A file downloaded later may not match one downloaded now. The build must pin SHA-256 hashes and Last-Modified dates (`data/raw/zips/MANIFEST.tsv`, written by `scripts/recon/fetch_years.py`) and say which vintage it used |

### 1.2 Format

| Item | V2 (`scrdata`) | V1 (`planilha`) |
|---|---|---|
| Encoding | UTF-8 **with BOM** **[D]** | UTF-8 with BOM **[D]** |
| Delimiter | `;` | `;` |
| Quoting | every field double-quoted **[D]** | unquoted, except `"-"` placeholders **[D]** |
| **Trap: delimiter inside a value** | CNAE label `Comércio; reparação de veículos automotores e motocicletas` contains `;` inside quotes. A naive split on `;` corrupts every PJ commerce row **[D]** | same label, unquoted form not observed in the rows sampled |
| Decimals | comma, no thousands separator (`633904,03`) **[D]**; no measure value in any profiled month contains `.`, and every value parses **[D]** | same **[D]** |
| Dates | `data_base` ISO `YYYY-MM-DD`, last calendar day of the month **[D]** | same |

### 1.3 Volume for the full history

From the central directory of all 30 yearly archives, read by HTTP range request without
downloading them **[D]** (`scripts/recon/remote_zip_index.py`):

| | Months | Zipped | Uncompressed | Recent month (zipped → raw) |
|---|---|---|---|---|
| V2 `scrdata` | 169 | **2.02 GB** | **13.8 GB** | ~15 MB → ~100 MB |
| V1 `planilha` | 175 | 4.26 GB | 40.1 GB | ~33 MB → ~295 MB |

Rows per V2 month: 196,751 (2012-07) to 322,852 (2025-06). **Full V2 history: 43,062,885 rows**,
counted on conversion of all 169 months **[D]** (`data/parquet/scrdata/conversion_log.jsonl`).

Every archive member is a plain `.csv` whose name matches the expected pattern. No member uses an
unexpected compression method, and the highest compression ratio is 10.5× **[D]**. Nothing
suggests a malformed or hostile archive. Each month used here was CRC32-verified against the
archive's central directory before it was written.

**Trap: transport.** The host resets long transfers. Whole-year downloads at roughly 0.3 MB/s
failed or stalled repeatedly, and so did single 30 MB range requests. Fetching in 4 MB ranges with
retries worked every time **[D]**. The fetch script needs to do the same.

### 1.4 Decision: read ZIPs in place, or expand?

**Expand once, to Parquet. Don't query the ZIPs.**

- DuckDB's CSV reader handles gzip/zstd-compressed files, not ZIP archives. Reading members in
  place would need a community extension or a Python shim, and would re-inflate 100 MB per month
  on every query.
- Raw layer: the yearly V2 ZIPs (2 GB), SHA-256 recorded, immutable, gitignored.
- Staging input: one typed Parquet file per month, written once by DuckDB with measures parsed
  from pt-BR decimals and dimension text trimmed (`scripts/recon/to_parquet.py`). **Measured:
  1.62 GB for all 169 months** (7.9–12.4 MB per month, zstd), against 13.8 GB of raw CSV. A full
  profile over all months runs in about 13 seconds.
- dbt reads the Parquet. V1 is not ingested at all (section 3).

---

## 2. V2 (`scrdata_YYYYMM.csv`), column by column

24 columns, identical header in all 169 months **[D]**. Types below are after parsing (the files
are text). Months profiled in full: 2013-06, 2023-12, 2024-01, 2024-06, 2024-11, 2024-12, 2025-01,
2025-02, 2026-07.

### 2.1 Dimensions

No dimension column has a null or empty value in any month profiled **[D]**.

| Column | Meaning | Values observed | Changes over time | Traps |
|---|---|---|---|---|
| `data_base` | Reference month **[M2]** | One value per file, last day of month **[D]** | — | Quoted in V2, unquoted in V1 |
| `uf` | State. PF by residential CEP, PJ by head-office CEP **[M2]** | 27 UFs **[D]** | none observed | No national-total rows. Don't look for "Brasil" **[D]** |
| `segmento` | Institution type, grouped from BCB's registry **[M2]** | Banco, Cooperativa, Financeira, Instituição de pagamento, Fintech, Desenvolvimento/Fomento, Arrendamento, Outros **[D]** | 6 values until 2017-12. `Instituição de pagamento` appears for PF in **2018-01** (PJ 2019-11), `Fintech` for PF in **2019-05** (PJ 2019-07). 8 values from 2019-05 **[D, full history]** | Label is `Instituição de pagamento` in the data and `Instituição de Pagamento` in the methodology. Segment membership changes as institutions change licence, so a segment series is not a fixed set of lenders. Instituições de pagamento held R$115.8 bn of PF credit in 2026-07 **[D]** |
| `cliente` | PF (individuals) / PJ (firms) **[M2]** | `PF`, `PJ` **[D]** | — | — |
| `cnae_ocupacao` | **Overloaded.** PF: *natureza da ocupação*. PJ: CNAE section **[M2]**. The V1 methodology says occupation comes from the Receita Federal registry and is the *main* occupation **[M1]**. The V2 methodology doesn't say. Doc 3040 has no occupation field **[3040]**, which is consistent with BCB attaching it from the tax registry | PF (8): Servidor ou empregado público; Empregado de entidades sem fins lucrativos; Empregado de empresa privada; Aposentado/pensionista; Autônomo; Empresário; MEI; Outros. PJ (22): 21 CNAE sections + `Não informados` **[D]** | **MEI**: 0% until 2015-12; 0.38% from 2016-01, 0.68% from 2017-01, 1.06% from 2018-01; 1.77% in 2026-07. **Outros** falls in January reclassifications: **2016 (−7.8 pp), 2017 (−11.3 pp), 2018 (−2.3 pp), 2021 (−2.1 pp), 2023 (−0.6 pp)** **[D, full history]** (§10) | (a) Filter on `cliente` before using this column. (b) **"Outros" is the largest PF occupation** and its share moves by 16 pp over the series, so it can't be treated as a behavioural segment. (c) Why a borrower is "Outros" is **not confirmed**. The source attribute is the income-tax return's *natureza da ocupação*, tied to a filing year, with 24 categories. Only 31.6 million people filed for 2020, so non-filers and "não especificada" returns plausibly feed "Outros" (§10.4). (d) A registry attribute can be stale relative to the borrower's current job |
| `porte` | **Overloaded.** PF: gross *individual* monthly income in federal minimum wages (SM). PJ: firm size **[M2][3040]** | PF (9): Sem rendimento; Até 1 SM; Mais de 1 a 2; 2 a 3; 3 a 5; 5 a 10; 10 a 20; Acima de 20 SM; Indisponível. PJ (5): Micro, Pequeno, Médio, Grande, Indisponível **[D]** | PJ `Indisponível` first appears **2018-11**. PF band shares shift every January (minimum-wage reset) and at recodings in 2018-11, 2019-03, 2021-09, 2025-01, 2025-07 and 2026-05 **[D, full history]** (§10) | (a) Doc 3040: income is reported **by each lender**, "from the most current information available", and **presumed or estimated income is allowed**. `Indisponível` is only permitted when reported income ≤ R$1 **[3040]**. The same person can therefore be in different bands at different lenders. (b) **Bands are relative to the minimum wage**, which rises each January: R$678 (2013), R$1,412 (2024), R$1,518 (2025), R$1,621 (2026) **[SGS 1619]**. Whether the band uses the SM of the reference month or of when income was captured is **unknown** (not stated in [M2] or [3040]; needs BCB confirmation). (c) **January-2025 anomaly** (below). (d) Data labels say `salários mínimos`; the methodology says `salários-mínimos`. Joining on labels from the PDF will fail |
| `modalidade` | Credit modality, Anexo 3 of the 3040 layout **[M2]** | 13 values **[D]** | Same set in every month profiled **[D]** | The data label is `Financiamentos rurais  (ex-financiamentos rurais e agroindustriais)`, with a **double space**. The methodology calls it `Financiamentos rurais e agroindustriais` |
| `submodalidade` | Sub-modality, Anexo 3 **[M2]** | 49 (2013-06); 55–56 (2023–2026) **[D]** | **Renamed or split** (dated on the full history: the overdraft and working-capital splits in **2014-02**; `Outros direitos creditórios descontados` **2016-09**; `Cartão de crédito - não migrado` and `Capital de giro com teto rotativo` **2017-05**; `Financiamentos agroindustriais` and `Industrialização` **2017-07**): `Cheque especial e conta garantida` → `Cheque especial` + `Conta Garantida`; `Capital de giro com prazo vencim. igual ou superior 30 d` / `…inferior a 30 d` → `…até 365 dias` / `…superior a 365 dias` / `…com teto rotativo`. New: `Cartão de crédito - não migrado`, `Financiamentos agroindustriais`, `Industrialização`, `Outros direitos creditórios descontados` **[D]** | **Leading/trailing whitespace in 5–8% of rows** (7,487–24,895 rows per month across all 169 months). Trim before grouping **[D]**. Any modality series below `modalidade` level needs a hand-built crosswalk |
| `origem` | Earmarked or not, Anexo 4 first level **[M2]** | Sem destinação específica; Com destinação específica **[D]** | — | — |
| `indexador` | Rate index, Anexo 5 first level **[M2]** | Prefixado, Pós-fixado, Flutuantes, Índices de preços, TCR/TRFC, Outros indexadores **[D]** | **TCR/TRFC first appears 2019-08 for PF, 2019-10 for PJ** (5 values before) **[D, full history]** | — |

**Unstable PF categories, share of PF portfolio (%)** **[D]**, from `scripts/recon/crosstab_cells.py`

| Category | 2013-06 | 2016-05 | 2016-06 | 2023-12 | 2024-06 | 2024-12 | **2025-01** | 2025-02 | 2025-06 | 2025-12 | 2026-07 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Income "Sem rendimento" | 3.84 | 2.39 | 2.10 | 0.20 | 0.10 | 0.13 | **2.86** | 0.27 | 0.15 | 0.70 | 0.64 |
| Income "Indisponível" | 0.28 | 0.02 | 0.01 | 1.21 | 1.38 | 1.60 | 1.96 | 1.96 | 2.25 | 2.17 | 2.08 |
| Occupation "Outros" | 41.53 | 37.32 | 37.95 | 25.18 | 25.18 | 26.10 | 25.76 | 25.93 | 26.36 | 27.14 | 27.85 |
| Occupation "MEI" | 0.00 | 0.37 | 0.38 | 1.49 | 1.57 | 1.57 | 1.62 | 1.62 | 1.65 | 1.70 | 1.77 |

Between 2016 and 2023, "Sem rendimento" fell from about 2% to about 0.1% and "Indisponível" rose
from about 0% to about 1.3%. The combined share stayed in the same range (2.1–2.4% in 2016, 1.4–1.7%
in 2023–24). That is consistent with missing income being **recoded** from one band to the other,
not with borrowers gaining income. When this happened and why is **unknown**. The months in between
haven't been profiled, and doc 3040's rule reserves "Indisponível" for reported income ≤ R$1
**[3040]**. The January-2025 spike did not recur in February, June or December 2025. In December
2024 → January 2025 the "Acima de 20 SM" share also fell from 20.28% to 17.50% and "Até 1 SM" rose
from 8.51% to 9.28% **[D]** (`scripts/recon/jan2025_control.py`).

In January 2025, "Sem rendimento" went from R$5.4 bn to R$116.8 bn. That included R$56.1 bn of
rural credit, up from R$0.4 bn, and spread across every occupation (Autônomo R$0.4 → 23.8 bn,
Empresário R$0.8 → 28.8 bn) **[D]**. Most of it reverted a month later. This is a reporting event,
not borrower behaviour. **Any income-band time series has to handle January 2025 explicitly.** The
recoding between "Sem rendimento" and "Indisponível" means neither band is a stable population, so
the design keeps both out of comparisons.

### 2.2 The grain

`(data_base, uf, segmento, cliente, cnae_ocupacao, porte, modalidade, submodalidade, origem,
indexador)` is **unique** in every month profiled (e.g. 310,193 rows = 310,193 distinct tuples in
2026-07). There are no subtotal rows **[D]**. Every aggregate must be built by summing rows.

### 2.3 Measures

All measures are R$, parsed from pt-BR text into `DECIMAL(22,2)`. No parse failures and no
negative values in any month profiled **[D]**.

| Column | Meaning **[M2]** | Checked identity **[D]** | Traps |
|---|---|---|---|
| `numero_de_operacoes` | Number of credit operations in the cell | — | **Sentinel `-1`** on 82,406 rows holding R$475.8 bn (2026-07) and on 55,253 rows in 2013-06. The V2 methodology doesn't mention it. V1 publishes `<= 15` for cells with ≤15 operations **[M1]**, so reading `-1` as "≤15, suppressed" is **an inference by analogy, not documented**. Never sum this column without handling `-1`. It is a stock count, not new lending |
| `a_vencer_ate_90_dias` … `a_vencer_acima_de_5400_dias` | Performing balance by remaining maturity (≤90, 91–360, 361–1080, 1081–1800, 1801–5400, >5400 days) | — | Maturity buckets, **not** delinquency buckets |
| `carteira_a_vencer` | Sum of the six a-vencer columns | exact on every row, every month | — |
| `vencido_de_15_ate_90_dias` | Overdue *amounts* 15–90 days past due | — | Amounts overdue, not the whole balance of the loan |
| `vencido_acima_de_90_dias` | Overdue *amounts* >90 days past due | — | Same. **Not** the official delinquency concept (see `carteira_inadimplencia`) |
| `carteira_vencida` | 15–90 + >90 | exact on every row, every month | — |
| `carteira_ativa` | a-vencer + vencida. Portfolio defined as maturities of modalities 01–13 of the 3040 layout **[M2]** | **242–1,069 rows off per month (R$6–72 M) from 2012-07 to 2016-04**; ≤97 rows from 2016-05 to 2016-12; exact on every row from 2017-01 except 1 row in 2024-12 **[D, full history]** | (a) Where amounts **1–14 days overdue** sit is **unknown**. There is no column for them and the identity holds, so they're either inside `a_vencer_ate_90_dias` or excluded. Resolving it needs BCB confirmation (`scr.data@bcb.gov.br`). (b) **Scope threshold change**: operations above R$1,000 until May 2016, above R$200 from June 2016 **[M2]**. See section 5.1 |
| `carteira_inadimplencia` | Full balance (performing + overdue) of operations with **any instalment >90 days overdue**. The V1 name is `carteira_inadimplida_arrastada` **[M2][M1]** | ≠ `vencido_acima_de_90_dias` on 58,961–89,136 rows per month. PF 2026-07: 5.82% of portfolio vs 3.18% | **This, divided by `carteira_ativa`, is BCB's official 90-day delinquency concept.** It reconciles with SGS 21084 for PF (table below). The two ">90" columns are different measures. Label them explicitly everywhere |
| `ativo_problematico` | Balance of operations classified as problem assets **[M2]** | ≥ `carteira_inadimplencia` except 2–118 rows per month | **Definition changed in January 2025** **[M2]**: until Dec 2024, >90 days overdue OR restructured with an E–H rating (restructuring detected by a BCB algorithm). From Jan 2025, operations that lenders themselves flag as problem assets (*característica especial 19* in doc 3040). Not comparable across the break. See `docs/data-landscape.md` |

**Reconciliation to the official series.** PF `carteira_inadimplencia / carteira_ativa` **[D]** vs
SGS 21084, "Percent of 90 days past due loans of credit operations outstanding – Households – Total"
**[SGS]**:

| Month | SCR.data V2 | SGS 21084 |
|---|---|---|
| 2013-06 | 4.66% | 4.62% |
| 2024-06 | 3.74% | 3.71% |
| 2024-12 | 3.66% | 3.63% |
| 2025-01 | 3.97% | 3.89% |
| 2026-07 | 5.82% | 5.81% |

The PF numerator and denominator are the ones BCB uses, within about 0.1 pp in these months. Over all 169 months the median gap is +0.02 pp; every month from 2017 to 2024 is within 0.2 pp; the gap widens to 0.23–0.33 pp in March–June 2026 (§10). PJ reconciles less
well (e.g. 3.02% vs SGS 21083 3.31% in 2026-07). The V1 methodology warns the file may differ from
consolidated statistics **[M1]**, and PJ is out of scope for v1 anyway.

---

## 3. V1 (`planilha_YYYYMM.csv`), and why it is not used

23 columns, identical header in all 175 months **[D]**. Grain `(data_base, uf, tcb, sr, cliente,
ocupacao, cnae_secao, cnae_subclasse, porte, modalidade, origem, indexador)` unique **[D]**.

| Column | Finding | Trap |
|---|---|---|
| `tcb` | Bancário / Cooperativas / Não bancário **[M1][D]** | **All rows `-` from 2025-07** (checked 2025-07, 2026-07); three values through 2025-06 **[D]** |
| `sr` | Prudential segment S1–S5 under Res. 4.553/2017 **[M1]** | **NULL on every row in 2013-06**, populated by 2024-12. When it starts is **unknown**, presumably after the 2017 rule. Not a usable time dimension |
| `cliente` | PF / PJ | — |
| `ocupacao` | `PF - <occupation>`; `-` for PJ | Prefix; placeholder rows |
| `cnae_secao`, `cnae_subclasse` | `PJ - <section>`; 7-digit subclass only where the subclass × UF × size cell has >5 firms, otherwise the section **[M1]**. 1,253–1,254 distinct subclasses **[D]** | `aqüicultura` spelling differs from V2 `aquicultura` |
| `porte` | `PF - <band>` / `PJ - <size>` | **Right-padded with spaces on 100% of rows** **[D]** |
| `modalidade` | **A different taxonomy**: 16 IF.data-style groups (`PF - Cartão de crédito`, `PF - Veículos`, `PF - Empréstimo com consignação em folha`…) **[D][M1]** | Doesn't map 1:1 to V2 `modalidade`. BCB publishes an equivalence workbook (`Equivalencia_Modalidades.xlsx`) **[M1]** |
| `numero_de_operacoes` | Sentinel `<= 15` on 679,662 rows / R$1,081 bn (2026-07) **[D][M1]** | — |
| `vencido_acima_de_15_dias` | All overdue amounts >15 days | **No 15–90 / >90 split.** V1 cannot carry an early-delinquency measure |
| `carteira_ativa` | = six a-vencer columns + `vencido_acima_de_15_dias`, exactly, on every row (2026-07) **[D]** | **Disagreement:** [M1] defines "carteira total" as the a-vencer items only |
| `carteira_inadimplida_arrastada` | Same concept as V2 `carteira_inadimplencia` **[M1]** | — |
| `ativo_problematico` | As V2 | — |

**Structural change in V1 between 2025-06 and 2025-07** **[D]** (`scripts/recon/v1_structure.py`):
rows 1,025,243 → 891,135; PF rows 161,076 → 116,894; `tcb` collapses to `-`. That is consistent
with BCB's note that V1 stopped being maintained at June 2025, but the files kept coming.

**V1 and V2 disagree on the size of the portfolio for the same month** **[D]**:

| Month | PF carteira V1 | PF carteira V2 | V2 − V1 |
|---|---|---|---|
| 2013-06 | R$1,123.2 bn | R$1,141.1 bn | +1.59% |
| 2024-12 | R$3,999.0 bn | R$4,044.4 bn | +1.13% |
| 2026-07 | R$4,593.8 bn | R$4,680.3 bn | +1.88% |

PJ 2026-07: +12.0%. The >90 and problem-asset totals agree more closely (PF 2026-07: arrastada
R$268.8 bn vs R$272.1 bn). The cause is **unknown**. Possibilities include different institution
coverage, a different extraction vintage, or the aggregation of small cells. Resolving it needs a
segment-level comparison, which V1's collapsed `tcb` prevents after 2025-06, or an answer from BCB.
It doesn't matter for the design as long as nothing mixes the two versions.

**Decision: V1 is not ingested.** It lacks the overdue split and the institution segment, uses a
different modality taxonomy, and is no longer maintained.

---

## 4. When does V1 become V2?

**It doesn't, in the sense the original plan assumed.** There is no data-base month at which the schema
switches:

- All 175 V1 files share one header; all 169 V2 files share another **[D]**
  (`scripts/recon/header_scan.py` reads the header and first row of every monthly file).
- V2 is a **re-publication of the full history** in a new schema (2012-07 onward), regenerated in
  2026 (section 1.1). V1 runs 2012-01 onward and is degraded from 2025-07.
- What *does* change over time sits inside the columns: category sets (`segmento`, `indexador`,
  `submodalidade`, PF `MEI`, PJ `Indisponível`), classification (January reclassifications of
  occupation, above all 2017; income recodings), reporting (the January-2025 income event), scope
  (June 2016) and meaning (`ativo_problematico` from January 2025). All dated in section 10.

**Column crosswalk V1 → V2**

| V1 | V2 | Notes |
|---|---|---|
| `data_base`, `uf`, `cliente`, `origem`, `indexador` | same | V1 values unquoted |
| `tcb`, `sr` | (removed) | V2 has `segmento` instead, a different grouping |
| — | `segmento` (added) | |
| `ocupacao` + `cnae_secao` | `cnae_ocupacao` | merged; prefixes dropped |
| `cnae_subclasse` | (removed) | V2 stops at CNAE section |
| `porte` | `porte` | prefix and padding dropped |
| `modalidade` (16 IF.data groups) | `modalidade` (13 layout groups) + `submodalidade` (added) | **same name, different taxonomy** |
| `numero_de_operacoes` (`<= 15`) | `numero_de_operacoes` (`-1`) | sentinel changed |
| `vencido_acima_de_15_dias` | `vencido_de_15_ate_90_dias` + `vencido_acima_de_90_dias` (+ `carteira_vencida`) | split |
| — | `carteira_a_vencer` (added) | |
| `carteira_ativa` | `carteira_ativa` | same identity; V2 totals 1–2% higher for PF |
| `carteira_inadimplida_arrastada` | `carteira_inadimplencia` | **renamed**, same concept |
| `ativo_problematico` | `ativo_problematico` | same; both change meaning Jan-2025 |

---

## 5. Are the overdue measures and the denominator consistent across the series?

### 5.1 The June-2016 scope change

SCR's identification threshold fell from operations above R$1,000 to above R$200 at data-base
June 2016 **[M2][M1]**. That changes the population in both numerator and denominator at once.

**Effect in the data, May → June 2016** **[D]** (`scripts/recon/threshold_2016.py`):

| PF | 2016-05 | 2016-06 | Change | Official comparison |
|---|---|---|---|---|
| Operations (cells with a count) | 252.0 M | 336.5 M | **+33.5%** | — |
| `carteira_ativa` | R$1,520.7 bn | R$1,547.8 bn | **+1.79%** | SGS 20541 PF outstanding (doc 3050, no threshold): +0.24% |
| "Até 1 SM" `carteira_ativa` / operations | R$83.0 bn / 31.4 M | R$99.6 bn / 55.0 M | **+20.0% / +75%** | — |
| "Outros créditos" (card purchases) `carteira_ativa` | R$111.3 bn | R$121.1 bn | +8.8% | — |
| 90-day rate (`carteira_inadimplencia`) | 4.390% | 4.268% | −0.12 pp | SGS 21084: 4.37% → 4.10% (−0.27 pp) |
| 15–90 days | 1.051% | 1.079% | +0.03 pp | — |

**Reading.** The scope change is large in *counts*: a third more PF operations in one month, mostly
small card and low-income loans. It is material in the *composition of low-income cells*: the
"Até 1 SM" portfolio grew 20% overnight. In *aggregate balances* it is modest, adding about 1.5 pp
of portfolio above the official series. The aggregate 90-day rate fell, but the official series,
which the threshold doesn't affect, fell more in the same month. So the rate effect can't be
separated from whatever else moved in June 2016, and at the aggregate it is small.
`numero_de_operacoes` must never be compared across 2016-06.

**Decision:** cell-level analysis starts at **2016-06**, because the membership of the low-income
cells changed. Only national context series may run from 2012-07, with the break marked.
**Superseded for occupation by section 10:** the January-2017 reclassification moves the start of
occupation analysis to 2017-01.

### 5.2 The January-2025 accounting change

The column definitions don't change **[M2]**, but three rules that decide what sits in each column
did **[R]**:

| Rule | Until Dec 2024 (Res. CMN 2.682/1999) | From Jan 2025 (Res. CMN 4.966/2021, Res. BCB 352/2023) |
|---|---|---|
| Write-off | H-rated operations written off after six months in H (art. 7). Minimum rating H at >180 days overdue (art. 4). BCB: "typically nine months after default" | Written off when recovery is no longer probable (4.966 art. 49). Minimum incurred-loss provision floors rise with months since default and reach 100% after 15 (portfolio C3–C5) to ~21 months (C1) (352 Anexo I) |
| Income accrual | Prohibited from **60 days** overdue (art. 9). Doc 3040 overdue values followed it (Carta Circular 3.869/2018 art. 6 §2) | Prohibited once the asset is a **problem asset** (art. 17), i.e. from >90 days or earlier by judgment (art. 3). Doc 3040 overdue values now include accrued contractual interest except on problem assets (IN BCB 414/2023; **[3040]** item f) |
| Problem asset | (dataset proxy) >90 days, or restructured and rated E–H | >90 days, or evidence the obligation won't be honoured, lender's judgment (art. 3); all of a counterparty's instruments move to stage 3 together (art. 37 §5) |

What that does to each measure:

| Measure | Consistent across Jan 2025? | Evidence |
|---|---|---|
| `vencido_acima_de_90_dias`, `carteira_inadimplencia` | **No.** Loans that used to be written off about nine months after default now stay on the books longer, so the stock rises with no change in borrower behaviour. The effect builds through 2025 rather than stepping in January | BCB estimates the regulatory change explains **~70%** (0.53 of 0.78 pp) of the 2025 rise in SFN 90-day delinquency to June 2025, similarly for PF and PJ (*Relatório de Política Monetária*, Sep 2025, box). In the data, PF `carteira_inadimplencia` rose +0.31 pp Dec-24→Jan-25 against +0.03 pp in the Dec-23→Jan-24 control **[D]** |
| `vencido_de_15_ate_90_dias` | **Closest to consistent.** Write-off happens long after 90 days under both regimes, so this bucket is untouched by write-off policy. Residual risk, **documented in the reporting rule** (§10.4): since January 2025, overdue values include accrued contractual interest until an asset is a problem asset, whereas before accrual stopped at 60 days. Balances 60–90 days overdue can therefore be slightly higher (**unquantified**) | Dec→Jan change **+0.026 pp** in 2025 vs **+0.010 pp** in the 2024 control **[D]** |
| `ativo_problematico` | **No.** Definition changed | Section 2.3; `docs/data-landscape.md` |
| `carteira_ativa` (denominator) | **Same identity, same scope rule, no visible level shift for PF.** But from 2025 it contains the non-written-off defaulted stock, so it is slightly inflated relative to 2024 | PF carteira Dec→Jan: +1.05% (2025) vs +0.99% (2024) **[D]**. Whether 4.966's amortised-cost measurement changed reported balances is **unknown**. It would need BCB confirmation or a same-institution comparison |

**Conclusion for the design.** The original plan's premise that the overdue bands are "consistent across
the whole series" holds for the *definitions* and fails for the >90 *stocks*. Only the 15–90 bucket
is defensible as a measure that runs through January 2025 with no adjustment. It has its own
earlier break, in March 2014 (section 10). Any >90 series across
the break has to be labelled and either stop at December 2024 or carry BCB's counterfactual as a
caveat.

---

## 6. The cross-tab test, in detail

Question: is occupation × income a joint distribution, or are they published as separate
marginal slices?

| Check | Result **[D]** |
|---|---|
| Grain unique across the 10 dimensions | yes, all 169 months |
| Any row whose occupation or income is a total/"todos"/placeholder | none. The only non-substantive values are the real categories `Outros` and `Indisponível` |
| PF cells populated, 8 occupations × 9 income bands | **72/72 in every month from 2016-01 to 2026-07** (127 months); 68–70 of 72 from 2012-07 to 2015-12, with MEI cells empty (`scripts/recon/panel.py`) |
| Sum of cells = sum of marginals | holds trivially: marginals are built by summing cells, since there are no published marginals |

**Answer: cross-tabbable.** Two caveats about content, not structure:

- The cells are **exposure-weighted** (R$), not borrower-weighted. A borrower with loans at two
  lenders can appear in two income bands (section 2.1, `porte`).
- The occupation × income matrix is very unbalanced. In 2026-07: Empresário × Acima de 20 SM
  R$433.6 bn; Empregado de entidades sem fins lucrativos × Sem rendimento R$0.02 bn. Many cells are
  too thin for monthly rates without pooling.

---

## 7. Open questions, and what it would take to close each

| # | Unknown | How to find out |
|---|---|---|
| U1 | Where SCR.data puts doc 3040 maturity codes 205 (1–14 days overdue) and 199 (open-ended). Both are inside "carteira" (codes 110–290) **[M2][3040]**, but no published column holds them and the identities are exact | Ask BCB |
| U2 | Whether `numero_de_operacoes = -1` means ≤15 operations, and whether the official suppression/aggregation of sparse cells (§10.4) also moves balances into other categories ("Outros", "Indisponível", "Outros créditos") | Partly answered: BCB confirms sparse cells are hidden or aggregated. The marker's meaning and any reallocation: ask BCB |
| U3 | Which IRPF *natureza da ocupação* categories map to each SCR group, which filing year each data-base uses, and how non-filers are classified | Partly answered (§10.4: CPF registry field tied to a filing year; 24 IRPF categories). Mapping and process: ask BCB |
| U4 | Whether SCR.data uses each lender's reported `PorteCli` as is, or recomputes the band from reported income | Partly answered. Lenders assign `PorteCli` from their most current information **[3040]**. BCB states there is no client-level consolidation (LAI, §10.4). Bands move against the minimum wage in force at the data-base, including at the mid-year resets (§10.5). Ask BCB which of the two options applies |
| U5 | Cause of the income shifts | **Largely located** (§10.5). 2018-11: new "Indisponível" code. 2019-03, 2020-08, 2021-09, 2026-05: bank reporting changes, mostly in real-estate financing. 2025-01: cooperatives in RS/PR/MT, reversed next month. Januaries: minimum wage. 2025-07: permanent step in the size field, in V2 and V1, PF and PJ, while occupation doesn't move. Most likely a production change at BCB (§10.6, inference). **What changed in band assignment is undocumented.** Ask BCB, and whether the lender events will be revised |
| ~~U6~~ | ~~Exact months when `submodalidade`, `segmento`, `indexador` categories changed~~ | **Resolved** on the full history (§2.1, §10) |
| U7 | Why V2 reports 1–2% more PF portfolio than V1 | Not needed for the design, since V1 is dropped. Ask BCB if it ever matters |
| ~~U8~~ | ~~Whether the 2025 rules changed how reported balances are valued~~ | **Answered** (§10.4): from Jan/2025 overdue values include accrued contractual interest except on problem assets (IN BCB 414/2023). Performing values remain the present value of instalments |
| ~~U9~~ | ~~Effect of the June-2016 threshold change~~ | **Resolved**, §5.1: +33.5% PF operations, +1.8% PF balance, +20% in the "Até 1 SM" portfolio. Aggregate rate effect small and not separable |
| U10 | Why occupation is reclassified in January (2016, 2017, 2018, 2021, 2023), and what happened in January 2017 | Largely narrowed (§10.4). BCB receives occupation daily from Receita with a tax-return year (RIPD 2020). Receita removed "Não informado" (14% of filers in 2013) from calendar year 2014, which fits the 2016 and 2017 drops in "Outros" if unreported occupations were mapped there. Still needed from BCB: the mapping, which tax-return year each January uses, and why the refresh is annual |
| U11 | Cause of the March-2014 fall in the 15–90-day rate (Empréstimos 2.95% → 1.99%) | Outside the v1 window. Ask BCB if the pre-2017 series is ever needed |
| U12 | Cause of the post-window income reclassifications (2025-07, 2026-05) | 2026-05 is a bank real-estate reporting change (§10.5). 2025-07 is tested in §10.6: a permanent step in the size field in both V2 and V1, for PF and for PJ at banks, with occupation unchanged and PF cell counts falling. Most likely a production change from data-base July 2025, which BCB's notes on V1 and CSV-only publication date to the same month. The exact rule change is undocumented. Ask BCB |
| U13 | Why SCR.data PF 90-day rate diverges from SGS 21084 by 0.2–0.3 pp in March–June 2026 | SGS values unrevised on 2026-09-15. The documented scope difference (cooperatives etc.) makes the gap larger, not smaller (§10.4). Ask BCB |

---

## 8. Files profiled for this document

Monthly CSVs extracted from the official yearly archives with CRC32 verification. SHA-256 recorded
in `data/raw/months/SHA256SUMS` (gitignored with the data):

| File | Rows | SHA-256 (first 16) |
|---|---|---|
| `scrdata_201306.csv` | 215,590 | `7ea88f11a09f9858` |
| `scrdata_201605.csv` | 213,681 | `62ed024ddad729a0` |
| `scrdata_201606.csv` | 216,704 | `8c0449aefcf356e9` |
| `scrdata_202312.csv` | 312,370 | `c0e5e5aa124b94c1` |
| `scrdata_202401.csv` | 311,692 | `0d89b35131ff26c1` |
| `scrdata_202406.csv` | 306,976 | `535c0d796a28692d` |
| `scrdata_202411.csv` | 308,866 | `3f9e3d4649cf9918` |
| `scrdata_202412.csv` | 310,432 | `546c762047c506ed` |
| `scrdata_202501.csv` | 313,638 | `b83581d2cdd44cd5` |
| `scrdata_202502.csv` | 313,564 | `11e82dc62a240be7` |
| `scrdata_202506.csv` | 322,852 | `0e47ba8a070064bf` |
| `scrdata_202512.csv` | 310,452 | `e19b509e76890df8` |
| `scrdata_202607.csv` | 310,193 | `ec7726666d73f369` |
| `planilha_201306.csv` | 499,766 | `dd8edb90f18074d0` |
| `planilha_202412.csv` | 995,670 | `d2b4b1f5c1f7f8a9` |
| `planilha_202506.csv` | 1,025,243 | `ae690ae295b58a8f` |
| `planilha_202507.csv` | 891,135 | `03ba96a5e7fbc32d` |
| `planilha_202607.csv` | 911,689 | `b6386ad0b245e8a6` |

Plus the header line and first data row of all 344 monthly files, read by range request.

**Full V2 history** (section 10): all 15 yearly archives, every member CRC-checked, pinned in
`data/raw/zips/MANIFEST.tsv` **[D]**:

| Archive | Months | Last-Modified (publication vintage) | SHA-256 (first 16) |
|---|---|---|---|
| `scrdata_2012.zip` | 2012-07 … 2012-12 | 16 Apr 2026 | `a8ab66779c36d178` |
| `scrdata_2013.zip` | 12 | 16 Apr 2026 | `4059e19f25e99e11` |
| `scrdata_2014.zip` | 12 | 16 Apr 2026 | `2b34af234b9d9284` |
| `scrdata_2015.zip` | 12 | 15 Apr 2026 | `f5d5c769f76cba0d` |
| `scrdata_2016.zip` | 12 | 14 Apr 2026 | `3c75ab4fa0a59e9a` |
| `scrdata_2017.zip` | 12 | 10 Apr 2026 | `d01dcf132d4da541` |
| `scrdata_2018.zip` | 12 | 9 Apr 2026 | `3721e879c88c250a` |
| `scrdata_2019.zip` | 12 | 8 Apr 2026 | `ebfaeff4b0a6e88e` |
| `scrdata_2020.zip` | 12 | 7 Apr 2026 | `2b1b4162c4961052` |
| `scrdata_2021.zip` | 12 | 6 Apr 2026 | `2c15f07b8b2dd772` |
| `scrdata_2022.zip` | 12 | 2 Apr 2026 | `530dbca38199feb0` |
| `scrdata_2023.zip` | 12 | 27 Mar 2026 | `015cffedbb80575b` |
| `scrdata_2024.zip` | 12 | 2 Sep 2026 | `00b773506fa5cecb` |
| `scrdata_2025.zip` | 12 | 5 Sep 2026 | `b6c4e3a02bf3698e` |
| `scrdata_2026.zip` | 2026-01 … 2026-07 | 12 Sep 2026 | `b43d659873815e09` |

## 9. Reproducing this document

```bash
# index every archive and read every header (no bulk download)
uv run python scripts/recon/remote_zip_index.py
uv run python scripts/recon/header_scan.py
# fetch individual months (4 MB range requests, CRC-verified)
uv run python scripts/recon/fetch_member.py data/raw/months scrdata_202607 scrdata_202412 scrdata_202501
# load typed into DuckDB and profile
uv run python scripts/recon/load_months.py data/recon.duckdb data/raw/months/*.csv
uv run python scripts/recon/structure_checks.py data/recon.duckdb profile scrdata_202607
uv run python scripts/recon/structure_checks.py data/recon.duckdb recon planilha_202607 scrdata_202607
uv run python scripts/recon/category_presence.py
uv run python scripts/recon/jan2025_break.py
uv run python scripts/recon/jan2025_control.py
uv run python scripts/recon/v1_structure.py
uv run python scripts/recon/threshold_2016.py
uv run python scripts/recon/crosstab_cells.py
uv run python scripts/recon/sgs.py
```

Full history (section 10): about 15 minutes to download, 10 to convert, seconds to profile.

```bash
uv run python scripts/recon/fetch_years.py data/raw/zips scrdata 2012 2026 --jobs 3
uv run python scripts/recon/to_parquet.py data/parquet/scrdata data/raw/zips/scrdata_*.zip
uv run python scripts/recon/panel.py data/parquet/scrdata data/recon/panel
uv run python scripts/recon/breaks_context.py data/parquet/scrdata
```

Run `uv sync` first. The scripts run in the project environment, which pins Python 3.13 and
`dbt-core` 1.11 (1.12 pulls in a parser whose build downloads a binary at install time).

---

## 10. Full-history profile: all 169 V2 months

Sections 1–9 were built from 13 sampled months. This section profiles **every** V2 month, 2012-07 to
2026-07 (43,062,885 rows), so that every change inside the analysis window is dated rather than
guessed. Outputs: `data/recon/panel/` (`month_summary.csv`, `category_presence.csv`,
`pf_series.csv`, `steps.csv`) from `scripts/recon/panel.py`, and the context tables from
`scripts/recon/breaks_context.py`. A candidate break is a month-on-month move more than six robust
standard deviations from that series' own typical move, and material in size (≥0.25 pp for a share,
≥0.15 pp for a rate on ≥R$10 bn). A flag starts an inspection; it is not a finding.

### 10.1 Structure: clean throughout

| Check | Result **[D]** |
|---|---|
| Months present | 169, no gaps |
| Grain unique (10 dimensions) | every month |
| Null or empty value in any column | none, any month |
| Unparseable measure; negative measure | none; none |
| `numero_de_operacoes` values other than positive or `-1` | none |
| PF occupation × income cells | 68–70 of 72 until 2015-12; **72 from 2016-01** |
| `carteira_ativa` = a-vencer + vencida | 242–1,069 rows off per month (R$6–72 M) until 2016-04; ≤97 rows 2016-05 to 2016-12; **exact from 2017-01** except 1 row in 2024-12 |
| `carteira_inadimplencia` < `vencido_acima_de_90_dias` (impossible by definition) | 1–116 rows per month until 2016-10; **none from 2016-11** |
| Scope: PF portfolio growth vs SGS 20541 differs by >1 pp | **only 2016-06** in 168 month-on-month changes |
| PF 90-day rate vs SGS 21084 | median +0.02 pp, range −0.10 to +0.33 pp. >0.2 pp only in 2016-07 (0.21) and 2026-03 to 2026-06 (0.23–0.33). Within 0.2 pp in every month 2017–2024 |

Data quality before 2017 is visibly weaker (identity failures, impossible rows, missing cells) but
small in R$. From 2017 the files are internally consistent.

### 10.2 Break register

**Occupation** (`scripts/recon/breaks_context.py`, "Occupation, Dec → Jan" and "'Outros' moves ≥0.5 pp"):

| Month | Share shift (pp of PF portfolio) | 90-day rates | Reading |
|---|---|---|---|
| 2016-01 | Outros −7.76 (45.17 → 37.41%); Servidor +2.43, Aposentado +3.26, Empregado privado +2.35; **MEI appears** (0 → 0.38%) | Named occupations −0.30 to −1.46 pp; Outros +1.96 pp; PF total +0.05 | Reclassification out of "Outros". Before the window |
| **2017-01** | **Outros −11.27 (37.74 → 26.47%)**; Empregado privado +3.58, Empresário +2.36, Autônomo +2.16, Aposentado +1.99, Servidor +0.82, MEI +0.30 | **Named occupations +0.41 to +2.24 pp** (Autônomo 2.89 → 5.13%, Empresário 2.84 → 4.09%, Empregado privado 2.27 → 3.47%, Aposentado 2.41 → 3.38%); Outros −1.10 pp; **PF total +0.04** | **Largest classification break in the series.** Borrowers with higher delinquency moved out of "Outros" into named occupations. Occupation-level rates are not comparable across this month |
| 2018-01 | Outros −2.33 (27.06 → 24.73%); Aposentado +2.06, MEI +0.39, Servidor −0.66 | Named occupations within ±0.2 pp of the PF total's +0.19 pp | Mix shift, rates not visibly affected |
| 2021-01 | Outros −2.14 (25.91 → 23.76%); Empregado privado +0.85, Aposentado +0.70 | Within −0.11 to +0.16 pp of the PF total's +0.06 pp | Mix shift, rates not visibly affected |
| 2023-01 | Outros −0.58; Aposentado +0.25 | In line with total | Minor |
| other months | Outros ≥0.5 pp only in 2016-06 (+0.63, scope change), 2024-09 (+0.51), 2025-05 (+0.63) | — | Minor |

Every material reclassification happens in **January**. Whether that is an annual refresh of the
tax-registry attribute is unknown (U10).

**Income band:**

| Month | Shift (pp of PF portfolio) | Reading |
|---|---|---|
| Every January 2017–2026 | In 8 of 10 Januaries "Acima de 20 SM" loses ≥0.5 pp (range −0.16 to −0.84; −2.77 in 2025) and "Até 1 SM" gains ≥0.4 pp (up to +1.80); "1–2 SM" gains up to +1.85 (2022). Named-band 90-day rates mostly move within ±0.2 pp of the PF total (exception: "Até 1 SM" −0.81 pp in Jan-2017) | Consistent with borrowers crossing band thresholds when the minimum wage is raised each January (R$880 in 2016, R$1,412 in 2024, R$1,518 in 2025, R$1,621 in 2026 **[SGS 1619]**). Tested in §10.5: the two mid-year minimum-wage resets (2020-02, 2023-05) show the same pattern at a smaller scale, and January shift size tracks the size of the reset. **Income bands are only comparable within a calendar year** |
| 2018-11 | "Indisponível" 0.00 → 0.99%; "Sem rendimento" 1.31 → 0.29%; PJ `Indisponível` first appears | Missing income recoded from "Sem rendimento" to "Indisponível" |
| 2019-03 | "Indisponível" +2.69 (1.23 → 3.92%); "Acima de 20 SM" −1.73, "5–10" −1.08, "10–20" −0.87. Named-band rates ±0.1 pp | Income of higher-band borrowers reclassified as unavailable |
| 2020-08 | "Indisponível" −0.52 | Minor |
| 2021-09 | "Indisponível" −1.68 (2.77 → 1.09%), into "2–3", "3–5", "Acima de 20" | Reverse recoding |
| 2025-01 | "Sem rendimento" +2.72, reverted in 2025-02 | Section 2.1 |
| 2025-07 | "Acima de 20 SM" **+3.53** (18.97 → 22.50%); "1–2" −1.98, "Até 1" −1.69, "2–3" −0.94 | Post-window reclassification. Same month V1's structure changed (section 3) |
| 2026-05 | "Até 1 SM" −2.52, "1–2" −1.82, "5–10" +2.17, "Indisponível" +0.84 | Post-window reclassification |

**Measures and products:**

| Month | What | Reading |
|---|---|---|
| **2014-03** | PF 15–90-day rate 1.33 → 0.99% (−0.34 pp), driven by Empréstimos 2.95 → 1.99%. No matching move in 90-day | **15–90-day series is not consistent before 2014-03.** Cause unknown (U11). Before the window |
| 2017-05 → 2017-06 | `Cartão de crédito - não migrado` appears (0.15 → 0.88% of PF) while `Crédito rotativo vinculado a cartão de crédito` falls 2.44 → 1.22%. The card group total holds at 11.05–11.45%. Card 15–90 falls 3.18 → 2.22% between April and August 2017 | Revolving balances moved between card sub-modalities. A product group summing **all** card sub-modalities is continuous. Doc 3040 cites Res. CMN 4.549/2017 on financing revolving balances; the link is plausible, not verified |
| Every May | Rural 15–90-day rate rises April → May in every year: +0.02 to +0.18 pp in 2013–2023, **+0.56 (2024), +0.62 (2025), +0.72 (2026)**. The May level in 2024–26 is roughly 5–8× the 2021–22 May level | Seasonal pattern, with real rural stress on top from 2024 (not only the 2024 floods, since it repeats) |
| — | Rural credit is **52.4% of "Acima de 20 SM"** PF balances and **42.3% of "Autônomo"**, against 16.0% of all PF (2024) | High-income and self-employed rates are largely rural-credit rates. Product decomposition is essential for these groups |
| 2021-05 → 2021-06 | Real-estate 15–90 0.13 → 0.30 → 0.11% | One-month anomaly |
| 2020-03 | Real-estate 90-day +0.70 pp | Pandemic onset |

**Categories** (`category_presence.csv`): segments 6 → 7 (2018-01) → 8 (2019-05); `TCR/TRFC` index from
2019-08; PJ income `Indisponível` from 2018-11; sub-modality renames 2014-02, 2016-09, 2017-05,
2017-07 (section 2.1). `modalidade` has the same 13 values in every month.

### 10.3 What this changes

1. **Occupation analysis starts 2017-01**, not 2016-06. January 2017 changes the level of every
   named occupation's rate. January 2018 and January 2021 are flagged as classification events in
   any mix decomposition that spans them.
2. **Income bands are compared within calendar years only.** Every January moves band membership
   mechanically, and the 2019-03 recoding shifts the top bands. A calendar-year window contains no
   January step. 2019 is taken as March–December to stay after the recoding.
3. **Time decompositions use occupation × product cells**, not income, and run over episodes that
   start in a January after a reclassification: 2018-01 → 2020-12, 2021-01 → 2022-12,
   2023-01 → 2024-12.
4. **Post-2025 income cuts are not usable** without handling 2025-07 and 2026-05. The present-day
   read is by occupation.
5. The SGS reconciliation test can use a **0.2 pp tolerance for 2017–2024**.

`docs/analysis-design.md` and `docs/v1-decision.md` are amended accordingly.

### 10.4 What the public documentation already explains

Checked on 2026-09-15, before asking BCB anything. Sources:
- BCB's doc 3040 layout workbook `SCR3040_Leiaute.xls`, sheet `HistoricoAtualizacoes` (last saved 6 May 2026). Dates below are converted from Excel serials; "from data-base" is quoted from the log.
- The current *Instruções de Preenchimento do Documento 3040* **[3040]**.
- Carta Circular 3.869/2018.
- SERPRO's bCadastros documentation of the CPF registry.
- Receita Federal's *Natureza de Ocupação* table (IRPF statistics by occupation).
- REF May 2026, annex *Conceitos e Metodologias*, and *Relatório de Cidadania Financeira 2021*, glossary.
- BCB's methodology note for credit statistics (*Nota para a Imprensa*, `notaempr.pdf`).
- BCB working paper TD 338; doc 3026 filling instructions; Voto 159/2024–BCB.
- Busca LAI (CGU, `buscalai.cgu.gov.br`): 63 past access-to-information requests mentioning
  "SCR.data", 62 to BCB. Answers read in full where they bear on methodology.

| Observation in the data | Documented cause | Status |
|---|---|---|
| 2014-02 split of `Cheque especial e conta garantida` and of the working-capital sub-modalities | Layout change of 13/11/2013 (Carta Circular 3.617/2013): modality 0201 replaced by 0213 "cheque especial" and 0214 "conta garantida"; 0205/0206 replaced by 0215/0216. The same change renamed the field "Faturamento anual PJ" to **"Faturamento anual PJ ou Renda mensal PF"** | Explained. It also means PF income only became a reported 3040 field around 2014, consistent with the unstable income bands of 2012–2014. The log doesn't state the effective data-base; the data shows 2014-02 |
| 2016-09 `Outros direitos creditórios descontados` | Carta-Circular 3.773/2016, from data-base Sep/2016 | Explained |
| 2017-04 → 2017-07 card and rural sub-modality changes | Carta-Circular 3.806/2017: special characteristic 18 (financing of revolving card balances, Res. 4.549) from Apr/2017; sub-modality 0217 from May/2017; modality 08 renamed from "Financiamentos rurais e agroindustriais" to "Financiamentos rurais", with 0440 and 0804 added, from Jul/2017. Carta-Circular 3.817/2017: 0218 "cartão de crédito - não migrado" from May/2017 | Explained, including the data label "(ex-financiamentos rurais e agroindustriais)" |
| Problem-asset flag | Special characteristic 19 "Ativo problemático" exists in doc 3040 from data-base Dec/2017 (Carta-Circular 3.819/2017). SCR.data uses it only from Jan/2025 **[M2]** | Documented |
| Payment-institution segment appears for PF in 2018-01 | Carta Circular 3.869/2018 (consolidating Circular 3.870/2017) requires Instituições de Pagamento to report doc 3040 | Consistent; the exact start of the obligation isn't verified |
| **2018-11 income recoding** ("Indisponível" 0.00 → 0.99%; PJ `Indisponível` first appears) | Carta-Circular 3.871/2018 added domain **"0 - Indisponível" to Anexo 24 (PJ size) and Anexo 25 (PF income band) from data-base Nov/2018**. Before that, lenders had no "unavailable" code | **Explained** |
| 2019-05 | Carta Circular 3.869/2018 art. 4: from data-base May/2019, undisbursed contracted credit and non-cancellable commitments count towards a client's total for the reporting threshold | Documented. No visible effect (PF growth tracks SGS 20541 that month) |
| **2025-01 overdue amounts** | IN BCB 414/2023 changed the maturity-value description from Jan/2025. Overdue codes 205–290 are now present value **plus accrued contractual interest**, excluding unreceived revenue on problem assets ("stop accrual em ativos problemáticos") **[3040 item f]**. Before: present value plus charges, observing Res. 2.682 art. 9, i.e. no accrual from 60 days (Carta Circular 3.869/2018 art. 6 §2) | **Explained.** Balances 60–90 days overdue can now include accrued interest. Note: the cash-flow section of the same instructions still says maturity buckets exclude revenue after 60 days, which is inconsistent with item f |
| **Occupation source and January refreshes** | The CPF registry holds `codNatOcup` together with `anoExerc`, "Exercício a que se referem os códigos natureza da ocupação e código da ocupação principal" (SERPRO). The income-tax return has 24 natureza categories, including "Microempreendedor Individual - MEI" and "Natureza da ocupação não especificada anteriormente". There were **31.6 million filers** for calendar year 2020 (Receita Federal) | **Mechanism documented, BCB's process not.** Occupation is a tax-return attribute tied to a filing year, which is consistent with annual January updates. People who don't file have no declared occupation, which plausibly feeds "Outros" (not confirmed). Nothing explains the size of January 2017 |
| **BCB's Receita feed** | BCB, *Relatório de Impacto à Proteção de Dados Pessoais* (Sep 2020), §3.3: under an agreement with Receita Federal, BCB receives individuals' registry data, including "código e descrição da natureza da ocupação principal" and "exercício a que se referem os códigos". About 254 million records; "recebidos diariamente entre 30 e 50 mil registros", rising to "alguns milhões por dia" in the IRPF filing season | **Officially documented.** The source updates continuously, yet SCR.data occupation shifts only in January (§10.2), so the annual step is in BCB's SCR.data processing. That process is not documented |
| **Lead on January 2016 and 2017: Receita removed "Não informado"** | Receita's IRPF statistics by occupation (`scripts/recon/receita_natocup.py`): **"Não informado" grew from 0.52 million filers (calendar year 2008) to 3.72 million (2013, 14% of filers), and it and all "Adaptação: …" codes are absent from 2014 onward.** Named categories jump 2013 → 2014 (Empregado de empresa privada 5.82 → 7.86 million; Aposentado 2.62 → 3.44 million; MEI 64 → 304 thousand) | **Strong lead, not confirmed.** If BCB mapped an unreported occupation to "Outros", adopting the returns filed after the removal would move borrowers from "Outros" into named occupations, as in 2016-01 (−7.8 pp) and 2017-01 (−11.3 pp). The lag between tax year and SCR.data January, and the mapping, are not documented. The metadata PDF for Receita's table only defines columns. A secondary site's claim that a MEI code was added around 2017 is contradicted by Receita's table (MEI exists from 2008) |
| Income band assignment | Lenders classify `PorteCli` themselves "a partir da informação mais atual disponível", presumed or estimated income allowed; income is updated "sempre que houver nova informação" **[3040]** | Partly explained. January shifts are consistent with lenders reclassifying at the new minimum wage. Whether SCR.data uses `PorteCli` as reported or recomputes it isn't stated |
| One income band per borrower | REF May 2026 annex and RCF 2021 glossary, "Renda mensal": where lenders report different PF bands, BCB takes the **mode**, breaking ties by the band with the larger aggregate active portfolio, then the highest reported income within that band. This is stated for BCB's individual income-commitment metric | Documented for BCB analyses. Whether SCR.data applies the same single-band rule or keeps each lender's band is **not stated** |
| SCR.data vs SGS 21084 scope | The credit-statistics note (footnote 2) says SGS delinquency rates, from doc 3050, exclude credit cooperatives, development agencies and microcredit companies. **Tested** (`scripts/recon/sgs_scope.py`): excluding cooperatives, or cooperatives plus Desenvolvimento/Fomento and Outros, **widens** the gap (2017–2024 median +0.12 pp instead of +0.02 pp; 2026 maximum +0.39–0.40 pp instead of +0.33 pp) | Documented difference, **but it does not explain the gap** |
| Doc 3026 as a client-data source | Annual (December data-base) report limited to conglomerates with operations of at least R$5 million | Ruled out as the source of PF occupation or income |
| Voto 159/2024–BCB | Amends Circular 3.870/2017 on how often SCR information is compiled and on events that change a debt balance | Unrelated to the breaks |
| **No client-level consolidation; sparse cells hidden or aggregated** | BCB answer to LAI 18810.021683/2023-64 (appeal answered 02/01/2024 by the head of Desig, substitute; `buscalai.cgu.gov.br/busca/6633034`). SCR.data results from processing "cerca de 1 bilhão de operações reportadas mensalmente". BCB built "rotinas adicionais de pré-processamento para a ocultação e agregação de operações de modo a prevenir uma eventual quebra indireta do sigilo bancário dos tomadores, enquadrados em recortes esparsos de atividade econômica, unidade da federação e porte/rendimento". Client-level (CPF/CNPJ) consolidation "não existe atualmente no SCR.Data ou em qualquer outra publicação do Banco Central" | **Officially documented.** (a) Sparse cells are suppressed or aggregated, which is consistent with the `-1` sentinel and matters for thin v1 cells. Whether values are *moved* into other categories is not stated. (b) No client consolidation means SCR.data almost certainly does not apply the REF's single-band-per-borrower rule (inference from the official statement) |
| **2025 months withdrawn and revised** | BCB answers to LAI 18810.007763/2025-79 (22/04/2025; `busca/8635493`): "Os dados de 2025 foram retirados da página para revisão interna e deverão ser divulgados posteriormente". And to LAI 18810.008534/2025-71 (05/05/2025; `busca/8683869`): the Jan/Feb-2025 data "estão em processo de revisão devido ao início de vigência da ResCMN 4.966" | **Officially documented.** The 2025 months in today's files are a revised production, and SCR.data vintages differ |
| **No document found for:** January-2017 occupation break; income shifts 2019-03, 2020-08, 2021-09, 2025-01, 2025-07, 2026-05 (no Anexo 25 change on those dates; located by lender type and product in §10.5); 2014-03 15–90 drop; `TCR/TRFC` from 2019-08; the `-1` sentinel; where SCR.data puts maturity codes 199 (open-ended) and 205 (1–14 days overdue); the 2026 SCR–SGS gap (SGS values unchanged on 2026-09-15); whether the REF counterfactual series are published | — | Open questions for BCB (section 7) |

### 10.5 Where the income-band shifts come from

**Method.** Each shift in a band's share of the PF portfolio is split into the contribution of each
lender segment, modality and UF (`scripts/recon/income_shift_drivers.py`). A shift concentrated in
one lender type and one product points to a reporting change by those lenders. A broad shift points
to a common cause **[D]**.

| Month | Shift (pp of PF portfolio) | Where it comes from | Reading |
|---|---|---|---|
| 2018-11 | "Indisponível" +0.99 | Banks +0.97; loans +0.47, financing +0.33, other credit +0.14; no UF above +0.22 | New "Indisponível" code (Carta-Circular 3.871/2018, §10.4) |
| 2019-03 | "Indisponível" +2.69; "Acima de 20 SM" −1.73 | Banks +2.50 (finance companies +0.13, cooperatives +0.05). Loans +1.26 (R$10.8 → 34.4 bn) and **real-estate financing +1.09 (R$0.4 → 20.7 bn)**. The top-band fall is wider: banks −1.43, cooperatives −0.25; rural −0.77 | Reporting change concentrated in banks. The source of the top-band fall is not isolated |
| 2020-08 | "Indisponível" −0.52 | Banks −0.51; "Financiamentos" R$9.5 → 4.7 bn | Bank reporting change |
| 2021-09 | "Indisponível" −1.68 | Banks −1.54; loans −0.78 (R$38.8 → 19.3 bn), **real-estate −0.53 (R$16.0 → 2.7 bn)** | Largely reverses 2019-03 (share back to 1.09% against 1.23% before) |
| 2025-01 | "Sem rendimento" +2.72 | **Cooperatives +2.00: R$0.5 → 82.0 bn, from 0.19% to 32.36% of cooperatives' PF book**; banks +0.73; rural +1.36; **RS +0.91, PR +0.58, MT +0.38** | One-month event concentrated in cooperatives in RS, PR and MT. Reversed in 2025-02 (cooperatives −2.00, banks −0.59). January 2025 is also when IN BCB 414/2023 took effect, and the 2025 months were withdrawn and revised (LAI, §10.4) |
| 2025-07 | "Acima de 20 SM" +3.52; "1–2 SM" −1.98 | **Broad.** The top band's share rises inside every segment shown: banks 18.66 → 22.12%, cooperatives 47.35 → 56.46%, finance companies 2.49 → 3.07%, development agencies 55.02 → 63.48%. Also inside rural (63.43 → 75.11%), loans, real-estate and other credit, and in SP, MG, GO and DF | Not one lender type, and no minimum-wage change in July 2025. Permanent, also in V1, and accompanied by a PJ size step at banks: most likely a change in SCR.data production (§10.6) |
| 2026-05 | "Até 1 SM" −2.52; "5–10 SM" +2.17 | Banks −2.54 / +2.15. **Real-estate financing is about 90% of both moves** ("Até 1 SM" R$131.7 → 28.3 bn; "5–10 SM" R$218.3 → 311.7 bn). Within payment institutions, finance companies and cooperatives the "Até 1 SM" share is flat | Bank reporting change in real-estate financing |
| 2024-01 (a typical January) | "Acima de 20 SM" −0.63; "Até 1 SM" +0.75 | **Broad.** "Até 1 SM" rises inside every segment shown: banks 8.01 → 8.77%, finance companies 16.47 → 17.42%, payment institutions 14.72 → 16.20%, cooperatives 4.08 → 4.24%. The top band falls inside banks, cooperatives and finance companies. Same direction in the top four modalities and UFs | Common cause: see the test below |

The diagnostic is the **within-segment share**. A lender event moves one segment's share and leaves
the others flat, as in 2025-01 and 2026-05. A common cause moves them all the same way, as in 2025-07
and the Januaries.

**Minimum-wage test** (`scripts/recon/minimum_wage_test.py`). The minimum wage changed every January,
and also in **2020-02 (+0.6%)** and **2023-05 (+1.4%)** **[SGS 1619]**. If bands respond to it,
those two months should move the January way:

| Change in band share (pp) | Acima de 20 SM | 10–20 SM | 1–2 SM | Até 1 SM |
|---|---|---|---|---|
| 2023-05 (minimum wage +1.4%) | −0.23 | −0.15 | +0.21 | +0.26 |
| 2020-02 (minimum wage +0.6%) | −0.06 | −0.14 | +0.13 | +0.13 |
| Neighbouring months, no change (2019-12, 2020-03, 2023-03, 2023-04, 2023-06, 2023-07) | +0.14, +0.18, +0.07, +0.06, −0.01, +0.18 | −0.09, −0.00, −0.08, +0.18, +0.10, +0.04 | +0.06, −0.01, −0.08, −0.03, +0.02, −0.15 | −0.22, +0.02, −0.20, −0.08, −0.18, −0.10 |
| 90th percentile of \|change\|, months without a reset or reporting event, 2017-02 to 2024-12 | 0.42 | 0.13 | 0.25 | 0.22 |

**Result.** Both mid-year resets move all four bands the January way: top bands down, bottom bands
up. None of the six neighbouring months does. Size alone is weaker evidence. The 10–20 SM move
passes the 90th percentile in both reset months, but so does 2023-04, a control month. "Acima de
20 SM" stays below its 90th percentile in both reset months. Across Januaries the size link is loose.
The smallest reset, 2018 (+1.8%), has the smallest moves: "Acima de 20 SM" −0.16 pp and "Até 1 SM"
−0.08 pp. The largest, 2022 (+10.2%), has the largest "1–2 SM" gain (+1.85 pp) but not the largest
top-band fall (2023: −0.84 pp) **[SGS 1619; `minimum_wage_test.py`]**.

**Reading.** PF bands behave as if measured against the minimum wage in force at each data-base,
and they shift in the month it changes, mid-year included. Whether lenders reclassify `PorteCli` or
BCB recomputes the band from reported income is still unknown (U4). This is consistent evidence from
two events, not proof.

**For v1.** The comparison windows already avoid these events: March–December 2019 starts after
2019-03; calendar 2022 and 2024 contain no reporting event; the post-2024 read is by occupation.
Reporting events cluster in **real-estate and rural credit**, which the product split in chart 4
isolates.

### 10.6 The July-2025 step

**Data tests.** From `scripts/recon/income_step_2025_07.py`, comparing 2025-06 with 2025-07 unless stated:

| Test | Result | Reading |
|---|---|---|
| New money? | PF balance R$4,241.7 → 4,272.4 bn (+0.7%); operations 830.4 → 844.5 million | Normal growth. Balances moved between bands |
| Persistent? | "Acima de 20 SM" 18.97 → 22.50%, then 21.1–22.5% every month to 2026-07. "1–2 SM" 17.13 → 15.15%, then 13.2–15.1% | **Permanent level change**, unlike the one-month 2025-01 event |
| Balances or operations? | Top band's share of operations 2.11 → 2.76%, while its balance per operation falls from R$45.8k to 41.2k. "1–2 SM" share of operations 32.12 → 30.05% | Many operations moved. Those entering the top band are smaller than those already there |
| How broad? | The top band's share rose by more than 1 pp in segment × modality × UF × occupation cells holding **56%** of PF balance, and fell in cells holding 0%. For comparison: ordinary months 2% rose / 8% fell (2025-06) and 2% / 1% (2024-05); January 2024 1% rose / 31% fell; 2026-05 bank event, "Até 1 SM" fell in 45% | The broadest band move tested, and all in one direction |
| Minimum-wage divisor? | Retirees' "1–2 SM" share falls 14.0 → 11.2%. A small divisor change would raise it, from retirees on exactly 1 SM crossing the edge. Every occupation's top band rises: Empresário 44.1 → 52.5%, Autônomo 40.3 → 46.9%, Servidor 8.7 → 12.1%, Aposentado 7.4 → 10.0% | **Rejected.** Too large and in the wrong direction for an edge effect |
| Which products? | Largest in rural and business-like credit: Custeio top band 66.6 → 79.2% and "Até 1 SM" 4.0 → 0.6%; Investimento 60.4 → 71.1%; housing outside SFH 50.5 → 57.7%. Payroll loans also move (3.6 → 5.3%). Smaller moves in SFH mortgages (6.2 → 7.2%), vehicles (6.5 → 7.2%) and non-migrated card (3.8 → 4.3%) | Not confined to products where income is poorly known |
| Risk of who moved | Top band 90-day rate 2.86% (Jun) → 3.49% (Jul) → 4.14% (Aug). "Até 1 SM" 6.49 → 7.10% | Borrowers with higher delinquency entered the top band. **Band-level rates are not comparable across this month** |
| Other dimensions | PF occupation shares move within ±0.1 pp. PJ size moves: "Grande" 52.33 → 50.77% of PJ; inside banks 51.15 → 48.99% and leasing companies 45.67 → 41.08%, while "Grande" moves less than 0.5 pp inside cooperatives (9.73 → 9.69%), finance companies (51.17 → 51.63%) and development agencies (85.06 → 85.49%) | Only the lender-reported size field moves; occupation, sourced from Receita, does not. For PJ the move is at banks |
| V1 files | Same step in V1: PF "Acima de 20 SM" 19.16 → 22.67%, "1–2 SM" 17.14 → 15.18%; PJ "Grande" 50.09 → 48.66%. V1's structure changes in the same month (§3) | The change is upstream of both publications |
| Cells | PF rows 194,161 → 180,953 ("Até 1 SM" 22,808 → 19,269); rows with `-1` operations 39,315 → 35,219. PJ rows 128,691 → 127,256 | PF cell structure changed in the same month |

**Documents checked (2026-09-15).**
- **IN BCB 627/2025** is the only doc 3040 change effective from data-base July 2025 (Art. 1). It adds special characteristics 40–42 (acquired precatórios, acquired rights in execution, syndicated operations), the EcoInvest regulatory-use code, and an auction number in additional information. It does not touch Anexos 24/25 or income. The layout log has no Anexo 24/25 change after 2018.
- **Methodology:** the V1 PDF (created 2025-06-03) and V2 PDF (created 2026-03-06) both say the published sizes "representam os portes definidos nos Anexos 24 e 25", and describe no change.
- **REF annex:** the "Renda mensal" definition is word-for-word the same in April 2025 and May 2026.
- **Dados Abertos metadata:** the V2 ZIP resource and the V1 notice ("disponíveis até a data-base junho/2025 e não serão mais atualizados") were both created on 2025-11-27. The V2 methodology resource was created on 2025-11-28.
- **BCB's SCR.data page:** the current source holds a commented-out note, "Para informações a partir de julho/2025, os dados foram disponibilizados apenas no formato CSV". The note is absent from the Wayback copies of the page content of 2025-04-28 and 2025-12-10, so it was added later.
- **Busca LAI:** none of the 63 requests mentioning "SCR.data" (most recent answered 2026-09-14) concerns income bands or July 2025.
- **Web searches:** no other rule or announcement found.

**Reading.** Several things change together at data-base July 2025, while occupation, sourced from Receita, does not:
- the lender-reported size field steps, for PF across every lender type and product, and for PJ at banks;
- PF cell counts fall in V2, and V1's structure changes;
- BCB's own notes place the end of V1 and the switch to CSV-only publication at this month.

The most likely explanation is **a change in how SCR.data is produced from data-base July 2025**. This is an inference, not documented. What changed in band assignment is also not documented. Two changes fit the aggregates and can't be told apart without borrower-level data:
- deriving the band from the reported amount ("Renda mensal PF") instead of the reported size code;
- assigning one band per borrower across lenders, as the REF annex does (BCB said in 2023 that SCR.data had no client consolidation).

A lender-side cause is unlikely. No rule required re-reporting, and banks and cooperatives moved together for PF but not for PJ. It stays an open question for BCB (U12).

**For v1.** v1's income cross-sections end in 2024 and are unaffected. Any income-band series or band-level rate that crosses July 2025 needs a break flag, and a level adjustment can't be estimated from the data alone.
