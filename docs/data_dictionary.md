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

## 0. The five things that change the design

1. **Occupation × income is a genuine cross-tab, not two marginal slices.** V2 has a unique grain
   of ten dimensions, no subtotal rows, and all 72 PF occupation × income cells populated in every
   2024–2026 month profiled (70 of 72 in June 2013) **[D]**. The cross-tab also crosses UF,
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
   0.13% to 2.86% of the PF portfolio for one month (0.27% in February) **[D]**. The bands are also
   measured in minimum wages, which are re-set every January. Section 2, `porte`.
5. **Occupation is dominated by a residual category that shrinks over time.** "Outros" was 41.5% of
   PF balances in June 2013 and 25–28% in 2024–2026. MEI was effectively absent in 2013 **[D]**.
   Some of any change in the occupation mix is a change in classification, not in borrowers.

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
| Revisions | The Last-Modified dates of the V2 ZIPs for 2012–2023 are 27 Mar–16 Apr 2026, and for 2024–2026 are 2–12 Sep 2026 **[D: HTTP headers]**. **History is re-published.** A file downloaded later may not match one downloaded now. The build must pin SHA-256 hashes (`data/raw/months/SHA256SUMS`) and say which vintage it used |

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

Rows per V2 month: 215,590 (2013-06) to 313,638 (2025-01) **[D]**. Extrapolating from the ten
months profiled, the full V2 history is roughly 45–50 million rows. That is an estimate, not a
count.

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
  from pt-BR decimals and dimension text trimmed. The Parquet size is **unknown** until measured,
  but the data is highly repetitive text, so it should be far below the 13.8 GB of raw CSV.
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
| `segmento` | Institution type, grouped from BCB's registry **[M2]** | Banco, Cooperativa, Financeira, Instituição de pagamento, Fintech, Desenvolvimento/Fomento, Arrendamento, Outros **[D]** | **6 values in 2013-06** (no Fintech, no Instituição de pagamento). 8 in every 2023–2026 month **[D]** | Label is `Instituição de pagamento` in the data and `Instituição de Pagamento` in the methodology. Segment membership changes as institutions change licence, so a segment series is not a fixed set of lenders. Instituições de pagamento held R$115.8 bn of PF credit in 2026-07 **[D]** |
| `cliente` | PF (individuals) / PJ (firms) **[M2]** | `PF`, `PJ` **[D]** | — | — |
| `cnae_ocupacao` | **Overloaded.** PF: *natureza da ocupação*. PJ: CNAE section **[M2]**. The V1 methodology says occupation comes from the Receita Federal registry and is the *main* occupation **[M1]**. The V2 methodology doesn't say. Doc 3040 has no occupation field **[3040]**, which is consistent with BCB attaching it from the tax registry | PF (8): Servidor ou empregado público; Empregado de entidades sem fins lucrativos; Empregado de empresa privada; Aposentado/pensionista; Autônomo; Empresário; MEI; Outros. PJ (22): 21 CNAE sections + `Não informados` **[D]** | **MEI**: 29 rows, R$0.00 bn in 2013-06; 1.49% of PF balances in 2023-12; 1.77% in 2026-07. **Outros**: 41.53% (2013-06) → 25.18% (2024-06) → 27.85% (2026-07) **[D]** | (a) Filter on `cliente` before using this column. (b) **"Outros" is the largest PF occupation** and its share moves by 16 pp over the series, so it can't be treated as a behavioural segment. (c) Why a borrower is "Outros" is **unknown**. It might be missing registry data, a non-listed occupation, or non-filers of income tax. Finding out needs BCB or Receita documentation of the source code list. (d) A registry attribute can be stale relative to the borrower's current job |
| `porte` | **Overloaded.** PF: gross *individual* monthly income in federal minimum wages (SM). PJ: firm size **[M2][3040]** | PF (9): Sem rendimento; Até 1 SM; Mais de 1 a 2; 2 a 3; 3 a 5; 5 a 10; 10 a 20; Acima de 20 SM; Indisponível. PJ (5): Micro, Pequeno, Médio, Grande, Indisponível **[D]** | PJ `Indisponível` absent in 2013-06 **[D]**. PF shares move sharply: see the table below | (a) Doc 3040: income is reported **by each lender**, "from the most current information available", and **presumed or estimated income is allowed**. `Indisponível` is only permitted when reported income ≤ R$1 **[3040]**. The same person can therefore be in different bands at different lenders. (b) **Bands are relative to the minimum wage**, which rises each January: R$678 (2013), R$1,412 (2024), R$1,518 (2025), R$1,621 (2026) **[SGS 1619]**. Whether the band uses the SM of the reference month or of when income was captured is **unknown** (not stated in [M2] or [3040]; needs BCB confirmation). (c) **January-2025 anomaly** (below). (d) Data labels say `salários mínimos`; the methodology says `salários-mínimos`. Joining on labels from the PDF will fail |
| `modalidade` | Credit modality, Anexo 3 of the 3040 layout **[M2]** | 13 values **[D]** | Same set in every month profiled **[D]** | The data label is `Financiamentos rurais  (ex-financiamentos rurais e agroindustriais)`, with a **double space**. The methodology calls it `Financiamentos rurais e agroindustriais` |
| `submodalidade` | Sub-modality, Anexo 3 **[M2]** | 49 (2013-06); 55–56 (2023–2026) **[D]** | **Renamed or split between 2013 and 2024** (exact month unknown): `Cheque especial e conta garantida` → `Cheque especial` + `Conta Garantida`; `Capital de giro com prazo vencim. igual ou superior 30 d` / `…inferior a 30 d` → `…até 365 dias` / `…superior a 365 dias` / `…com teto rotativo`. New: `Cartão de crédito - não migrado`, `Financiamentos agroindustriais`, `Industrialização`, `Outros direitos creditórios descontados` **[D]** | **Leading/trailing whitespace in ~7% of rows** (23,367 rows in 2026-07). Trim before grouping **[D]**. Any modality series below `modalidade` level needs a hand-built crosswalk |
| `origem` | Earmarked or not, Anexo 4 first level **[M2]** | Sem destinação específica; Com destinação específica **[D]** | — | — |
| `indexador` | Rate index, Anexo 5 first level **[M2]** | Prefixado, Pós-fixado, Flutuantes, Índices de preços, TCR/TRFC, Outros indexadores **[D]** | **TCR/TRFC absent in 2013-06** (5 values) **[D]** | — |

