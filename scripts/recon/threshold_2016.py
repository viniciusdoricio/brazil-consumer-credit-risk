"""June-2016 scope change (SCR threshold R$1,000 -> R$200): what moved between May and June 2016.

RECON_DB=data/recon.duckdb uv run --no-project --with duckdb python scripts/recon/threshold_2016.py
"""

import os

import duckdb

con = duckdb.connect(os.environ.get("RECON_DB", "data/recon.duckdb"), read_only=True)
T = ["scrdata_201605", "scrdata_201606"]
con.execute(
    "CREATE TEMP VIEW v AS "
    + " UNION ALL ".join(
        f"SELECT data_base, cliente, cnae_ocupacao, porte, modalidade, submodalidade, "
        f"numero_de_operacoes, carteira_ativa, vencido_de_15_ate_90_dias, vencido_acima_de_90_dias, "
        f"carteira_inadimplencia, ativo_problematico FROM {t}"
        for t in T
    )
)


def show(title, sql):
    r = con.execute(sql)
    cols = [d[0] for d in r.description]
    print(f"\n### {title}\n    " + " | ".join(cols))
    for x in r.fetchall():
        print("    " + " | ".join(str(v) for v in x))


M = """round(sum(carteira_ativa)/1e9, 2) ativa_bi,
 sum(numero_de_operacoes) FILTER (WHERE numero_de_operacoes > 0) ops_pos,
 count(*) FILTER (WHERE numero_de_operacoes = -1) rows_sentinel,
 round(100*sum(vencido_de_15_ate_90_dias)/sum(carteira_ativa), 3) d15,
 round(100*sum(vencido_acima_de_90_dias)/sum(carteira_ativa), 3) v90,
 round(100*sum(carteira_inadimplencia)/sum(carteira_ativa), 3) d90,
 round(100*sum(ativo_problematico)/sum(carteira_ativa), 3) ap"""
show(
    "rows by month",
    "SELECT strftime(data_base, '%Y-%m') m, count(*) n FROM v GROUP BY 1 ORDER BY 1",
)
show(
    "by cliente",
    f"SELECT cliente, strftime(data_base, '%Y-%m') m, {M} FROM v GROUP BY ALL ORDER BY 1, 2",
)
show(
    "PF by income band",
    f"SELECT porte, strftime(data_base, '%Y-%m') m, {M} FROM v WHERE cliente='PF' GROUP BY ALL ORDER BY 1, 2",
)
show(
    "PF by occupation",
    f"SELECT cnae_ocupacao, strftime(data_base, '%Y-%m') m, {M} FROM v WHERE cliente='PF' GROUP BY ALL ORDER BY 1, 2",
)
show(
    "PF by modalidade",
    f"SELECT modalidade, strftime(data_base, '%Y-%m') m, {M} FROM v WHERE cliente='PF' GROUP BY ALL ORDER BY 1, 2",
)
