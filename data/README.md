# data/

Everything under `data/` is gitignored and can be rebuilt with one command:

```bash
make fetch        # the same as: uv run fetch-data
```

| Path | What |
|---|---|
| `raw/zips/` | SCR.data yearly archives, and `MANIFEST.tsv` with each archive's size, Last-Modified date and SHA-256 |
| `parquet/scrdata/` | one typed Parquet file per month, and `conversion_log.jsonl` |
| `raw/sgs/`, `parquet/sgs.parquet` | the SGS series, raw and tidy |

Every archive member is checked against its CRC32 before anything is converted. BCB republishes
past years, so a local archive is kept even when a newer version appears, until
`uv run fetch-data --refresh` replaces it, and a month is converted again whenever its archive
changes. The manifest records which release a run used.

## Provenance

| Source | What | Licence |
|---|---|---|
| BCB SCR.data | Monthly aggregated credit operations, from July 2012 | ODbL |
| BCB SGS, credit and rate series | Delinquency, balances, new lending, rates, spreads, household debt, Selic | ODbL |
| BCB SGS, republished series | Unemployment and IPCA (IBGE), the minimum wage | Terms of the original publisher |

BCB's open-data portal publishes SCR.data and its own SGS series under the Open Database License
(ODbL). Charts and reports built from them need attribution. A derived dataset published from this
repository, such as an exported mart, must also be released under the ODbL.

## What this data is not

SCR.data is aggregated. There is no account-level public credit data in Brazil, because bank
secrecy and the LGPD forbid it. Every conclusion drawn here is about segments, never individuals.