**PF income-band share of PF portfolio (%)** **[D]** — `scripts/recon/control.py`, `checks.py`

| Band | 2013-06 | 2023-12 | 2024-06 | 2024-12 | **2025-01** | 2025-02 | 2026-07 |
|---|---|---|---|---|---|---|---|
| Sem rendimento | 3.84 | 0.20 | 0.10 | 0.13 | **2.86** | 0.27 | 0.64 |
| Indisponível | 0.28 | 1.21 | 1.38 | 1.60 | 1.96 | — | 2.08 |
| Acima de 20 SM | 21.36 | 19.11 | 19.30 | 20.28 | **17.50** | — | 21.06 |
| Até 1 SM | 4.61 | 8.37 | 8.33 | 8.51 | 9.28 | — | 6.36 |

In January 2025, "Sem rendimento" went from R$5.4 bn to R$116.8 bn. That included R$56.1 bn of
rural credit, up from R$0.4 bn, and spread across every occupation (Autônomo R$0.4 → 23.8 bn,
Empresário R$0.8 → 28.8 bn) **[D]**. Most of it reverted a month later. This is a reporting event,
not borrower behaviour. **Any income-band time series has to handle January 2025 explicitly**, and
the drift in "Indisponível" (0.28% → 2.08%) means the known-income population is not constant.

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
| `carteira_ativa` | a-vencer + vencida. Portfolio defined as maturities of modalities 01–13 of the 3040 layout **[M2]** | exact in 2023–2026 except 1 row (R$3,088.53, 2024-12); **877 rows off by R$24.9 M in total in 2013-06** | (a) Where amounts **1–14 days overdue** sit is **unknown**. There is no column for them and the identity holds, so they're either inside `a_vencer_ate_90_dias` or excluded. Resolving it needs BCB confirmation (`scr.data@bcb.gov.br`). (b) **Scope threshold change**: operations above R$1,000 until May 2016, above R$200 from June 2016 **[M2]**. See section 5.1 |
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

