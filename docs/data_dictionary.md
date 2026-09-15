# SCR.data — data dictionary

*Phase 1 of the reconnaissance (`docs/research-prompt.md`). Written from files opened and profiled,
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
| **Trap — discovery** | The CKAN resources for the monthly data have **empty `url` fields**. The URL is a pattern written in the resource *description* **[D: CKAN API]**. `scripts/fetch_scr.py` assumes resources carry URLs, so as written it cannot find the data. The fetch script has to be rewritten before the build phase |
| V2 files | `https://www.bcb.gov.br/pda/desig/scrdata_{YYYY}.zip`, one ZIP per **year** holding one CSV per month (`scrdata_YYYYMM.csv`) **[D][M2]** |
| V1 files | `https://www.bcb.gov.br/pda/desig/planilha_{YYYY}.zip` holding `planilha_YYYYMM.csv` **[D]** |
| Coverage, V2 | **2012-07 to 2026-07**, 169 months, no gaps, no duplicates **[D]** — the V1 methodology says the series starts June 2012 **[M1]**; V2 has no June 2012 file |
| Coverage, V1 | **2012-01 to 2026-07**, 175 months, no gaps **[D]** — BCB's portal says V1 "is available up to data-base June/2025 and will not be updated". **Disagreement:** V1 files exist through July 2026, with changed structure from July 2025 (section 3) |
| Release lag | "updated on the last business day of the month… 30 days after the close of each period" **[M2]**. On 2026-09-14 the latest month is 2026-07 **[D]** |
| Revisions | The Last-Modified dates of the V2 ZIPs for 2012–2023 are 27 Mar–16 Apr 2026, and for 2024–2026 are 2–12 Sep 2026 **[D: HTTP headers]**. **History is re-published.** A file downloaded later may not match one downloaded now. The build must pin SHA-256 hashes and Last-Modified dates (`data/raw/zips/MANIFEST.tsv`, written by `scripts/recon/fetch_years.py`) and say which vintage it used |

### 1.2 Format

| Item | V2 (`scrdata`) | V1 (`planilha`) |
|---|---|---|
| Encoding | UTF-8 **with BOM** **[D]** | UTF-8 with BOM **[D]** |
| Delimiter | `;` | `;` |
| Quoting | every field double-quoted **[D]** | unquoted, except `"-"` placeholders **[D]** |
| **Trap — delimiter inside a value** | CNAE label `Comércio; reparação de veículos automotores e motocicletas` contains `;` inside quotes. A naive split on `;` corrupts every PJ commerce row **[D]** | same label, unquoted form not observed in the rows sampled |
| Decimals | comma, no thousands separator (`633904,03`) **[D]** — no measure value in any profiled month contains `.`, and every value parses **[D]** | same **[D]** |
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

**Trap — transport.** The host resets long transfers. Whole-year downloads at roughly 0.3 MB/s
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

