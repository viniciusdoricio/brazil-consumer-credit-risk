"""Load monthly SCR.data CSVs (V1 planilha_*, V2 scrdata_*) into a DuckDB file, typed.

    uv run python scripts/recon/load_months.py recon.duckdb data/raw/months/scrdata_202607.csv ...

Each file lands as table <stem> (e.g. scrdata_202607). Text dimensions are kept exactly as
published in raw_<col> AND trimmed in <col>, so whitespace traps stay visible. Measures are
parsed from pt-BR format ("1234,56") into DECIMAL(22,2); any value that fails to parse is
counted and reported rather than silently nulled.
"""

import sys
from pathlib import Path

import duckdb

MEASURE_PREFIXES = ("a_vencer", "vencido", "carteira", "ativo_problematico")

db, files = sys.argv[1], sys.argv[2:]
con = duckdb.connect(db)
for f in files:
    stem = Path(f).stem
    con.execute(f"DROP TABLE IF EXISTS {stem}_txt")
    con.execute(
        f"CREATE TABLE {stem}_txt AS SELECT * FROM read_csv('{f}', delim=';', quote='\"', "
        "header=true, all_varchar=true, sample_size=-1, strict_mode=true)"
    )
    cols = [r[0] for r in con.execute(f"DESCRIBE {stem}_txt").fetchall()]
    sel, failures = [], []
    for c in cols:
        q = f'"{c}"'
        if c.startswith(MEASURE_PREFIXES):
            expr = f"TRY_CAST(replace({q}, ',', '.') AS DECIMAL(22,2))"
            bad = con.execute(
                f"SELECT count(*) FROM {stem}_txt WHERE {q} IS NOT NULL AND {expr} IS NULL"
            ).fetchone()[0]
            dots = con.execute(f"SELECT count(*) FROM {stem}_txt WHERE {q} LIKE '%.%'").fetchone()[
                0
            ]
            if bad or dots:
                failures.append((c, bad, dots))
            sel.append(f"{expr} AS {c}")
        elif c == "numero_de_operacoes":
            sel.append(f"{q} AS raw_numero_de_operacoes")
            sel.append(f"TRY_CAST({q} AS BIGINT) AS numero_de_operacoes")
        elif c == "data_base":
            sel.append(f"CAST({q} AS DATE) AS data_base")
        else:
            sel.append(f"{q} AS raw_{c}")
            sel.append(f"trim({q}) AS {c}")
    con.execute(f"CREATE OR REPLACE TABLE {stem} AS SELECT {', '.join(sel)} FROM {stem}_txt")
    con.execute(f"DROP TABLE {stem}_txt")
    n = con.execute(f"SELECT count(*) FROM {stem}").fetchone()[0]
    print(
        f"loaded {stem}: {n:,} rows, {len(cols)} source columns; "
        f"measure parse problems (col, unparsed, contains '.'): {failures or 'none'}"
    )
