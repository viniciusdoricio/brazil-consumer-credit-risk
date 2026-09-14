# data/

`raw/` is gitignored. Everything here is reproducible from scratch:

```bash
make fetch
```

## Provenance

| Source | What | Licence |
|---|---|---|
| BCB SCR.data | Monthly aggregated credit operations, Jun 2012– | Open data, BCB |
| BCB SGS | Macro and credit time series | Open data, BCB |

Both are published by the Banco Central do Brasil under its open data
policy. Attribution required; check current terms before republishing
derived data.

## A note on what this data is not

SCR.data is **aggregated**. There is no account-level public credit data
in Brazil — bank secrecy and LGPD forbid it. Every conclusion drawn here
is about segments, never individuals.