The PF numerator and denominator are the ones BCB uses, within about 0.1 pp. PJ reconciles less
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
  `submodalidade`, PF `MEI`, PJ `Indisponível`), reporting (the January-2025 income event), scope
  (June 2016) and meaning (`ativo_problematico` from January 2025).

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
**Effect in the data: pending.** The 2016-05 and 2016-06 files were still being fetched when this
section was first committed. It is updated in a follow-up commit.

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
is defensible as a measure that runs through January 2025 with no adjustment. Any >90 series across
the break has to be labelled and either stop at December 2024 or carry BCB's counterfactual as a
caveat.

---

## 6. The cross-tab test, in detail

Question: is occupation × income a joint distribution, or are they published as separate
marginal slices?

| Check | Result **[D]** |
|---|---|
| Grain unique across the 10 dimensions | yes, every month |
| Any row whose occupation or income is a total/"todos"/placeholder | none. The only non-substantive values are the real categories `Outros` and `Indisponível` |
| PF cells populated, 8 occupations × 9 income bands | **72/72** in 2023-12, 2024-01, 2024-06, 2024-11, 2024-12, 2025-01, 2026-07; **70/72** in 2013-06 (MEI × two bands empty) |
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
| U5 | Cause of the January-2025 "Sem rendimento" spike, and whether it recurs | Profile every month of 2025 (the full V2 download); ask BCB |
| U6 | Exact months when `submodalidade`, `segmento`, `indexador` categories changed | Full V2 download; one query |
| U7 | Why V2 reports 1–2% more PF portfolio than V1 | Not needed for the design, since V1 is dropped. Ask BCB if it ever matters |
| U8 | Whether 4.966 amortised-cost measurement moved reported balances | BCB confirmation |
| U9 | Effect of the June-2016 threshold change on levels and rates | 2016-05/06 files (in progress) |

---

## 8. Files profiled for this document

Monthly CSVs extracted from the official yearly archives with CRC32 verification. SHA-256 recorded
in `data/raw/months/SHA256SUMS` (gitignored with the data):

| File | Rows | SHA-256 (first 16) |
|---|---|---|
| `scrdata_201306.csv` | 215,590 | `7ea88f11a09f9858` |
| `scrdata_202312.csv` | 312,370 | `c0e5e5aa124b94c1` |
| `scrdata_202401.csv` | 311,692 | `0d89b35131ff26c1` |
| `scrdata_202406.csv` | 306,976 | `535c0d796a28692d` |
| `scrdata_202411.csv` | 308,866 | `3f9e3d4649cf9918` |
| `scrdata_202412.csv` | 310,432 | `546c762047c506ed` |
| `scrdata_202501.csv` | 313,638 | `b83581d2cdd44cd5` |
| `scrdata_202502.csv` | 313,564 | `11e82dc62a240be7` |
| `scrdata_202607.csv` | 310,193 | `ec7726666d73f369` |
| `planilha_201306.csv` | 499,766 | `dd8edb90f18074d0` |
| `planilha_202412.csv` | 995,670 | `d2b4b1f5c1f7f8a9` |
| `planilha_202506.csv` | 1,025,243 | `ae690ae295b58a8f` |
| `planilha_202507.csv` | 891,135 | `03ba96a5e7fbc32d` |
| `planilha_202607.csv` | 911,689 | `b6386ad0b245e8a6` |

Plus the header line and first data row of all 344 monthly files, read by range request.

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
uv run --no-project python scripts/recon/sgs.py
```

`uv sync` for the full project currently fails: `dbt-core` 1.12.4 depends on a pre-release parser
whose build step downloads a wheel from GitHub, and that download failed certificate verification
on this machine. The recon scripts avoid the project environment for that reason. Pinning
`dbt-core` is a build-phase task.
