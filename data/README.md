# data/

Everything under `data/` is gitignored and can be rebuilt. Until the pipeline has its own fetch
step, the research scripts download and stage the files:

```bash
uv run python scripts/recon/fetch_years.py data/raw/zips scrdata 2012 2026 --jobs 3
uv run python scripts/recon/to_parquet.py data/parquet/scrdata data/raw/zips/scrdata_*.zip
```

`fetch_years.py` checks every archive member against its CRC32 and records each archive's size,
Last-Modified date and SHA-256 in `data/raw/zips/MANIFEST.tsv`. BCB republishes the history, so
the manifest is what ties a run to one release.

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
