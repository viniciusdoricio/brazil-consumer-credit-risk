"""Does the SCR.data vs SGS 21084 gap come from scope? Recompute the PF 90-day rate on SGS's scope.

    uv run --no-project --with duckdb python scripts/recon/sgs_scope.py data/parquet/scrdata

BCB's credit-statistics methodology note (notaempr.pdf, footnote 2) says SGS delinquency rates, built
from doc 3050, exclude credit cooperatives, development agencies and microcredit companies. SCR.data
includes them. This compares SGS 21084 with the SCR.data PF rate (a) as published, (b) excluding
segmento 'Cooperativa', (c) also excluding 'Desenvolvimento/Fomento' and 'Outros' (the segment that
holds microcredit companies, among others).
"""

import json
import sys

import duckdb
from sgs import curl

src = sys.argv[1]
sgs = {
    f"{d['data'][6:]}-{d['data'][3:5]}": float(d["valor"])
    for d in json.loads(
        curl("https://api.bcb.gov.br/dados/serie/bcdata.sgs.21084/dados?formato=json")
    )
}
con = duckdb.connect()
rows = con.execute(
    f"""SELECT strftime(data_base, '%Y-%m') AS m,
          100*sum(carteira_inadimplencia)/sum(carteira_ativa) AS all_seg,
          100*sum(carteira_inadimplencia) FILTER (WHERE segmento <> 'Cooperativa')
             / sum(carteira_ativa) FILTER (WHERE segmento <> 'Cooperativa') AS ex_coop,
          100*sum(carteira_inadimplencia) FILTER (WHERE segmento NOT IN ('Cooperativa', 'Desenvolvimento/Fomento', 'Outros'))
             / sum(carteira_ativa) FILTER (WHERE segmento NOT IN ('Cooperativa', 'Desenvolvimento/Fomento', 'Outros')) AS ex_coop_fom_out,
          100*sum(carteira_ativa) FILTER (WHERE segmento = 'Cooperativa')/sum(carteira_ativa) AS coop_share,
          100*sum(carteira_inadimplencia) FILTER (WHERE segmento = 'Cooperativa')
             / sum(carteira_ativa) FILTER (WHERE segmento = 'Cooperativa') AS coop_d90
        FROM read_parquet('{src}/scrdata_*.parquet') WHERE cliente = 'PF' GROUP BY 1 ORDER BY 1"""
).fetchall()


def stats(label, lo, hi, idx):
    gaps = [r[idx] - sgs[r[0]] for r in rows if lo <= r[0] <= hi and r[0] in sgs]
    gaps.sort()
    n = len(gaps)
    print(
        f"  {label:<28} n={n:3d}  median {gaps[n // 2]:+.3f}  min {gaps[0]:+.3f}  max {gaps[-1]:+.3f}  "
        f"mean |gap| {sum(abs(g) for g in gaps) / n:.3f}"
    )


for lo, hi in (("2017-01", "2024-12"), ("2025-01", "2026-07")):
    print(f"\nGap to SGS 21084 (pp), {lo} .. {hi}")
    stats("SCR.data, all segments", lo, hi, 1)
    stats("excluding cooperatives", lo, hi, 2)
    stats("excl. coop, fomento, outros", lo, hi, 3)

print("\nmonth | SGS | all | ex-coop | ex-coop-fom-out | coop share % | coop 90-day %")
for r in rows:
    if r[0] >= "2025-01" or r[0] in ("2017-01", "2019-12", "2022-12", "2024-12"):
        print(
            f"{r[0]} | {sgs.get(r[0])} | {r[1]:.3f} | {r[2]:.3f} | {r[3]:.3f} | {r[4]:.2f} | {r[5]:.3f}"
        )
