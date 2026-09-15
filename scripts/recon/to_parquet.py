"""Convert SCR.data V2 monthly CSVs to typed Parquet, once, with a conversion log.

    uv run --no-project --with duckdb python scripts/recon/to_parquet.py data/parquet/scrdata data/raw/zips/scrdata_*.zip
    uv run --no-project --with duckdb python scripts/recon/to_parquet.py data/parquet/scrdata data/raw/months/scrdata_2024*.csv

Inputs may be yearly ZIPs (each member is extracted to a temporary CSV, converted, and deleted) or
monthly CSVs. Output: one file per month, <out>/scrdata_YYYYMM.parquet, and one JSON line per month
in <out>/conversion_log.jsonl.

Typing follows docs/data_dictionary.md section 2: data_base DATE; dimensions trimmed (the raw
whitespace is counted in the log, not kept); numero_de_operacoes BIGINT with the -1 sentinel left
as published; measures DECIMAL(22,2) parsed from pt-BR decimals. The header must match the V2
schema exactly, and any measure that fails to parse stops the conversion for that month.
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
import zipfile
from pathlib import Path

import duckdb

DIMS = [
    "uf",
    "segmento",
    "cliente",
    "cnae_ocupacao",
    "porte",
    "modalidade",
    "submodalidade",
    "origem",
    "indexador",
]
MEASURES = [
    "a_vencer_ate_90_dias",
    "a_vencer_de_91_ate_360_dias",
    "a_vencer_de_361_ate_1080_dias",
    "a_vencer_de_1081_ate_1800_dias",
    "a_vencer_de_1801_ate_5400_dias",
    "a_vencer_acima_de_5400_dias",
    "carteira_a_vencer",
    "vencido_de_15_ate_90_dias",
    "vencido_acima_de_90_dias",
    "carteira_vencida",
    "carteira_ativa",
    "carteira_inadimplencia",
    "ativo_problematico",
]
HEADER = ["data_base", *DIMS, "numero_de_operacoes", *MEASURES]
NAME = re.compile(r"scrdata_(\d{6})\.csv")


def convert_csv(con: duckdb.DuckDBPyConnection, csv: Path, out: Path, month: str) -> dict:
    con.execute("DROP TABLE IF EXISTS t")
    con.execute(
        f"CREATE TEMP TABLE t AS SELECT * FROM read_csv('{csv}', delim=';', quote='\"', header=true, "
        "all_varchar=true, sample_size=-1, strict_mode=true)"
    )
    cols = [r[0] for r in con.execute("DESCRIBE t").fetchall()]
    if cols != HEADER:
        raise ValueError(f"{month}: header differs from V2 schema: {cols}")

    stats: dict = {"month": month, "rows": con.execute("SELECT count(*) FROM t").fetchone()[0]}
    stats["whitespace"] = {
        d: n
        for d in DIMS
        if (n := con.execute(f"SELECT count(*) FROM t WHERE {d} <> trim({d})").fetchone()[0])
    }
    stats["null_or_empty"] = {
        c: n
        for c in HEADER
        if (
            n := con.execute(
                f"SELECT count(*) FROM t WHERE {c} IS NULL OR trim({c}) = ''"
            ).fetchone()[0]
        )
    }
    bad = {
        m: n
        for m in MEASURES
        if (
            n := con.execute(
                f"SELECT count(*) FROM t WHERE {m} IS NOT NULL AND TRY_CAST(replace({m}, ',', '.') AS DECIMAL(22,2)) IS NULL"
            ).fetchone()[0]
        )
    }
    if bad:
        raise ValueError(f"{month}: unparseable measures {bad}")
    stats["ops_unparsed"] = con.execute(
        "SELECT count(*) FROM t WHERE TRY_CAST(numero_de_operacoes AS BIGINT) IS NULL"
    ).fetchone()[0]
    dates = con.execute("SELECT list(DISTINCT data_base) FROM t").fetchone()[0]
    stats["data_base"] = dates
    if len(dates) != 1 or dates[0][:7].replace("-", "") != month:
        raise ValueError(f"{month}: data_base values {dates} do not match the file name")

    select = ", ".join(
        ["CAST(data_base AS DATE) AS data_base"]
        + [f"trim({d}) AS {d}" for d in DIMS]
        + ["TRY_CAST(numero_de_operacoes AS BIGINT) AS numero_de_operacoes"]
        + [f"CAST(replace({m}, ',', '.') AS DECIMAL(22,2)) AS {m}" for m in MEASURES]
    )
    tmp = out / f".scrdata_{month}.parquet.tmp"
    con.execute(f"COPY (SELECT {select} FROM t) TO '{tmp}' (FORMAT parquet, COMPRESSION zstd)")
    tmp.rename(out / f"scrdata_{month}.parquet")
    stats["parquet_bytes"] = (out / f"scrdata_{month}.parquet").stat().st_size
    return stats


def main() -> int:
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    log = out / "conversion_log.jsonl"
    con = duckdb.connect()
    done = {p.stem.split("_")[1] for p in out.glob("scrdata_*.parquet")}
    failures = 0

    def handle(csv: Path, month: str, source: str) -> None:
        nonlocal failures
        try:
            stats = convert_csv(con, csv, out, month)
            stats["source"] = source
            with log.open("a") as fh:
                fh.write(json.dumps(stats, ensure_ascii=False) + "\n")
            print(
                f"ok {month} rows={stats['rows']:,} parquet={stats['parquet_bytes'] / 1e6:.1f}MB",
                flush=True,
            )
        except Exception as exc:  # noqa: BLE001 — report every bad month, keep going
            failures += 1
            print(f"FAILED {month}: {exc}", flush=True)

    for arg in sys.argv[2:]:
        path = Path(arg)
        if path.suffix == ".zip":
            with zipfile.ZipFile(path) as z:
                for info in sorted(z.infolist(), key=lambda i: i.filename):
                    m = NAME.fullmatch(info.filename)
                    if not m:
                        print(f"FAILED {info.filename}: unexpected member name", flush=True)
                        failures += 1
                        continue
                    if m.group(1) in done:
                        continue
                    with tempfile.TemporaryDirectory(dir=out) as tmpdir:
                        csv = Path(tmpdir) / info.filename
                        with z.open(info) as src, csv.open("wb") as dst:
                            while block := src.read(1 << 20):
                                dst.write(block)
                        handle(csv, m.group(1), f"{path.name}:{info.filename}")
        else:
            m = NAME.fullmatch(path.name)
            if not m:
                print(f"FAILED {path}: unexpected file name", flush=True)
                failures += 1
                continue
            if m.group(1) not in done:
                handle(path, m.group(1), path.name)
    print(f"DONE failures={failures}", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
