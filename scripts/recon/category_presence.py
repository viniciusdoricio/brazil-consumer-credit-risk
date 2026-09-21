"""Which dimension values are missing from some of the five sampled V2 months.

    RECON_DB=data/recon.duckdb uv run python scripts/recon/category_presence.py

Months: 2013-06, 2024-06, 2024-12, 2025-01 and 2026-07, loaded by load_months.py. For
sub-modality, segment, index, modality and size or income band, prints every value that is
not present in all five months, with the months it appears in and its balance in R$ bn.
"""

import os

import duckdb

con = duckdb.connect(os.environ.get("RECON_DB", "data/recon.duckdb"), read_only=True)
T = ["scrdata_201306", "scrdata_202406", "scrdata_202412", "scrdata_202501", "scrdata_202607"]
for col in ["submodalidade", "segmento", "indexador", "modalidade", "porte"]:
    u = " UNION ALL ".join(
        f"SELECT strftime(data_base, '%Y-%m') AS m, cliente, {col} AS k, sum(carteira_ativa) AS a FROM {t} GROUP BY ALL"
        for t in T
    )
    rows = con.execute(
        f"SELECT cliente, k, string_agg(DISTINCT m, ',' ORDER BY m) AS present, round(sum(a)/1e9, 1) AS bi "
        f"FROM ({u}) GROUP BY 1, 2 HAVING count(DISTINCT m) < 5 ORDER BY 3, 1, 2"
    ).fetchall()
    print(f"\n### {col}: values not present in all 5 sampled months")
    for r in rows:
        print("   ", r)
