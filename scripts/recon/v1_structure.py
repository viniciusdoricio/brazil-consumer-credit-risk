"""V1 (planilha) structure by month, and V1-vs-V2 portfolio totals for the same month.

    RECON_DB=data/recon.duckdb uv run python scripts/recon/v1_structure.py

Requires the months to have been loaded with scripts/recon/load_months.py. Produces the V1 table in
docs/data-dictionary.md section 3 and the V1/V2 gap figures.
"""

import os
import sys

import duckdb

con = duckdb.connect(os.environ.get("RECON_DB", "data/recon.duckdb"), read_only=True)
tables = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
if not any(t.startswith("planilha_") for t in tables):
    sys.exit("no planilha_ tables loaded: see docs/data-dictionary.md, section 9")

print(
    "table | rows | PF rows | PF carteira R$ bi | tcb values | sr values | modalidades | '<= 15' rows"
)
for t in sorted(x for x in tables if x.startswith("planilha_")):
    r = con.execute(
        f"SELECT count(*), count(*) FILTER (WHERE cliente='PF'), "
        f"round(sum(carteira_ativa) FILTER (WHERE cliente='PF')/1e9, 1), "
        f"string_agg(DISTINCT tcb, ',' ORDER BY tcb), "
        f"string_agg(DISTINCT coalesce(sr, 'NULL'), ',' ORDER BY coalesce(sr, 'NULL')), "
        f"count(DISTINCT modalidade), count(*) FILTER (WHERE raw_numero_de_operacoes = '<= 15') "
        f"FROM {t}"
    ).fetchone()
    print(t, "|", " | ".join(str(x) for x in r))

print(
    "\nmonth | client | V1 carteira | V2 carteira | V2-V1 | % | V1 arrastada | V2 inadimplencia "
    "| V1 AP | V2 AP   (R$ bi)"
)
for t in sorted(x for x in tables if x.startswith("planilha_")):
    m = t.split("_")[1]
    if f"scrdata_{m}" not in tables:
        continue
    for cli in ("PF", "PJ"):
        a = con.execute(
            f"SELECT sum(carteira_ativa)/1e9, sum(carteira_inadimplida_arrastada)/1e9, "
            f"sum(ativo_problematico)/1e9 FROM planilha_{m} WHERE cliente='{cli}'"
        ).fetchone()
        b = con.execute(
            f"SELECT sum(carteira_ativa)/1e9, sum(carteira_inadimplencia)/1e9, "
            f"sum(ativo_problematico)/1e9 FROM scrdata_{m} WHERE cliente='{cli}'"
        ).fetchone()
        print(
            f"{m} | {cli} | {a[0]:,.2f} | {b[0]:,.2f} | {b[0] - a[0]:,.2f} | "
            f"{100 * (b[0] - a[0]) / a[0]:.2f} | {a[1]:,.2f} | {b[1]:,.2f} | {a[2]:,.2f} | {b[2]:,.2f}"
        )