## 2. V2 (`scrdata_YYYYMM.csv`) — column by column

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
| `cnae_ocupacao` | **Overloaded.** PF: *natureza da ocupação*. PJ: CNAE section **[M2]**. The V1 methodology says occupation comes from the Receita Federal registry and is the *main* occupation **[M1]**. The V2 methodology doesn't say. Doc 3040 has no occupation field **[3040]**, which is consistent with BCB attaching it from the tax registry | PF (8): Servidor ou empregado público; Empregado de entidades sem fins lucrativos; Empregado de empresa privada; Aposentado/pensionista; Autônomo; Empresário; MEI; Outros. PJ (22): 21 CNAE sections + `Não informados` **[D]** | **MEI**: 0% until 2015-12; 0.38% from 2016-01, 0.68% from 2017-01, 1.06% from 2018-01; 1.77% in 2026-07. **Outros** falls in January reclassifications: **2016 (−7.8 pp), 2017 (−11.3 pp), 2018 (−2.3 pp), 2021 (−2.1 pp), 2023 (−0.6 pp)** **[D, full history]** (§10) | (a) Filter on `cliente` before using this column. (b) **"Outros" is the largest PF occupation** and its share moves by 16 pp over the series, so it can't be treated as a behavioural segment. (c) Why a borrower is "Outros" is **unknown**. It might be missing registry data, a non-listed occupation, or non-filers of income tax. Finding out needs BCB or Receita documentation of the source code list. (d) A registry attribute can be stale relative to the borrower's current job |
| `porte` | **Overloaded.** PF: gross *individual* monthly income in federal minimum wages (SM). PJ: firm size **[M2][3040]** | PF (9): Sem rendimento; Até 1 SM; Mais de 1 a 2; 2 a 3; 3 a 5; 5 a 10; 10 a 20; Acima de 20 SM; Indisponível. PJ (5): Micro, Pequeno, Médio, Grande, Indisponível **[D]** | PJ `Indisponível` first appears **2018-11**. PF band shares shift every January (minimum-wage reset) and at recodings in 2018-11, 2019-03, 2021-09, 2025-01, 2025-07 and 2026-05 **[D, full history]** (§10) | (a) Doc 3040: income is reported **by each lender**, "from the most current information available", and **presumed or estimated income is allowed**. `Indisponível` is only permitted when reported income ≤ R$1 **[3040]**. The same person can therefore be in different bands at different lenders. (b) **Bands are relative to the minimum wage**, which rises each January: R$678 (2013), R$1,412 (2024), R$1,518 (2025), R$1,621 (2026) **[SGS 1619]**. Whether the band uses the SM of the reference month or of when income was captured is **unknown** (not stated in [M2] or [3040]; needs BCB confirmation). (c) **January-2025 anomaly** (below). (d) Data labels say `salários mínimos`; the methodology says `salários-mínimos`. Joining on labels from the PDF will fail |
| `modalidade` | Credit modality, Anexo 3 of the 3040 layout **[M2]** | 13 values **[D]** | Same set in every month profiled **[D]** | The data label is `Financiamentos rurais  (ex-financiamentos rurais e agroindustriais)`, with a **double space**. The methodology calls it `Financiamentos rurais e agroindustriais` |
| `submodalidade` | Sub-modality, Anexo 3 **[M2]** | 49 (2013-06); 55–56 (2023–2026) **[D]** | **Renamed or split** (dated on the full history: the overdraft and working-capital splits in **2014-02**; `Outros direitos creditórios descontados` **2016-09**; `Cartão de crédito - não migrado` and `Capital de giro com teto rotativo` **2017-05**; `Financiamentos agroindustriais` and `Industrialização` **2017-07**): `Cheque especial e conta garantida` → `Cheque especial` + `Conta Garantida`; `Capital de giro com prazo vencim. igual ou superior 30 d` / `…inferior a 30 d` → `…até 365 dias` / `…superior a 365 dias` / `…com teto rotativo`. New: `Cartão de crédito - não migrado`, `Financiamentos agroindustriais`, `Industrialização`, `Outros direitos creditórios descontados` **[D]** | **Leading/trailing whitespace in 5–8% of rows** (7,487–24,895 rows per month across all 169 months). Trim before grouping **[D]**. Any modality series below `modalidade` level needs a hand-built crosswalk |
| `origem` | Earmarked or not, Anexo 4 first level **[M2]** | Sem destinação específica; Com destinação específica **[D]** | — | — |
| `indexador` | Rate index, Anexo 5 first level **[M2]** | Prefixado, Pós-fixado, Flutuantes, Índices de preços, TCR/TRFC, Outros indexadores **[D]** | **TCR/TRFC first appears 2019-08 for PF, 2019-10 for PJ** (5 values before) **[D, full history]** | — |

**Unstable PF categories, share of PF portfolio (%)** **[D]** — `scripts/recon/cells.py`

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
from 8.51% to 9.28% **[D]** (`scripts/recon/control.py`).

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

**Reconciliation to the official series** — PF `carteira_inadimplencia / carteira_ativa` **[D]** vs
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

## 3. V1 (`planilha_YYYYMM.csv`) — and why it is not used

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

