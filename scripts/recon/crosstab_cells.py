"""Cross-tab completeness and income-band stability for every loaded V2 month.

    RECON_DB=data/recon.duckdb uv run python scripts/recon/crosstab_cells.py

For each scrdata_YYYYMM table: rows, whether the 10-dimension grain is unique, how many of the
8 x 9 PF occupation-by-income cells are populated, and the PF shares of the unstable categories
("Sem rendimento", "Indisponível", occupation "Outros", "MEI").
"""

import os

import duckdb

con = duckdb.connect(os.environ.get("RECON_DB", "data/recon.duckdb"), read_only=True)
tables = sorted(r[0] for r in con.execute("SHOW TABLES").fetchall() if r[0].startswith("scrdata_"))
dims = "data_base, uf, segmento, cliente, cnae_ocupacao, porte, modalidade, submodalidade, origem, indexador"
print(
    "month | rows | grain unique | PF cells populated | % Sem rendimento | % Indisponível | % Outros | % MEI"
)
for t in tables:
    n = con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
    d = con.execute(f"SELECT count(*) FROM (SELECT DISTINCT {dims} FROM {t})").fetchone()[0]
    cells = con.execute(
        f"SELECT count(DISTINCT (cnae_ocupacao, porte)) FROM {t} WHERE cliente='PF' AND carteira_ativa > 0"
    ).fetchone()[0]
    s = con.execute(
        f"""SELECT round(100*sum(carteira_ativa) FILTER (WHERE porte='Sem rendimento')/sum(carteira_ativa), 2),
                   round(100*sum(carteira_ativa) FILTER (WHERE porte='Indisponível')/sum(carteira_ativa), 2),
                   round(100*sum(carteira_ativa) FILTER (WHERE cnae_ocupacao='Outros')/sum(carteira_ativa), 2),
                   round(100*sum(carteira_ativa) FILTER (WHERE cnae_ocupacao='MEI')/sum(carteira_ativa), 2)
            FROM {t} WHERE cliente='PF'"""
    ).fetchone()
    print(f"{t[-6:]} | {n:,} | {n == d} | {cells}/72 | " + " | ".join(str(x) for x in s))
