"""SCR.data V2: download the yearly archives, verify them, and stage each month as typed Parquet.

BCB publishes one ZIP per year at ``{BASE_URL}/scrdata_{YYYY}.zip``, holding one semicolon-separated
CSV per month. The open-data portal's catalogue entries carry no download URLs, so the pattern is
used directly (docs/data-dictionary.md, section 1). BCB republishes past years, so each archive's
size, Last-Modified date and SHA-256 are recorded in MANIFEST.tsv next to it.

Typing follows docs/data-dictionary.md, section 2: data_base as DATE, dimensions trimmed,
numero_de_operacoes as BIGINT with the -1 sentinel kept as published, and measures as
DECIMAL(22,2) parsed from pt-BR decimals.
"""

from __future__ import annotations

import csv
import hashlib
import json
import logging
import re
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import duckdb
import requests

from .download import download, head

log = logging.getLogger(__name__)

BASE_URL = "https://www.bcb.gov.br/pda/desig"
FIRST_YEAR = 2012
MEMBER = re.compile(r"scrdata_(\d{6})\.csv")
MAX_MEMBER_BYTES = 2_000_000_000
MANIFEST = "MANIFEST.tsv"
MANIFEST_COLUMNS = [
    "file",
    "bytes",
    "last_modified",
    "sha256",
    "members",
    "first_month",
    "last_month",
    "downloaded_utc",
]
CONVERSION_LOG = "conversion_log.jsonl"

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


def archive_name(year: int) -> str:
    return f"scrdata_{year}.zip"


def archive_url(year: int) -> str:
    return f"{BASE_URL}/{archive_name(year)}"


@dataclass(frozen=True)
class ArchiveCheck:
    members: int
    first_month: str
    last_month: str


def verify_archive(path: Path) -> ArchiveCheck:
    """Accept only monthly V2 CSVs that pass their CRC32 check.

    Member names must be exactly scrdata_YYYYMM.csv, so a hostile archive cannot write outside
    the output directory when its members are extracted.
    """
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        months = []
        for info in infos:
            match = MEMBER.fullmatch(info.filename)
            if not match:
                raise ValueError(f"{path.name}: unexpected member {info.filename!r}")
            if info.compress_type not in (zipfile.ZIP_DEFLATED, zipfile.ZIP_STORED):
                raise ValueError(f"{path.name}: unexpected compression for {info.filename}")
            if info.file_size > MAX_MEMBER_BYTES:
                raise ValueError(f"{path.name}: {info.filename} is too large")
            months.append(match.group(1))
        if not months:
            raise ValueError(f"{path.name}: no members")
        bad = archive.testzip()
        if bad is not None:
            raise ValueError(f"{path.name}: CRC check failed for {bad}")
    return ArchiveCheck(len(infos), min(months), max(months))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while block := fh.read(1 << 20):
            digest.update(block)
    return digest.hexdigest()


def read_manifest(path: Path) -> dict[str, dict[str, str]]:
    """The latest manifest row for each archive."""
    if not path.exists():
        return {}
    with path.open(newline="") as fh:
        return {row["file"]: row for row in csv.DictReader(fh, delimiter="\t")}


def append_manifest(path: Path, row: dict[str, str]) -> None:
    new = not path.exists()
    with path.open("a", newline="") as fh:
        writer = csv.DictWriter(fh, MANIFEST_COLUMNS, delimiter="\t", lineterminator="\n")
        if new:
            writer.writeheader()
        writer.writerow(row)


def fetch_archive(
    session: requests.Session, year: int, raw_dir: Path, refresh: bool = False
) -> str:
    """Download and verify one year's archive.

    BCB republishes past years, so a local copy is only replaced when refresh is set: the
    analysis stays on the version recorded in the manifest until someone decides to move it.
    A new download is verified before it replaces anything.
    """
    name = archive_name(year)
    dest = raw_dir / name
    remote = head(session, archive_url(year))
    manifest = raw_dir / MANIFEST
    recorded = read_manifest(manifest).get(name)
    if dest.exists():
        local_size = dest.stat().st_size
        if local_size == remote.size and (
            recorded is None or recorded["last_modified"] == remote.last_modified
        ):
            return f"{name}: already downloaded"
        if not refresh:
            change = (
                f"Last-Modified {recorded['last_modified']} -> {remote.last_modified}"
                if recorded
                else f"{local_size} -> {remote.size} bytes"
            )
            return (
                f"{name}: kept the local copy, but BCB has republished it ({change}); "
                "run with --refresh to replace it"
            )

    log.info("%s: downloading %.1f MB (%s)", name, remote.size / 1e6, remote.last_modified)
    incoming = raw_dir / f"{name}.download"
    download(session, remote, incoming)
    try:
        check = verify_archive(incoming)
    except Exception:
        incoming.unlink()
        raise
    incoming.replace(dest)
    append_manifest(
        manifest,
        {
            "file": name,
            "bytes": str(remote.size),
            "last_modified": remote.last_modified,
            "sha256": sha256(dest),
            "members": str(check.members),
            "first_month": check.first_month,
            "last_month": check.last_month,
            "downloaded_utc": datetime.now(UTC).isoformat(),
        },
    )
    return (
        f"{name}: {remote.size / 1e6:.1f} MB, months {check.first_month} to "
        f"{check.last_month}, CRC ok"
    )