**It doesn't, in the sense the brief assumed.** There is no data-base month at which the schema
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
| `tcb`, `sr` | — (removed) | V2 has `segmento` instead, a different grouping |
| — | `segmento` (added) | |
| `ocupacao` + `cnae_secao` | `cnae_ocupacao` | merged; prefixes dropped |
| `cnae_subclasse` | — (removed) | V2 stops at CNAE section |
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
| Income accrual | Prohibited from **60 days** overdue (art. 9) | Prohibited once the asset is a **problem asset** (art. 17), i.e. from >90 days or earlier by judgment (art. 3) |
| Problem asset | (dataset proxy) >90 days, or restructured and rated E–H | >90 days, or evidence the obligation won't be honoured, lender's judgment (art. 3); all of a counterparty's instruments move to stage 3 together (art. 37 §5) |

What that does to each measure:

| Measure | Consistent across Jan 2025? | Evidence |
|---|---|---|
| `vencido_acima_de_90_dias`, `carteira_inadimplencia` | **No.** Loans that used to be written off about nine months after default now stay on the books longer, so the stock rises with no change in borrower behaviour. The effect builds through 2025 rather than stepping in January | BCB estimates the regulatory change explains **~70%** (0.53 of 0.78 pp) of the 2025 rise in SFN 90-day delinquency to June 2025, similarly for PF and PJ (*Relatório de Política Monetária*, Sep 2025, box). In the data, PF `carteira_inadimplencia` rose +0.31 pp Dec-24→Jan-25 against +0.03 pp in the Dec-23→Jan-24 control **[D]** |
| `vencido_de_15_ate_90_dias` | **Closest to consistent.** Write-off happens long after 90 days under both regimes, so this bucket is untouched by write-off policy. Residual risk: accrual now continues from 60 to 90 days where it used to stop, which could raise balances in the bucket slightly (**unquantified**) | Dec→Jan change **+0.026 pp** in 2025 vs **+0.010 pp** in the 2024 control **[D]** |
| `ativo_problematico` | **No.** Definition changed | Section 2.3; `docs/data-landscape.md` |
| `carteira_ativa` (denominator) | **Same identity, same scope rule, no visible level shift for PF.** But from 2025 it contains the non-written-off defaulted stock, so it is slightly inflated relative to 2024 | PF carteira Dec→Jan: +1.05% (2025) vs +0.99% (2024) **[D]**. Whether 4.966's amortised-cost measurement changed reported balances is **unknown**. It would need BCB confirmation or a same-institution comparison |

