"""Monthly series from BCB's SGS time-series API, kept as raw JSON and as one tidy Parquet file.

Official names, units and coverage of each series are in docs/data-landscape.md, section B.2.
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterable
from datetime import date
from pathlib import Path

import duckdb
import requests

from .download import Sleep

API_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"
TIMEOUT = 60

SERIES = {
    21084: "90-day delinquency, households, total (%)",
    24369: "Unemployment rate, PNAD Contínua (%)",
    1619: "Minimum wage (R$)",
    433: "IPCA, monthly change (%)",
    21129: "90-day delinquency, households, credit cards, non-earmarked (%)",
}

Row = tuple[int, date, float]


def fetch_series(
    session: requests.Session, code: int, attempts: int = 4, sleep: Sleep = time.sleep
) -> list[dict[str, str]]:
    """The full history of one series, as the API returns it."""
    problem = ""
    for attempt in range(attempts):
        try:
            response = session.get(
                API_URL.format(code=code), params={"formato": "json"}, timeout=TIMEOUT
            )
            if response.status_code == 200:
                return response.json()
            problem = f"HTTP {response.status_code}"
        except (requests.RequestException, ValueError) as exc:
            problem = str(exc)
        if attempt < attempts - 1:
            sleep(min(2**attempt, 30))
    raise OSError(f"SGS {code}: failed after {attempts} attempts ({problem})")


def parse_series(code: int, records: Iterable[dict[str, str]]) -> list[Row]:
    """(code, date, value) rows from API records such as {"data": "01/01/2024", "valor": "3.45"}."""
    rows = []
    for record in records:
        day, month, year = record["data"].split("/")
        rows.append((code, date(int(year), int(month), int(day)), float(record["valor"])))
    return rows


def write_parquet(rows: Iterable[Row], path: Path) -> None:
    con = duckdb.connect()
    con.execute("CREATE TABLE sgs (code INTEGER, date DATE, value DOUBLE)")
    con.executemany("INSERT INTO sgs VALUES (?, ?, ?)", list(rows))
    tmp = path.with_name(f".{path.name}.tmp")
    con.execute(f"COPY (SELECT * FROM sgs ORDER BY code, date) TO '{tmp}' (FORMAT parquet)")
    tmp.replace(path)


def fetch_all(
    session: requests.Session, raw_dir: Path, parquet_path: Path, codes: Iterable[int] = SERIES
) -> list[str]:
    """Fetch every series, save the raw JSON, and rewrite the tidy Parquet file."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    rows: list[Row] = []
    summary = []
    for code in codes:
        records = fetch_series(session, code)
        (raw_dir / f"sgs_{code}.json").write_text(json.dumps(records, ensure_ascii=False))
        parsed = parse_series(code, records)
        rows.extend(parsed)
        summary.append(f"SGS {code}: {len(parsed)} values, {parsed[0][1]} to {parsed[-1][1]}")
    write_parquet(rows, parquet_path)
    return summary
