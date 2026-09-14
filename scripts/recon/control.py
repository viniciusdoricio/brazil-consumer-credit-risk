"""Seasonal control for the Jan-2025 break: Dec23->Jan24 vs Nov24->Dec24->Jan25 (V2, PF)."""

import os

import duckdb

con = duckdb.connect(os.environ.get("RECON_DB", "data/recon.duckdb"), read_only=True)
T = [
    "scrdata_202312",
    "scrdata_202401",
    "scrdata_202411",
    "scrdata_202412",
    "scrdata_202501",
    "scrdata_202607",
]
con.execute(
    "CREATE TEMP VIEW v AS "
    + " UNION ALL ".join(
        f"SELECT data_base, cliente, cnae_ocupacao, porte, modalidade, segmento, carteira_ativa, vencido_de_15_ate_90_dias, "
        f"vencido_acima_de_90_dias, carteira_inadimplencia, ativo_problematico FROM {t}"
        for t in T
    )
)


def show(title, sql):
    r = con.execute(sql)
    cols = [d[0] for d in r.description]
    print(f"\n### {title}\n    " + " | ".join(cols))
    for x in r.fetchall():
        print("    " + " | ".join(str(v) for v in x))


M = """round(sum(carteira_ativa)/1e9,1) ativa_bi, round(100*sum(vencido_de_15_ate_90_dias)/sum(carteira_ativa),3) p15_90,
 round(100*sum(vencido_acima_de_90_dias)/sum(carteira_ativa),3) p_v90, round(100*sum(carteira_inadimplencia)/sum(carteira_ativa),3) p_inad,
 round(100*sum(ativo_problematico)/sum(carteira_ativa),3) p_ap, round(100*(sum(ativo_problematico)-sum(carteira_inadimplencia))/sum(carteira_ativa),3) p_ap_ex_inad"""
show(
    "PF and PJ by month",
    f"SELECT cliente, strftime(data_base,'%Y-%m') m, {M} FROM v GROUP BY ALL ORDER BY 1,2",
)
show(
    "PF income-band shares (%) by month",
    "PIVOT (SELECT porte, strftime(data_base,'%Y-%m') m, round(100*sum(carteira_ativa)/sum(sum(carteira_ativa)) OVER (PARTITION BY data_base),2) s FROM v WHERE cliente='PF' GROUP BY porte, data_base) ON m USING first(s) ORDER BY porte",
)
show(
    "PF occupation shares (%) by month",
    "PIVOT (SELECT cnae_ocupacao, strftime(data_base,'%Y-%m') m, round(100*sum(carteira_ativa)/sum(sum(carteira_ativa)) OVER (PARTITION BY data_base),2) s FROM v WHERE cliente='PF' GROUP BY cnae_ocupacao, data_base) ON m USING first(s) ORDER BY cnae_ocupacao",
)
show(
    "PF p_inad by occupation by month",
    "PIVOT (SELECT cnae_ocupacao, strftime(data_base,'%Y-%m') m, round(100*sum(carteira_inadimplencia)/sum(carteira_ativa),2) s FROM v WHERE cliente='PF' GROUP BY ALL) ON m USING first(s) ORDER BY cnae_ocupacao",
)
show(
    "PF p_ap_ex_inad by modalidade by month (R$ bi AP)",
    "PIVOT (SELECT modalidade, strftime(data_base,'%Y-%m') m, round(sum(ativo_problematico)/1e9,1) s FROM v WHERE cliente='PF' GROUP BY ALL) ON m USING first(s) ORDER BY modalidade",
)