**Conclusion for the design.** The brief's premise that the overdue bands are "consistent across
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
| U1 | Where 1–14-day overdue amounts sit (inside `a_vencer_ate_90_dias` or excluded) | Ask `scr.data@bcb.gov.br`; or reconcile against the 3040 maturity-code mapping |
| U2 | Whether `numero_de_operacoes = -1` means ≤15 operations | Ask BCB; or test that `-1` never co-occurs with a V1 cell showing >15 for a matched cell |
| U3 | Source code list behind PF occupation, and what puts a borrower in "Outros" | BCB / Receita Federal documentation of *natureza da ocupação* |
| U4 | Which month's minimum wage the income band uses | Ask BCB |
| U5 | Cause of the January-2025 "Sem rendimento" spike, and of the income recodings | **Dates resolved** (§10): recoding into "Indisponível" in 2018-11, further shifts 2019-03, 2020-08, 2021-09; spike 2025-01 reverted 2025-02. **Cause unknown**: ask BCB |
| ~~U6~~ | ~~Exact months when `submodalidade`, `segmento`, `indexador` categories changed~~ | **Resolved** on the full history (§2.1, §10) |
| U7 | Why V2 reports 1–2% more PF portfolio than V1 | Not needed for the design, since V1 is dropped. Ask BCB if it ever matters |
| U8 | Whether 4.966 amortised-cost measurement moved reported balances | BCB confirmation |
| ~~U9~~ | ~~Effect of the June-2016 threshold change~~ | **Resolved**, §5.1: +33.5% PF operations, +1.8% PF balance, +20% in the "Até 1 SM" portfolio. Aggregate rate effect small and not separable |
| U10 | Why occupation is reclassified in January (2016, 2017, 2018, 2021, 2023), and what happened in January 2017 | Consistent with an annual refresh of the registry attribute, but that is inference. Ask BCB |
| U11 | Cause of the March-2014 fall in the 15–90-day rate (Empréstimos 2.95% → 1.99%) | Outside the v1 window. Ask BCB if the pre-2017 series is ever needed |
| U12 | Cause of the post-window income reclassifications (2025-07, 2026-05) | Ask BCB. 2025-07 is also when V1's structure changed |
| U13 | Why SCR.data PF 90-day rate diverges from SGS 21084 by 0.2–0.3 pp in March–June 2026 | Check whether SGS revises those months; ask BCB |

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
uv run --no-project python scripts/recon/remote_zip_index.py
uv run --no-project python scripts/recon/header_scan.py
# fetch individual months (4 MB range requests, CRC-verified)
uv run --no-project python scripts/recon/fetch_member.py data/raw/months scrdata_202607 scrdata_202412 scrdata_202501
# load typed into DuckDB and profile
uv run --no-project --with duckdb python scripts/recon/load.py data/recon.duckdb data/raw/months/*.csv
uv run --no-project --with duckdb python scripts/recon/checks.py data/recon.duckdb profile scrdata_202607
uv run --no-project --with duckdb python scripts/recon/checks.py data/recon.duckdb recon planilha_202607 scrdata_202607
uv run --no-project --with duckdb python scripts/recon/presence.py
uv run --no-project --with duckdb python scripts/recon/control.py
uv run --no-project --with duckdb python scripts/recon/v1_structure.py
uv run --no-project --with duckdb python scripts/recon/threshold_2016.py
uv run --no-project --with duckdb python scripts/recon/cells.py
uv run --no-project python scripts/recon/sgs.py
```

Full history (section 10): about 15 minutes to download, 10 to convert, seconds to profile.

```bash
uv run --no-project python scripts/recon/fetch_years.py data/raw/zips scrdata 2012 2026 --jobs 3
uv run --no-project --with duckdb python scripts/recon/to_parquet.py data/parquet/scrdata data/raw/zips/scrdata_*.zip
uv run --no-project --with duckdb python scripts/recon/panel.py data/parquet/scrdata data/recon/panel
uv run --no-project --with duckdb python scripts/recon/breaks_context.py data/parquet/scrdata
```

`uv sync` for the full project currently fails: `dbt-core` 1.12.4 depends on a pre-release parser
whose build step downloads a wheel from GitHub, and that download failed certificate verification
on this machine. The recon scripts avoid the project environment for that reason. Pinning
`dbt-core` is a build-phase task.

---

## 10. Full-history profile — all 169 V2 months

Sections 1–9 were built from 13 sampled months. This section profiles **every** V2 month, 2012-07 to
2026-07 (43,062,885 rows), so that every change inside the analysis window is dated rather than
guessed. Outputs: `data/recon/panel/` (`month_summary.csv`, `category_presence.csv`,
`pf_series.csv`, `steps.csv`) from `scripts/recon/panel.py`, and the context tables from
`scripts/recon/breaks_context.py`. A candidate break is a month-on-month move more than six robust
standard deviations from that series' own typical move, and material in size (≥0.25 pp for a share,
≥0.15 pp for a rate on ≥R$10 bn). A flag starts an inspection; it is not a finding.

### 10.1 Structure — clean throughout

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
| Every January 2017–2026 | In 8 of 10 Januaries "Acima de 20 SM" loses ≥0.5 pp (range −0.16 to −0.84; −2.77 in 2025) and "Até 1 SM" gains ≥0.4 pp (up to +1.80); "1–2 SM" gains up to +1.85 (2022). Named-band 90-day rates mostly move within ±0.2 pp of the PF total (exception: "Até 1 SM" −0.81 pp in Jan-2017) | Consistent with borrowers crossing band thresholds when the minimum wage is raised each January (R$880 in 2016, R$1,412 in 2024, R$1,518 in 2025, R$1,621 in 2026 **[SGS 1619]**). The cause is an inference. **Income bands are only comparable within a calendar year** |
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
