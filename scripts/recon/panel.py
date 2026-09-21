"""Month-by-month profile and break scan over the full V2 history (Parquet from to_parquet.py).

    uv run python scripts/recon/panel.py data/parquet/scrdata data/recon/panel

Writes CSVs to the output directory and prints a summary:

  month_summary.csv      rows, grain uniqueness, PF cells populated, identity failures, sentinels,
                         PF/PJ portfolio and rates, SCR-vs-SGS 21084 gap, PF growth vs SGS 20541
  category_presence.csv  every dimension value: first/last month, months present, gaps
  pf_series.csv          PF shares and rates by occupation, income band, modality, and total
  steps.csv              candidate breaks: month-on-month changes that are extreme against the
                         series' own history (robust z-score > 6, plus an absolute floor)

Step rule, per series: d_t = x_t - x_{t-1}; z_t = (d_t - median(d)) / (1.4826 * MAD(d)).
Flagged if |z| > 6 AND the move is material: >= 0.25 pp for a share of PF portfolio,
>= 0.15 pp for a rate on a series with >= R$10 bn of portfolio. A flag is a candidate for
inspection, not a finding: January seasonality and real shocks also trip it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb
from sgs import curl

src, out = Path(sys.argv[1]), Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
con = duckdb.connect()
con.execute(
    f"CREATE VIEW s AS SELECT *, strftime(data_base, '%Y-%m') AS m FROM read_parquet('{src}/scrdata_*.parquet')"
)
DIMCOLS = (
    "uf, segmento, cliente, cnae_ocupacao, porte, modalidade, submodalidade, origem, indexador"
)
AV = (
    "a_vencer_ate_90_dias + a_vencer_de_91_ate_360_dias + a_vencer_de_361_ate_1080_dias + "
    "a_vencer_de_1081_ate_1800_dias + a_vencer_de_1801_ate_5400_dias + a_vencer_acima_de_5400_dias"
)
MEAS = (
    "a_vencer_ate_90_dias, a_vencer_de_91_ate_360_dias, a_vencer_de_361_ate_1080_dias, "
    "a_vencer_de_1081_ate_1800_dias, a_vencer_de_1801_ate_5400_dias, a_vencer_acima_de_5400_dias, "
    "carteira_a_vencer, vencido_de_15_ate_90_dias, vencido_acima_de_90_dias, carteira_vencida, "
    "carteira_ativa, carteira_inadimplencia, ativo_problematico"
)


def show(title: str, sql: str, limit: int = 60) -> None:
    r = con.execute(sql)
    cols = [d[0] for d in r.description]
    rows = r.fetchall()
    print(f"\n### {title} ({len(rows)} rows)\n    " + " | ".join(cols))
    for row in rows[:limit]:
        print("    " + " | ".join(str(v) for v in row))
    if len(rows) > limit:
        print(f"    ... {len(rows) - limit} more (see CSV)")


# --- months present and contiguity -------------------------------------------------------------
months = [r[0] for r in con.execute("SELECT DISTINCT m FROM s ORDER BY 1").fetchall()]
idx = [int(x[:4]) * 12 + int(x[5:]) - 1 for x in months]
missing = [f"{i // 12}-{i % 12 + 1:02d}" for i in range(idx[0], idx[-1] + 1) if i not in set(idx)]
print(
    f"months: {len(months)} ({months[0]} .. {months[-1]}); missing inside range: {missing or 'none'}"
)

# --- per-month structural checks (looped so each distinct-count stays small) --------------------
con.execute(
    "CREATE TEMP TABLE grain (m VARCHAR, rows BIGINT, distinct_tuples BIGINT, pf_cells BIGINT)"
)
for mo in months:
    con.execute(
        f"""INSERT INTO grain SELECT '{mo}', count(*),
              (SELECT count(*) FROM (SELECT DISTINCT {DIMCOLS} FROM s WHERE m = '{mo}')),
              count(DISTINCT (cnae_ocupacao, porte)) FILTER (WHERE cliente = 'PF' AND carteira_ativa > 0)
            FROM s WHERE m = '{mo}'"""
    )

# --- official series for reconciliation ---------------------------------------------------------
sgs = {}
for code in (21084, 20541):
    data = json.loads(
        curl(f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados?formato=json")
    )
    sgs[code] = {f"{d['data'][6:]}-{d['data'][3:5]}": float(d["valor"]) for d in data}
con.execute("CREATE TEMP TABLE sgs (m VARCHAR, sgs_21084 DOUBLE, sgs_20541 DOUBLE)")
con.executemany(
    "INSERT INTO sgs VALUES (?, ?, ?)",
    [(mo, sgs[21084].get(mo), sgs[20541].get(mo)) for mo in months],
)

con.execute(
    f"""CREATE TEMP TABLE month_summary AS
    WITH base AS (
      SELECT m,
        count(*) FILTER (WHERE abs(carteira_a_vencer - ({AV})) > 0.05) AS id_a_vencer_off,
        count(*) FILTER (WHERE abs(carteira_vencida - (vencido_de_15_ate_90_dias + vencido_acima_de_90_dias)) > 0.05) AS id_vencida_off,
        count(*) FILTER (WHERE abs(carteira_ativa - (carteira_a_vencer + carteira_vencida)) > 0.05) AS id_ativa_off,
        round(sum(abs(carteira_ativa - (carteira_a_vencer + carteira_vencida)))/1e6, 3) AS id_ativa_gap_mn,
        count(*) FILTER (WHERE ativo_problematico < carteira_inadimplencia - 0.05) AS ap_below_inad,
        count(*) FILTER (WHERE carteira_inadimplencia < vencido_acima_de_90_dias - 0.05) AS inad_below_v90,
        count(*) FILTER (WHERE least({MEAS}) < 0) AS negative_rows,
        count(*) FILTER (WHERE numero_de_operacoes = -1) AS sentinel_rows,
        count(*) FILTER (WHERE numero_de_operacoes IS NULL OR numero_de_operacoes < -1 OR numero_de_operacoes = 0) AS ops_other_odd,
        count(DISTINCT segmento) AS n_segmento, count(DISTINCT submodalidade) AS n_submodalidade,
        count(DISTINCT indexador) AS n_indexador, count(DISTINCT modalidade) AS n_modalidade,
        count(DISTINCT uf) AS n_uf,
        sum(carteira_ativa) FILTER (WHERE cliente='PF') AS pf_a,
        sum(carteira_ativa) FILTER (WHERE cliente='PJ') AS pj_a,
        sum(vencido_de_15_ate_90_dias) FILTER (WHERE cliente='PF') AS pf_n15,
        sum(vencido_acima_de_90_dias) FILTER (WHERE cliente='PF') AS pf_v90,
        sum(carteira_inadimplencia) FILTER (WHERE cliente='PF') AS pf_n90,
        sum(ativo_problematico) FILTER (WHERE cliente='PF') AS pf_ap,
        sum(carteira_inadimplencia) FILTER (WHERE cliente='PJ') AS pj_n90,
        sum(ativo_problematico) FILTER (WHERE cliente='PJ') AS pj_ap
      FROM s GROUP BY m)
    SELECT b.m, g.rows, g.rows = g.distinct_tuples AS grain_unique, g.pf_cells,
      b.id_a_vencer_off, b.id_vencida_off, b.id_ativa_off, b.id_ativa_gap_mn, b.ap_below_inad,
      b.inad_below_v90, b.negative_rows, b.sentinel_rows, b.ops_other_odd,
      b.n_uf, b.n_segmento, b.n_modalidade, b.n_submodalidade, b.n_indexador,
      round(b.pf_a/1e9, 2) AS pf_carteira_bn, round(b.pj_a/1e9, 2) AS pj_carteira_bn,
      round(100*b.pf_n15/b.pf_a, 3) AS pf_d15, round(100*b.pf_v90/b.pf_a, 3) AS pf_v90,
      round(100*b.pf_n90/b.pf_a, 3) AS pf_d90, round(100*b.pf_ap/b.pf_a, 3) AS pf_ap,
      round(100*b.pj_n90/b.pj_a, 3) AS pj_d90, round(100*b.pj_ap/b.pj_a, 3) AS pj_ap,
      x.sgs_21084, round(100*b.pf_n90/b.pf_a - x.sgs_21084, 3) AS pf_d90_minus_sgs,
      round(100*(b.pf_a / lag(b.pf_a) OVER (ORDER BY b.m) - 1), 2) AS pf_growth_mom,
      round(100*(x.sgs_20541 / lag(x.sgs_20541) OVER (ORDER BY b.m) - 1), 2) AS sgs20541_growth_mom
    FROM base b JOIN grain g USING (m) LEFT JOIN sgs x USING (m) ORDER BY b.m"""
)
con.execute(f"COPY month_summary TO '{out}/month_summary.csv' (HEADER)")

# --- category presence ------------------------------------------------------------------------
unions = " UNION ALL ".join(
    f"SELECT '{d}' AS dim, cliente, {d} AS value, m FROM s GROUP BY ALL"
    for d in (
        "uf",
        "segmento",
        "cnae_ocupacao",
        "porte",
        "modalidade",
        "submodalidade",
        "origem",
        "indexador",
    )
)
con.execute(
    f"""CREATE TEMP TABLE presence AS
    SELECT dim, cliente, value, min(m) AS first_month, max(m) AS last_month, count(DISTINCT m) AS months_present,
      (CAST(substr(max(m),1,4) AS INT)*12 + CAST(substr(max(m),6,2) AS INT))
        - (CAST(substr(min(m),1,4) AS INT)*12 + CAST(substr(min(m),6,2) AS INT)) + 1 - count(DISTINCT m) AS gap_months
    FROM ({unions}) GROUP BY ALL ORDER BY dim, cliente, first_month, value"""
)
con.execute(f"COPY presence TO '{out}/category_presence.csv' (HEADER)")

# --- PF series by dimension ---------------------------------------------------------------------
series_sql = " UNION ALL ".join(
    f"""SELECT m, '{label}' AS dim, {col} AS value, sum(carteira_ativa) AS a,
          sum(vencido_de_15_ate_90_dias) AS n15, sum(carteira_inadimplencia) AS n90, sum(ativo_problematico) AS nap
        FROM s WHERE cliente = 'PF' GROUP BY ALL"""
    for label, col in (
        ("total", "'PF'"),
        ("occupation", "cnae_ocupacao"),
        ("income", "porte"),
        ("modalidade", "modalidade"),
    )
)
con.execute(
    f"""CREATE TEMP TABLE pf_series AS
    SELECT m, dim, value, round(a/1e9, 3) AS carteira_bn,
      100*a/sum(a) OVER (PARTITION BY m, dim) AS share_pct,
      100*n15/a AS d15, 100*n90/a AS d90, 100*nap/a AS ap
    FROM ({series_sql}) ORDER BY dim, value, m"""
)
con.execute(f"COPY pf_series TO '{out}/pf_series.csv' (HEADER)")

# --- robust step detection ----------------------------------------------------------------------
con.execute(
    """CREATE TEMP TABLE steps AS
    WITH long AS (
      SELECT m, dim, value, carteira_bn, 'share_pct' AS metric, share_pct AS x FROM pf_series WHERE dim <> 'total'
      UNION ALL SELECT m, dim, value, carteira_bn, 'd15', d15 FROM pf_series
      UNION ALL SELECT m, dim, value, carteira_bn, 'd90', d90 FROM pf_series
      UNION ALL SELECT m, dim, value, carteira_bn, 'ap', ap FROM pf_series),
    d AS (
      SELECT *, x - lag(x) OVER (PARTITION BY dim, value, metric ORDER BY m) AS dx FROM long),
    med AS (
      SELECT dim, value, metric, median(dx) AS med FROM d WHERE dx IS NOT NULL GROUP BY ALL),
    mad AS (
      SELECT d.dim, d.value, d.metric, any_value(med.med) AS med, median(abs(d.dx - med.med)) AS mad
      FROM d JOIN med USING (dim, value, metric) WHERE d.dx IS NOT NULL GROUP BY ALL)
    SELECT d.m, d.dim, d.value, d.metric, round(d.x - d.dx, 3) AS before, round(d.x, 3) AS after,
      round(d.dx, 3) AS change_pp, round((d.dx - mad.med) / nullif(1.4826 * mad.mad, 0), 1) AS robust_z,
      d.carteira_bn
    FROM d JOIN mad USING (dim, value, metric)
    WHERE d.dx IS NOT NULL
      AND abs((d.dx - mad.med) / nullif(1.4826 * mad.mad, 0)) > 6
      AND ((d.metric = 'share_pct' AND abs(d.dx) >= 0.25)
        OR (d.metric <> 'share_pct' AND abs(d.dx) >= 0.15 AND d.carteira_bn >= 10))
    ORDER BY d.m, d.dim, d.value, d.metric"""
)
con.execute(f"COPY steps TO '{out}/steps.csv' (HEADER)")

# --- printed summary ----------------------------------------------------------------------------
show(
    "Months failing a structural check (grain, 72 cells, identities, negatives, odd op counts)",
    """SELECT m, rows, grain_unique, pf_cells, id_a_vencer_off, id_vencida_off, id_ativa_off, id_ativa_gap_mn,
              negative_rows, ops_other_odd, inad_below_v90
       FROM month_summary
       WHERE NOT grain_unique OR pf_cells < 72 OR id_a_vencer_off > 0 OR id_vencida_off > 0 OR id_ativa_off > 0
          OR negative_rows > 0 OR ops_other_odd > 0 OR inad_below_v90 > 0""",
)
show(
    "Category counts over time (months where a count changes)",
    """SELECT m, n_uf, n_segmento, n_modalidade, n_submodalidade, n_indexador FROM (
         SELECT *, lag(n_segmento) OVER w AS p1, lag(n_submodalidade) OVER w AS p2, lag(n_indexador) OVER w AS p3,
                lag(n_modalidade) OVER w AS p4, lag(n_uf) OVER w AS p5
         FROM month_summary WINDOW w AS (ORDER BY m))
       WHERE p1 IS NULL OR n_segmento <> p1 OR n_submodalidade <> p2 OR n_indexador <> p3 OR n_modalidade <> p4 OR n_uf <> p5""",
)
show(
    "Dimension values not present in every month of their span, or not spanning the full history",
    f"""SELECT dim, cliente, value, first_month, last_month, months_present, gap_months FROM presence
        WHERE first_month > '{months[0]}' OR last_month < '{months[-1]}' OR gap_months > 0""",
    limit=120,
)
show(
    "PF 90-day rate vs SGS 21084: distribution of the gap (pp)",
    """SELECT count(*) AS months, round(min(pf_d90_minus_sgs),3) AS min, round(quantile_cont(pf_d90_minus_sgs, 0.5),3) AS median,
              round(max(pf_d90_minus_sgs),3) AS max, count(*) FILTER (WHERE abs(pf_d90_minus_sgs) > 0.2) AS months_over_0_2pp
       FROM month_summary""",
)
show(
    "Months where the PF 90-day gap to SGS exceeds 0.2 pp",
    "SELECT m, pf_d90, sgs_21084, pf_d90_minus_sgs FROM month_summary WHERE abs(pf_d90_minus_sgs) > 0.2",
)
show(
    "Months where PF portfolio growth departs from SGS 20541 by more than 1 pp (scope-change candidates)",
    """SELECT m, pf_carteira_bn, pf_growth_mom, sgs20541_growth_mom, round(pf_growth_mom - sgs20541_growth_mom, 2) AS gap
       FROM month_summary WHERE abs(pf_growth_mom - sgs20541_growth_mom) > 1""",
)
show("Candidate breaks (robust step scan)", "SELECT * FROM steps", limit=200)
