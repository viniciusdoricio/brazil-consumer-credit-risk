# data/

Apart from this file, everything under `data/` is gitignored and can be rebuilt with one
command:

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
changes. The manifest records which release a run used. If BCB can't be reached, archives already
on disk are still staged, and the run ends with an error so the missed check isn't silent.

## Provenance

| Source | What | Licence |
|---|---|---|
| BCB SCR.data | Monthly aggregated credit operations, from July 2012 | ODbL |
| BCB SGS, BCB's own series | Household 90-day delinquency, total and credit cards (21084, 21129) | ODbL |
| BCB SGS, series BCB republishes | Unemployment and IPCA (IBGE; 24369, 433), the minimum wage (1619) | Terms of the original publisher |

BCB's open-data portal publishes SCR.data and its own SGS series under the Open Database License
(ODbL). Charts and reports built from them need attribution. A derived dataset published from this
repository, such as an exported mart, must also be released under the ODbL.

## What this data is not

SCR.data is aggregated. There is no account-level public credit data in Brazil, because bank
secrecy and the LGPD forbid it. Every conclusion drawn here is about segments, never individuals.
