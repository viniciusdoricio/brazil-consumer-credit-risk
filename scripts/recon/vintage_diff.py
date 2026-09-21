"""Compare two releases of the same months: what changed when BCB republished an archive.

    uv run python scripts/recon/vintage_diff.py data/parquet/vintage_2026-09-15 data/parquet/scrdata

For every month present in both directories: row counts, the PF portfolio (R$ bn), the PF 90-day
rate (%), and how many rows appear only in the old or only in the new release. Used in
docs/data-dictionary.md, section 1.1.
"""

import sys
from pathlib import Path

import duckdb

old, new = Path(sys.argv[1]), Path(sys.argv[2])


def months(folder: Path) -> set[str]:
    return {p.stem.removeprefix("scrdata_") for p in folder.glob("scrdata_*.parquet")}


con = duckdb.connect()
print("month | rows old -> new | PF portfolio R$ bn | PF 90-day % | rows only in old / new")
for m in sorted(months(old) & months(new)):
    a, b = old / f"scrdata_{m}.parquet", new / f"scrdata_{m}.parquet"
    totals = [
        con.execute(
            f"""SELECT count(*),
                       sum(carteira_ativa) FILTER (WHERE cliente = 'PF') / 1e9,
                       100 * sum(carteira_inadimplencia) FILTER (WHERE cliente = 'PF')
                           / sum(carteira_ativa) FILTER (WHERE cliente = 'PF')
                FROM '{f}'"""
        ).fetchone()
        for f in (a, b)
    ]
    only = [
        con.execute(
            f"SELECT count(*) FROM (SELECT * FROM '{x}' EXCEPT ALL SELECT * FROM '{y}')"
        ).fetchone()[0]
        for x, y in ((a, b), (b, a))
    ]
    (r0, c0, d0), (r1, c1, d1) = totals
    print(
        f"{m} | {r0:,} -> {r1:,} | {c0:,.1f} -> {c1:,.1f} | {d0:.3f} -> {d1:.3f} | "
        f"{only[0]:,} / {only[1]:,}"
    )
