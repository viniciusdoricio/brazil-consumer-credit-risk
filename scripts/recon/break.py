"""Quantify the Jan-2025 break in V2: Jun-2024, Dec-2024, Jan-2025, Jul-2026 side by side."""

import os

import duckdb

con = duckdb.connect(os.environ.get("RECON_DB", "data/recon.duckdb"), read_only=True)
T = ["scrdata_202406", "scrdata_202412", "scrdata_202501", "scrdata_202607"]
u = " UNION ALL ".join(
    f"SELECT * EXCLUDE (raw_uf, raw_segmento, raw_cliente, raw_cnae_ocupacao, raw_porte, raw_modalidade, raw_submodalidade, raw_origem, raw_indexador, raw_numero_de_operacoes) FROM {t}"
    for t in T
)
con.execute(f"CREATE TEMP VIEW v AS {u}")
M = """round(sum(carteira_ativa)/1e9,1) ativa_bi,
 round(100*sum(vencido_de_15_ate_90_dias)/sum(carteira_ativa),3) p15_90,
 round(100*sum(vencido_acima_de_90_dias)/sum(carteira_ativa),3) p_v90,
 round(100*sum(carteira_inadimplencia)/sum(carteira_ativa),3) p_inad,
 round(100*sum(ativo_problematico)/sum(carteira_ativa),3) p_ap,
 round(100*(sum(ativo_problematico)-sum(carteira_inadimplencia))/sum(carteira_ativa),3) p_ap_ex_inad,
 round(sum(ativo_problematico)/1e9,1) ap_bi, round(sum(carteira_inadimplencia)/1e9,1) inad_bi"""


def show(title, sql):
    r = con.execute(sql)
    cols = [d[0] for d in r.description]
    rows = r.fetchall()
    print(f"\n### {title}\n    " + " | ".join(cols))
    for x in rows:
        print("    " + " | ".join(str(v) for v in x))


show("by cliente, by month", f"SELECT cliente, data_base, {M} FROM v GROUP BY ALL ORDER BY 1,2")
show(
    "PF by occupation, Dec-24 vs Jan-25",
    f"SELECT cnae_ocupacao, data_base, {M} FROM v WHERE cliente='PF' AND data_base IN ('2024-12-31','2025-01-31') GROUP BY ALL ORDER BY 1,2",
)
show(
    "PF by income, Dec-24 vs Jan-25",
    f"SELECT porte, data_base, {M} FROM v WHERE cliente='PF' AND data_base IN ('2024-12-31','2025-01-31') GROUP BY ALL ORDER BY 1,2",
)
show(
    "PF by modalidade, Dec-24 vs Jan-25",
    f"SELECT modalidade, data_base, {M} FROM v WHERE cliente='PF' AND data_base IN ('2024-12-31','2025-01-31') GROUP BY ALL ORDER BY 1,2",
)
show(
    "PF by segmento, Dec-24 vs Jan-25",
    f"SELECT segmento, data_base, {M} FROM v WHERE cliente='PF' AND data_base IN ('2024-12-31','2025-01-31') GROUP BY ALL ORDER BY 1,2",
)
show(
    "rows where AP < inadimplencia, by month",
    "SELECT data_base, count(*) n, round(sum(carteira_inadimplencia-ativo_problematico)/1e9,3) gap_bi FROM v WHERE ativo_problematico < carteira_inadimplencia - 0.05 GROUP BY 1 ORDER BY 1",
)
show(
    "rows with AP>0 but zero inadimplencia (AP not driven by >90), by month",
    "SELECT data_base, cliente, count(*) n, round(sum(ativo_problematico)/1e9,2) ap_bi FROM v WHERE ativo_problematico > 0 AND carteira_inadimplencia = 0 GROUP BY ALL ORDER BY 1,2",
)