def convert_month(
    con: duckdb.DuckDBPyConnection, csv_path: Path, out_dir: Path, month: str
) -> dict:
    """Convert one monthly CSV to out_dir/scrdata_YYYYMM.parquet and return its statistics.

    Stops, writing nothing, if the header differs from the V2 schema, if any measure fails to
    parse, or if data_base doesn't match the month in the file name.
    """
    con.execute("DROP TABLE IF EXISTS t")
    con.execute(
        f"CREATE TEMP TABLE t AS SELECT * FROM read_csv('{csv_path}', delim=';', quote='\"', "
        "header=true, all_varchar=true, sample_size=-1, strict_mode=true)"
    )
    columns = [row[0] for row in con.execute("DESCRIBE t").fetchall()]
    if columns != HEADER:
        raise ValueError(f"{month}: header differs from the V2 schema: {columns}")

    # Every check in one pass over the month: a query per check scans it 46 times.
    checks = {
        "rows": "count(*)",
        **{f"whitespace:{d}": f"count_if({d} <> trim({d}))" for d in DIMS},
        **{f"null_or_empty:{c}": f"count_if({c} IS NULL OR trim({c}) = '')" for c in HEADER},
        **{
            f"unparsed:{m}": (
                f"count_if({m} IS NOT NULL "
                f"AND TRY_CAST(replace({m}, ',', '.') AS DECIMAL(22,2)) IS NULL)"
            )
            for m in MEASURES
        },
        "ops_unparsed": "count_if(TRY_CAST(numero_de_operacoes AS BIGINT) IS NULL)",
        "dates": "list(DISTINCT data_base)",
    }
    result = con.execute(f"SELECT {', '.join(checks.values())} FROM t").fetchone()
    found = dict(zip(checks, result, strict=True))

    def nonzero(kind: str) -> dict[str, int]:
        prefix = f"{kind}:"
        return {k.removeprefix(prefix): n for k, n in found.items() if k.startswith(prefix) and n}

    stats: dict = {
        "month": month,
        "rows": found["rows"],
        "whitespace": nonzero("whitespace"),
        "null_or_empty": nonzero("null_or_empty"),
    }
    unparsed = nonzero("unparsed")
    if unparsed:
        raise ValueError(f"{month}: measures that don't parse: {unparsed}")
    stats["ops_unparsed"] = found["ops_unparsed"]
    dates = found["dates"]
    stats["data_base"] = dates
    if len(dates) != 1 or dates[0][:7].replace("-", "") != month:
        raise ValueError(f"{month}: data_base values {dates} don't match the file name")

    select = ", ".join(
        ["CAST(data_base AS DATE) AS data_base"]
        + [f"trim({d}) AS {d}" for d in DIMS]
        + ["TRY_CAST(numero_de_operacoes AS BIGINT) AS numero_de_operacoes"]
        + [f"CAST(replace({m}, ',', '.') AS DECIMAL(22,2)) AS {m}" for m in MEASURES]
    )
    target = out_dir / f"scrdata_{month}.parquet"
    tmp = out_dir / f".{target.name}.tmp"
    con.execute(f"COPY (SELECT {select} FROM t) TO '{tmp}' (FORMAT parquet, COMPRESSION zstd)")
    tmp.replace(target)
    stats["parquet_bytes"] = target.stat().st_size
    return stats


def read_conversion_log(path: Path) -> dict[str, dict]:
    """The latest conversion-log entry for each month."""
    latest: dict[str, dict] = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if line.strip():
                entry = json.loads(line)
                latest[entry["month"]] = entry
    return latest


def stage_archive(
    con: duckdb.DuckDBPyConnection, archive: Path, out_dir: Path
) -> tuple[list[str], list[str]]:
    """Convert each month in the archive unless its Parquet file came from this same archive.

    Every conversion appends a line to conversion_log.jsonl with the SHA-256 of the archive it
    came from, so a republished archive is converted again rather than leaving Parquet from an
    older version next to it. Returns the months converted and the months that failed.
    """
    archive_sha = sha256(archive)
    done = {
        month
        for month, entry in read_conversion_log(out_dir / CONVERSION_LOG).items()
        if entry.get("archive_sha256") == archive_sha
        and (out_dir / f"scrdata_{month}.parquet").exists()
    }
    converted: list[str] = []
    failed: list[str] = []
    with zipfile.ZipFile(archive) as z:
        for info in sorted(z.infolist(), key=lambda i: i.filename):
            match = MEMBER.fullmatch(info.filename)
            if not match:
                log.error("%s: unexpected member %r", archive.name, info.filename)
                failed.append(info.filename)
                continue
            month = match.group(1)
            if month in done:
                continue
            with tempfile.TemporaryDirectory(dir=out_dir) as tmp:
                csv_path = Path(tmp) / info.filename
                with z.open(info) as src, csv_path.open("wb") as dst:
                    shutil.copyfileobj(src, dst, 1 << 20)
                try:
                    stats = convert_month(con, csv_path, out_dir, month)
                except Exception as exc:
                    log.error("%s: %s", month, exc)
                    failed.append(month)
                    continue
            stats["source"] = f"{archive.name}:{info.filename}"
            stats["archive_sha256"] = archive_sha
            with (out_dir / CONVERSION_LOG).open("a") as fh:
                fh.write(json.dumps(stats, ensure_ascii=False) + "\n")
            converted.append(month)
            log.info("%s: %s rows to Parquet", month, f"{stats['rows']:,}")
    return converted, failed
