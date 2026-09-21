"""Context around the candidate breaks found by panel.py, full V2 history.

    uv run python scripts/recon/breaks_context.py data/parquet/scrdata

Prints: December->January shifts by occupation and income band for every year (share and rates,
against the PF total as the seasonal baseline); every month the "Outros" occupation moves >= 0.5 pp;
income-band shifts around the Indisponivel recodings; the March-2014 15-90 day break; card
sub-modality continuity around May 2017; and the SCR-vs-SGS 21084 gap since 2025.
"""

import json
import sys

import duckdb
from sgs import curl

src = sys.argv[1]
con = duckdb.connect()
con.execute(
    f"CREATE VIEW s AS SELECT *, strftime(data_base, '%Y-%m') AS m FROM read_parquet('{src}/scrdata_*.parquet') WHERE cliente = 'PF'"
)
con.execute(
    """CREATE TEMP TABLE ser AS
    SELECT m, dim, value, a, 100*a/sum(a) OVER (PARTITION BY m, dim) AS share, 100*n15/a AS d15, 100*n90/a AS d90
    FROM (
      SELECT m, 'total' AS dim, 'PF' AS value, sum(carteira_ativa) AS a, sum(vencido_de_15_ate_90_dias) AS n15, sum(carteira_inadimplencia) AS n90 FROM s GROUP BY ALL
      UNION ALL SELECT m, 'occupation', cnae_ocupacao, sum(carteira_ativa), sum(vencido_de_15_ate_90_dias), sum(carteira_inadimplencia) FROM s GROUP BY ALL
      UNION ALL SELECT m, 'income', porte, sum(carteira_ativa), sum(vencido_de_15_ate_90_dias), sum(carteira_inadimplencia) FROM s GROUP BY ALL)"""
)


def show(title, sql):
    r = con.execute(sql)
    cols = [d[0] for d in r.description]
    print(f"\n### {title}\n    " + " | ".join(cols))
    for row in r.fetchall():
        print(
            "    "
            + " | ".join(
                "" if v is None else (f"{v:.2f}" if isinstance(v, float) else str(v)) for v in row
            )
        )


def pair(dim, m0, m1, value_filter=""):
    return f"""SELECT '{m0}->{m1}' AS step, b.value,
        round(b.share - a.share, 2) AS d_share_pp, round(b.d90 - a.d90, 2) AS d_d90_pp, round(b.d15 - a.d15, 2) AS d_d15_pp,
        round(a.share, 2) AS share_before, round(a.d90, 2) AS d90_before, round(b.d90, 2) AS d90_after
      FROM ser a JOIN ser b ON a.dim = b.dim AND a.value = b.value
      WHERE a.m = '{m0}' AND b.m = '{m1}' AND a.dim IN ('{dim}', 'total') {value_filter}
      ORDER BY a.dim = 'total' DESC, b.value"""


for y in range(2016, 2027):
    show(f"Occupation, Dec {y - 1} -> Jan {y}", pair("occupation", f"{y - 1}-12", f"{y}-01"))

show(
    "Every month the 'Outros' occupation share moves >= 0.5 pp",
    """SELECT m, round(share - lag(share) OVER (ORDER BY m), 2) AS d_share_pp, round(share, 2) AS share,
              round(d90 - lag(d90) OVER (ORDER BY m), 2) AS d_d90_pp
       FROM ser WHERE dim = 'occupation' AND value = 'Outros' QUALIFY abs(d_share_pp) >= 0.5 ORDER BY m""",
)
for y in range(2017, 2027):
    show(f"Income band, Dec {y - 1} -> Jan {y}", pair("income", f"{y - 1}-12", f"{y}-01"))
for m0, m1 in (
    ("2018-10", "2018-11"),
    ("2019-02", "2019-03"),
    ("2020-07", "2020-08"),
    ("2021-08", "2021-09"),
):
    show(f"Income band, {m0} -> {m1}", pair("income", m0, m1))

show(
    "15-90 day rate, PF total and by modality, 2014-01 .. 2014-06",
    """PIVOT (SELECT m, modalidade, round(100*sum(vencido_de_15_ate_90_dias)/sum(carteira_ativa), 3) d15 FROM s
             WHERE m BETWEEN '2014-01' AND '2014-06' GROUP BY ALL
             UNION ALL SELECT m, '_TOTAL', round(100*sum(vencido_de_15_ate_90_dias)/sum(carteira_ativa), 3) FROM s
             WHERE m BETWEEN '2014-01' AND '2014-06' GROUP BY ALL) ON m USING first(d15) ORDER BY modalidade""",
)
show(
    "Card-related sub-modalities, share of PF portfolio (%), 2017-02 .. 2017-08",
    """PIVOT (SELECT m, submodalidade, round(100*sum(carteira_ativa)/any_value(tot), 2) sh FROM s
             JOIN (SELECT m, sum(carteira_ativa) tot FROM s GROUP BY m) USING (m)
             WHERE m BETWEEN '2017-02' AND '2017-08' AND (submodalidade ILIKE '%cart%' OR submodalidade ILIKE '%rotativo%')
             GROUP BY ALL) ON m USING first(sh) ORDER BY submodalidade""",
)
show(
    "Card group total: share, 15-90 and 90-day rate, 2017-02 .. 2017-08",
    """SELECT m, round(100*sum(carteira_ativa)/any_value(tot), 2) AS share, round(100*sum(vencido_de_15_ate_90_dias)/sum(carteira_ativa), 2) AS d15,
              round(100*sum(carteira_inadimplencia)/sum(carteira_ativa), 2) d90
       FROM s JOIN (SELECT m, sum(carteira_ativa) tot FROM s GROUP BY m) USING (m)
       WHERE m BETWEEN '2017-02' AND '2017-08' AND (submodalidade ILIKE '%cart%' OR submodalidade ILIKE '%rotativo%')
       GROUP BY m ORDER BY m""",
)

sgs = {
    f"{d['data'][6:]}-{d['data'][3:5]}": float(d["valor"])
    for d in json.loads(
        curl("https://api.bcb.gov.br/dados/serie/bcdata.sgs.21084/dados?formato=json")
    )
}
rows = con.execute(
    "SELECT m, d90 FROM ser WHERE dim = 'total' AND m >= '2024-10' ORDER BY m"
).fetchall()
print("\n### PF 90-day rate, SCR.data vs SGS 21084, since 2024-10\n    m | scr | sgs | gap")
for m, d90 in rows:
    g = sgs.get(m)
    print(
        f"    {m} | {d90:.3f} | {g if g is not None else ''} | {'' if g is None else round(d90 - g, 3)}"
    )
