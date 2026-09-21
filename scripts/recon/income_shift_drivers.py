"""Where do the PF income-band shifts come from? Decompose each shift by lender segment, modality, UF.

    uv run python scripts/recon/income_shift_drivers.py data/parquet/scrdata

For each event (month-on-month change in one band's share of the PF portfolio) prints the
contribution of each segmento, modalidade and UF to the change in that band's share, in pp.
A shift concentrated in one lender segment or product points to a reporting change by those
lenders; a broad-based shift points to a common cause (a rule change or the minimum wage).
Also lists every change in the minimum wage (SGS 1619) since 2012, to catch non-January resets.
"""

import json
import sys

import duckdb
from sgs import curl

src = sys.argv[1]
EVENTS = [
    ("2018-10", "2018-11", "Indisponível"),
    ("2019-02", "2019-03", "Indisponível"),
    ("2019-02", "2019-03", "Acima de 20 salários mínimos"),
    ("2020-07", "2020-08", "Indisponível"),
    ("2021-08", "2021-09", "Indisponível"),
    ("2024-12", "2025-01", "Sem rendimento"),
    ("2025-01", "2025-02", "Sem rendimento"),
    ("2025-06", "2025-07", "Acima de 20 salários mínimos"),
    ("2025-06", "2025-07", "Mais de 1 a 2 salários mínimos"),
    ("2026-04", "2026-05", "Até 1 salário mínimo"),
    ("2026-04", "2026-05", "Mais de 5 a 10 salários mínimos"),
    ("2023-12", "2024-01", "Acima de 20 salários mínimos"),
    ("2023-12", "2024-01", "Até 1 salário mínimo"),
]
con = duckdb.connect()
con.execute(
    f"CREATE VIEW s AS SELECT *, strftime(data_base, '%Y-%m') AS m FROM read_parquet('{src}/scrdata_*.parquet') WHERE cliente = 'PF'"
)

for m0, m1, band in EVENTS:
    tot = dict(
        con.execute(
            f"SELECT m, CAST(sum(carteira_ativa) AS DOUBLE) FROM s WHERE m IN ('{m0}','{m1}') GROUP BY m"
        ).fetchall()
    )
    b0 = con.execute(
        f"SELECT CAST(sum(carteira_ativa) AS DOUBLE) FROM s WHERE m='{m0}' AND porte='{band}'"
    ).fetchone()[0]
    b1 = con.execute(
        f"SELECT CAST(sum(carteira_ativa) AS DOUBLE) FROM s WHERE m='{m1}' AND porte='{band}'"
    ).fetchone()[0]
    print(
        f"\n### {m0} -> {m1} | {band}: share {100 * b0 / tot[m0]:.2f}% -> {100 * b1 / tot[m1]:.2f}% "
        f"({100 * (b1 / tot[m1] - b0 / tot[m0]):+.2f} pp); balance R$ {b0 / 1e9:.1f} -> {b1 / 1e9:.1f} bn"
    )
    for dim in ("segmento", "modalidade", "uf"):
        rows = con.execute(
            f"""WITH x AS (
                  SELECT {dim} AS k,
                    coalesce(sum(carteira_ativa) FILTER (WHERE m='{m0}' AND porte='{band}'), 0) AS a0,
                    coalesce(sum(carteira_ativa) FILTER (WHERE m='{m1}' AND porte='{band}'), 0) AS a1,
                    coalesce(sum(carteira_ativa) FILTER (WHERE m='{m0}'), 0) AS t0,
                    coalesce(sum(carteira_ativa) FILTER (WHERE m='{m1}'), 0) AS t1
                  FROM s WHERE m IN ('{m0}','{m1}') GROUP BY 1)
                SELECT k, round(100*(a1/{tot[m1]} - a0/{tot[m0]}), 3) AS contrib_pp,
                       round(a0/1e9, 1) AS band_bn_before, round(a1/1e9, 1) AS band_bn_after,
                       round(100*a0/nullif(t0,0), 2) AS band_share_within_before,
                       round(100*a1/nullif(t1,0), 2) AS band_share_within_after
                FROM x ORDER BY abs(a1/{tot[m1]} - a0/{tot[m0]}) DESC LIMIT 4"""
        ).fetchall()
        print(
            f"  by {dim}: "
            + " ; ".join(
                f"{k}: {c:+.2f}pp (R${a:.1f}->{b:.1f}bn, {sa}%->{sb}% of its PF book)"
                for k, c, a, b, sa, sb in rows
            )
        )

mw = [
    (f"{d['data'][6:]}-{d['data'][3:5]}", float(d["valor"]))
    for d in json.loads(
        curl("https://api.bcb.gov.br/dados/serie/bcdata.sgs.1619/dados?formato=json")
    )
]
print("\nMinimum wage changes since 2012 (SGS 1619): month, old -> new")
for (_m_prev, v_prev), (m, v) in zip(mw, mw[1:], strict=False):
    if m >= "2012-01" and v != v_prev:
        print(f"  {m}: {v_prev:.2f} -> {v:.2f}")
