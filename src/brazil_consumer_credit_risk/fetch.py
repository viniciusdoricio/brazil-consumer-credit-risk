"""Download and stage the project's data.

    uv run fetch-data                        SCR.data from 2012 to this year, then the SGS series
    uv run fetch-data --years 2024 2026      a range of SCR.data years
    uv run fetch-data --no-sgs
    uv run fetch-data --refresh              replace archives BCB has republished

SCR.data archives go to data/raw/zips with MANIFEST.tsv, monthly Parquet to data/parquet/scrdata
with conversion_log.jsonl, and the SGS series to data/raw/sgs and data/parquet/sgs.parquet.
Archives already downloaded and months already converted from them are skipped, so an interrupted
run can simply be started again. A local archive is kept even when BCB republishes it, until
--refresh replaces it; months are converted again whenever their archive changes.
"""

from __future__ import annotations

import argparse
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import duckdb
import requests

from . import scr, sgs
from .download import new_session

log = logging.getLogger("fetch-data")


def fetch_scr(data_dir: Path, years: range, jobs: int, refresh: bool = False) -> int:
    """Download, verify and stage the SCR.data archives. Returns the number of failures."""
    raw_dir = data_dir / "raw" / "zips"
    out_dir = data_dir / "parquet" / "scrdata"
    raw_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    this_year = date.today().year

    def one(year: int) -> tuple[int, str | None, Exception | None]:
        try:
            return year, scr.fetch_archive(new_session(), year, raw_dir, refresh), None
        except requests.HTTPError as exc:
            if year == this_year and exc.response is not None and exc.response.status_code == 404:
                return year, f"{scr.archive_name(year)}: not published yet", None
            return year, None, exc
        except Exception as exc:
            return year, None, exc

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        results = sorted(pool.map(one, sorted(years, reverse=True)))

    failures = 0
    available = []
    for year, message, error in results:
        archive = raw_dir / scr.archive_name(year)
        if error is None:
            log.info("%s", message)
        else:
            # Still a failure, but an archive already on disk was verified when it was downloaded,
            # so staging it lets the build run while BCB is unreachable.
            failures += 1
            log.error("%s: %s", archive.name, error)
            if archive.exists():
                log.warning(
                    "%s: couldn't check for a newer release; using the local copy", archive.name
                )
        if archive.exists():
            available.append(year)

    con = duckdb.connect()
    for year in available:
        _, failed = scr.stage_archive(con, raw_dir / scr.archive_name(year), out_dir)
        failures += len(failed)
    return failures


def fetch_sgs(data_dir: Path) -> int:
    """Fetch the SGS series. Returns the number of failures (0 or 1)."""
    try:
        for line in sgs.fetch_all(
            new_session(), data_dir / "raw" / "sgs", data_dir / "parquet" / "sgs.parquet"
        ):
            log.info("%s", line)
    except Exception as exc:
        log.error("SGS: %s", exc)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fetch-data", description="Download and stage SCR.data and the SGS series."
    )
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument(
        "--years", type=int, nargs=2, metavar=("FIRST", "LAST"), help="SCR.data years to fetch"
    )
    parser.add_argument("--jobs", type=int, default=3, help="parallel archive downloads")
    parser.add_argument("--no-scr", action="store_true", help="skip SCR.data")
    parser.add_argument("--no-sgs", action="store_true", help="skip the SGS series")
    parser.add_argument(
        "--refresh", action="store_true", help="replace local archives that BCB has republished"
    )
    args = parser.parse_args(argv)

    first, last = args.years or (scr.FIRST_YEAR, date.today().year)
    if first < scr.FIRST_YEAR or last < first:
        parser.error(f"years must run from {scr.FIRST_YEAR} upward, first <= last")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    failures = 0
    if not args.no_scr:
        failures += fetch_scr(args.data_dir, range(first, last + 1), args.jobs, args.refresh)
    if not args.no_sgs:
        failures += fetch_sgs(args.data_dir)
    log.info("done, %d failure(s)", failures)
    return 1 if failures else 0
